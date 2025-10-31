# Kheiven D'Haiti — text normalization
from __future__ import annotations

import re
import unicodedata

_SMART = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201b": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u2026": "...",
}
_ZW = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"}


def _strip_trailing_ws(s: str) -> str:
    return "\n".join(re.sub(r"[ \t]+$", "", line) for line in s.splitlines())


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = text.translate({ord(k): v for k, v in _SMART.items()})
    text = unicodedata.normalize("NFKC", text)
    for z in _ZW:
        text = text.replace(z, "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _strip_trailing_ws(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def basic_clean(text: str) -> str:  # back-compat for tests
    return normalize_text(text)
