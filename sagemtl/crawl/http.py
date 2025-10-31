# Kheiven D'Haiti — minimal HTTP client
from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import importlib

    httpx = importlib.import_module("httpx")
except Exception:  # pragma: no cover
    httpx = None

if TYPE_CHECKING:  # help static analyzers find httpx
    import httpx  # type: ignore  # pragma: no cover

_UA = "sagemtl/0.0.1 (+https://github.com/Blood-Dawn/sagemtl)"


def get_text(url: str, timeout: float = 20.0) -> str:
    if httpx is None:  # pragma: no cover
        raise RuntimeError("Install with extras: pip install -e .[crawl]")
    with httpx.Client(
        headers={"user-agent": _UA},
        follow_redirects=True,
        http2=True,
        timeout=timeout,
    ) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text
