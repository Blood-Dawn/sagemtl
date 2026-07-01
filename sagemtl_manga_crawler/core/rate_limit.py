"""Per-host rate limiting via a token bucket.

Used by :mod:`fetch` to honor declared source rate limits (e.g. MangaDex ~5
req/s per IP, /at-home 40/min, /report 10/min). The time and sleep functions are
injectable so the limiter is deterministically testable without real sleeps.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 9.4.
"""

from __future__ import annotations

import time
from typing import Callable

__all__ = ["TokenBucket"]


class TokenBucket:
    """A simple token-bucket limiter: ``rate`` tokens/sec, burst up to ``capacity``."""

    def __init__(
        self,
        rate: float,
        capacity: float | None = None,
        *,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be > 0")
        self.rate = float(rate)
        self.capacity = float(capacity if capacity is not None else rate)
        self._tokens = self.capacity
        self._time = time_fn
        self._sleep = sleep_fn
        self._last = time_fn()

    def _refill(self) -> None:
        now = self._time()
        elapsed = max(0.0, now - self._last)
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last = now

    def acquire(self, tokens: float = 1.0) -> float:
        """Block until ``tokens`` are available; return the seconds waited."""

        waited = 0.0
        self._refill()
        if self._tokens < tokens:
            deficit = tokens - self._tokens
            delay = deficit / self.rate
            self._sleep(delay)
            waited = delay
            self._refill()
        self._tokens = max(0.0, self._tokens - tokens)
        return waited
