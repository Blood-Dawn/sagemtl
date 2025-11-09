"""
Polite HTTP client with robots.txt support and rate limiting
"""

import asyncio
import random
from typing import Optional, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx


class PoliteFetcher:
    """
    HTTP client that respects robots.txt and implements rate limiting
    """

    def __init__(
        self,
        user_agent: str = "SageMTL Crawler/1.0 (https://github.com/sagemtl)",
        delay_ms: Tuple[int, int] = (500, 1500),
        max_concurrency: int = 6,
        respect_robots: bool = True,
        timeout: float = 30.0
    ):
        self.user_agent = user_agent
        self.delay_ms = delay_ms
        self.max_concurrency = max_concurrency
        self.respect_robots = respect_robots
        self.timeout = timeout

        # Concurrency control
        self.semaphore = asyncio.Semaphore(max_concurrency)

        # Robots.txt cache (host -> RobotFileParser)
        self._robots_cache: dict[str, Optional[RobotFileParser]] = {}

        # HTTP client
        limits = httpx.Limits(
            max_connections=max_concurrency * 2,
            max_keepalive_connections=max_concurrency
        )

        self.client = httpx.AsyncClient(
            headers={"User-Agent": user_agent},
            limits=limits,
            timeout=timeout,
            follow_redirects=True
        )

    async def _get_robots_parser(self, url: str) -> Optional[RobotFileParser]:
        """Get robots.txt parser for a URL's host"""
        if not self.respect_robots:
            return None

        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"

        if host in self._robots_cache:
            return self._robots_cache[host]

        robots_url = f"{host}/robots.txt"
        parser = RobotFileParser(robots_url)

        try:
            # Fetch robots.txt
            response = await self.client.get(robots_url, timeout=5.0)
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
            else:
                # No robots.txt or error - allow all
                parser = None
        except Exception as e:
            print(f"Warning: Failed to fetch robots.txt from {host}: {e}")
            parser = None

        self._robots_cache[host] = parser
        return parser

    async def _check_robots_allowed(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt"""
        if not self.respect_robots:
            return True

        parser = await self._get_robots_parser(url)
        if parser is None:
            return True

        return parser.can_fetch(self.user_agent, url)

    async def _sleep_jitter(self):
        """Sleep with random jitter"""
        lo, hi = self.delay_ms
        delay_seconds = random.uniform(lo / 1000, hi / 1000)
        await asyncio.sleep(delay_seconds)

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        max_retries: int = 3,
        **kwargs
    ) -> httpx.Response:
        """
        Fetch a URL with politeness measures.

        Args:
            url: URL to fetch
            method: HTTP method
            max_retries: Maximum retry attempts
            **kwargs: Additional arguments for httpx.request

        Returns:
            HTTP response

        Raises:
            PermissionError: If robots.txt disallows the URL
            httpx.HTTPError: If fetch fails after retries
        """
        # Check robots.txt
        if not await self._check_robots_allowed(url):
            raise PermissionError(
                f"URL disallowed by robots.txt: {url}\n"
                f"Set respect_robots=False to override (not recommended)"
            )

        # Acquire semaphore for concurrency control
        async with self.semaphore:
            # Exponential backoff for retries
            for attempt in range(max_retries):
                try:
                    # Add jitter delay before request
                    if attempt > 0:
                        # Backoff: 2^attempt seconds + jitter
                        backoff = (2 ** attempt) + random.uniform(0, 1)
                        await asyncio.sleep(backoff)
                    else:
                        # Normal polite delay
                        await self._sleep_jitter()

                    # Make request
                    response = await self.client.request(method, url, **kwargs)

                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            await asyncio.sleep(float(retry_after))
                        continue

                    # Raise for HTTP errors (4xx, 5xx)
                    response.raise_for_status()

                    return response

                except httpx.HTTPStatusError as e:
                    if e.response.status_code >= 500 and attempt < max_retries - 1:
                        # Retry on server errors
                        continue
                    raise

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        continue
                    raise

                except httpx.RequestError as e:
                    if attempt < max_retries - 1:
                        continue
                    raise

            # Should not reach here
            raise httpx.RequestError(f"Failed to fetch {url} after {max_retries} attempts")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
