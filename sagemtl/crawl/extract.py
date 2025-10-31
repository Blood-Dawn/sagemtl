# Kheiven D''Haiti — minimal HTML extractor (stdlib-only)
from __future__ import annotations

import re
from html import unescape

from sagemtl.clean.text_normalize import normalize_text


_BLOCK = r"(?:article|main|section|div|body)"
_TAG_RE = re.compile(r"<[^>]+>", re.IGNORECASE | re.DOTALL)


def _pick_section(html: str) -> str:
    for tag in ("article", "main"):
        m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", html, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)
    m = re.search(r"<body\b[^>]*>(.*?)</body>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1) if m else html


def extract_main_text(html: str) -> str:
    if not isinstance(html, str):
        html = str(html)

    # 1) Focus on likely content
    chunk = _pick_section(html)

    # 2) Drop non-content
    chunk = re.sub(r"<(script|style|noscript)\b.*?</\1>", "", chunk, flags=re.IGNORECASE | re.DOTALL)

    # 3) Turn block boundaries into newlines
    #    Ensure <p>, <br>, headers, and list items become paragraph breaks.
    chunk = re.sub(r"</?(p|br|li|h[1-6]|section|article)\b[^>]*>", "\n", chunk, flags=re.IGNORECASE)

    # 4) Strip tags
    chunk = _TAG_RE.sub("", chunk)

    # 5) Unescape entities and clean whitespace
    chunk = unescape(chunk).replace("\u00A0", " ").replace("\ufeff", "")
    # collapse runs of spaces; keep newlines
    chunk = re.sub(r"[ \t]+", " ", chunk)
    # compress 3+ newlines down to 2
    chunk = re.sub(r"\n{3,}", "\n\n", chunk)
    chunk = chunk.strip()

    # 6) Normalize (smart quotes, dash, final newline, LF only)
    return normalize_text(chunk)
