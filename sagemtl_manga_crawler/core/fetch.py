"""HTTP fetch client for manga sources.

An httpx-backed client with per-host token-bucket rate limiting, retries with
exponential backoff, an honest (non-spoofed) User-Agent, and per-request Referer
support (manga CDNs hotlink-protect). The httpx import is lazy. A pre-built
``client`` can be injected (e.g. an ``httpx.Client`` with a ``MockTransport``) so
the fetcher is unit-testable without network.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 9.4.
"""

from __future__ import annotations

import time
from typing import Callable, Optional
from urllib.parse import urlsplit

from .rate_limit import TokenBucket

__all__ = ["MangaFetcher", "DEFAULT_USER_AGENT"]

DEFAULT_USER_AGENT = "SageMTL/0.1 (+https://github.com/Bloodawn/sagemtl; manga reader)"


class MangaFetcher:
    """Rate-limited, retrying HTTP client with per-host token buckets."""

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        rate_per_sec: float = 5.0,
        max_retries: int = 3,
        base_delay: float = 1.0,
        timeout: float = 30.0,
        client=None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.user_agent = user_agent
        self.rate_per_sec = rate_per_sec
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout
        self._client = client
        self._sleep = sleep_fn
        self._buckets: dict[str, TokenBucket] = {}

    def _get_client(self):
        if self._client is None:
            import httpx

            self._client = httpx.Client(
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    def _bucket(self, url: str) -> TokenBucket:
        host = urlsplit(url).netloc
        if host not in self._buckets:
            self._buckets[host] = TokenBucket(self.rate_per_sec, sleep_fn=self._sleep)
        return self._buckets[host]

    def _request(self, method: str, url: str, *, headers=None, params=None, json=None):
        import httpx

        self._bucket(url).acquire()
        client = self._get_client()
        delay = self.base_delay
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = client.request(method, url, headers=headers, params=params, json=json)
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    raise httpx.HTTPStatusError(
                        f"retryable status {response.status_code}", request=response.request,
                        response=response,
                    )
                return response
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    break
                self._sleep(delay)
                delay *= 2
        raise last_exc if last_exc is not None else RuntimeError("request failed")

    def get_json(self, url: str, *, params=None, headers=None) -> dict:
        response = self._request("GET", url, params=params, headers=headers)
        response.raise_for_status()  # surfaces 4xx (e.g. 404) to the caller
        return response.json()

    def get_bytes(self, url: str, *, referer: Optional[str] = None, headers=None) -> bytes:
        merged = dict(headers or {})
        if referer:
            merged["Referer"] = referer
        response = self._request("GET", url, headers=merged)
        response.raise_for_status()  # surfaces a stale-baseUrl 403 so we can re-request
        return response.content

    def post_json(self, url: str, *, json: dict, headers=None) -> int:
        return self._request("POST", url, json=json, headers=headers).status_code

    def report(self, url: str, payload: dict, *, timeout: float = 2.0) -> Optional[int]:
        """Fire-and-forget best-effort POST: short timeout, NO retries, errors swallowed.

        Image-success reporting must never block or fail a download, so it does not
        go through the retrying ``_request`` path. Returns the status code or None.
        """

        try:
            self._bucket(url).acquire()
            response = self._get_client().post(url, json=payload, timeout=timeout)
            return response.status_code
        except Exception:
            return None

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
