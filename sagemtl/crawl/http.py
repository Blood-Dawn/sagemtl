"""HTTP helpers with caching, retries, and robots.txt support."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import tempfile
import time
from typing import Callable, Dict, Optional
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx

DEFAULT_UA = "sagemtl/0.1 (+https://github.com/Blood-Dawn/sagemtl)"


class RobotsDisallowed(RuntimeError):
    """Raised when a URL is blocked by robots.txt rules."""


def _default_cache_dir() -> Path:
    override = os.environ.get("SAGEMTL_HTTP_CACHE")
    if override:
        return Path(override)
    return Path(tempfile.gettempdir()) / "sagemtl-http-cache"


@dataclass
class HTTPClientConfig:
    """Configuration for :class:`HTTPClient`."""

    cache_dir: Path | None = field(default_factory=_default_cache_dir)
    user_agent: str = DEFAULT_UA
    timeout: float = 20.0
    max_retries: int = 3
    retry_backoff: float = 0.5
    respect_robots: bool = True


ConfigFactory = Callable[[], HTTPClientConfig]


class HTTPClient:
    """Wrapper around :class:`httpx.Client` with caching and robots support."""

    def __init__(
        self,
        config: HTTPClientConfig | None = None,
        *,
        client: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config or HTTPClientConfig()
        if client is not None and transport is not None:
            raise ValueError("Provide either client or transport, not both")

        self._client = client or httpx.Client(
            headers={"User-Agent": self.config.user_agent},
            transport=transport,
        )
        self._owns_client = client is None
        self._robots_parsers: Dict[str, RobotFileParser] = {}

        if self.config.cache_dir is not None:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "HTTPClient":  # pragma: no cover - convenience
        return self

    def __exit__(self, *exc_info: object) -> None:  # pragma: no cover - convenience
        self.close()

    def get_text(self, url: str, *, encoding: str | None = None) -> str:
        if self.config.respect_robots and not self._is_allowed(url):
            raise RobotsDisallowed(f"Blocked by robots.txt: {url}")

        cached = self._read_cache(url)
        if cached is not None:
            return cached

        response = self._request_with_retries(url)
        if encoding:
            response.encoding = encoding
        response.raise_for_status()
        text = response.text
        self._write_cache(url, text)
        return text

    def _request_with_retries(self, url: str) -> httpx.Response:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = self._client.get(url, timeout=self.config.timeout)
                if response.status_code >= 500:
                    response.raise_for_status()
                return response
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt >= self.config.max_retries:
                    break
                time.sleep(self.config.retry_backoff * (2 ** (attempt - 1)))
        assert last_exc is not None
        raise last_exc

    def _robots_parser(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
        if origin in self._robots_parsers:
            return self._robots_parsers[origin]

        robots_url = urlunparse(
            (parsed.scheme, parsed.netloc, "/robots.txt", "", "", "")
        )
        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            response = self._request_with_retries(robots_url)
            if response.status_code == 404:
                parser.parse("")
            else:
                response.raise_for_status()
                parser.parse(response.text.splitlines())
        except httpx.RequestError:
            parser.parse("")

        self._robots_parsers[origin] = parser
        return parser

    def _is_allowed(self, url: str) -> bool:
        parser = self._robots_parser(url)
        return parser.can_fetch(self.config.user_agent, url)

    def _cache_path(self, url: str) -> Path | None:
        if self.config.cache_dir is None:
            return None
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.config.cache_dir / f"{digest}.txt"

    def _read_cache(self, url: str) -> str | None:
        cache_path = self._cache_path(url)
        if cache_path and cache_path.exists():
            return cache_path.read_text(encoding="utf-8")
        return None

    def _write_cache(self, url: str, text: str) -> None:
        cache_path = self._cache_path(url)
        if cache_path is None:
            return
        cache_path.write_text(text, encoding="utf-8")


_default_config = HTTPClientConfig()
_config_factory: ConfigFactory | None = None
_client_singleton: HTTPClient | None = None


def set_http_config_factory(factory: ConfigFactory) -> None:
    """Set a factory used to build :class:`HTTPClientConfig` instances."""

    global _config_factory, _client_singleton
    _config_factory = factory
    _client_singleton = None


def configure_http(config: HTTPClientConfig) -> None:
    """Set the global default HTTP configuration."""

    global _default_config, _client_singleton
    _default_config = config
    _client_singleton = None


def get_http_client() -> HTTPClient:
    """Return a process-wide :class:`HTTPClient` singleton."""

    global _client_singleton
    if _client_singleton is None:
        config = _config_factory() if _config_factory else _default_config
        _client_singleton = HTTPClient(config=config)
    return _client_singleton


def fetch_text(
    url: str,
    timeout: float | None = None,
    ua: str | None = None,
    encoding: str | None = None,
) -> str:
    """Compatibility wrapper around :class:`HTTPClient.get_text`."""

    config = _config_factory() if _config_factory else _default_config
    if timeout is not None or ua is not None:
        config = HTTPClientConfig(
            cache_dir=config.cache_dir,
            user_agent=ua or config.user_agent,
            timeout=timeout or config.timeout,
            max_retries=config.max_retries,
            retry_backoff=config.retry_backoff,
            respect_robots=config.respect_robots,
        )
        client = HTTPClient(config=config)
        try:
            return client.get_text(url, encoding=encoding)
        finally:
            client.close()

    client = get_http_client()
    return client.get_text(url, encoding=encoding)
