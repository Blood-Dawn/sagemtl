# Kheiven D'Haiti — text normalization
from __future__ import annotations

import re
import unicodedata

# smart punctuation & spaces → ASCII
_SMART = {
    "\u2018": "'", "\u2019": "'", "\u201B": "'",
    "\u201C": '"', "\u201D": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
    "\u2026": "...",
    "\u00A0": " ",  # NBSP -> space
}

# zero-widths to strip
_ZW = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"}

def _strip_trailing_ws(s: str) -> str:
    return "\n".join(re.sub(r"[ \t]+$", "", line) for line in s.splitlines())

def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    # map smart chars, fold width
    text = text.translate({ord(k): v for k, v in _SMART.items()})
    text = unicodedata.normalize("NFKC", text)
    # drop zero-widths
    for z in _ZW:
        text = text.replace(z, "")
    # normalize newlines to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # strip right-side spaces per line
    text = _strip_trailing_ws(text)
    # collapse 3+ blank lines → exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # guarantee exactly one trailing LF
    if not text.endswith("\n"):
        text += "\n"
    return text

# back-compat alias used by tests
def basic_clean(text: str) -> str:
    return normalize_text(text)
