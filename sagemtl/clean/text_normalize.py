# Kheiven D'Haiti — normalize utils (no em dashes, no drama)
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
    "\u00a0": " ",
}
_ZW = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"}


def _strip_trailing_ws(s: str) -> str:
    return "\n".join(re.sub(r"[ \t]+$", "", line) for line in s.splitlines())


def normalize_text(text: str) -> str:
    """Canonical cleaner: smart quotes → ASCII, collapse >2 LFs to 2, keep final LF."""
    if not isinstance(text, str):
        text = str(text)
    # map smart chars
    text = text.translate({ord(k): v for k, v in _SMART.items()})
    # normalize width/compat
    text = unicodedata.normalize("NFKC", text)
    # strip zero-widths
    for z in _ZW:
        text = text.replace(z, "")
    # CRLF/LF -> LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # strip trailing spaces per line
    text = _strip_trailing_ws(text)
    # collapse 3+ blank lines -> exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # ensure a final LF (library function contract)
    if not text.endswith("\n"):
        text += "\n"
    return text


def basic_clean(text: str) -> str:
    """Back-compat alias w/o final LF (tests expect no trailing newline)."""
    out = normalize_text(text)
    return out[:-1] if out.endswith("\n") else out
