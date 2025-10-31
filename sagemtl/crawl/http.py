# Kheiven D'Haiti — HTTP fetch (no drama)
from __future__ import annotations

import httpx

DEFAULT_UA = "sagemtl/0.1 (+https://github.com/Blood-Dawn/sagemtl)"


def fetch_text(
    url: str, timeout: float = 20.0, ua: str = DEFAULT_UA, encoding: str | None = None
) -> str:
    r = httpx.get(url, timeout=timeout, headers={"User-Agent": ua})
    r.raise_for_status()
    if encoding:
        r.encoding = encoding
    return r.text
