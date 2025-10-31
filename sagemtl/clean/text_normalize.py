from __future__ import annotations

import re
import unicodedata

_SMART = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",  # en/em dash -> hyphen
    "\u00a0": " ",  # nbsp -> space
}


def _desmart(s: str) -> str:
    for k, v in _SMART.items():
        s = s.replace(k, v)
    return s


def normalize_text(text: str, *, strip_smart: bool = True, collapse_ws: bool = True) -> str:
    # NFKC to fold width/compat characters (e.g., full-width)
    s = unicodedata.normalize("NFKC", text)
    if strip_smart:
        s = _desmart(s)
    # normalize line endings, trim trailing spaces
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(line.rstrip() for line in s.split("\n"))
    if collapse_ws:
        # collapse 2+ spaces -> single, keep newlines
        s = re.sub(r"[ \t]{2,}", " ", s)
        # collapse 3+ newlines -> 2
        s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip() + ("\n" if s.strip() else "")


# back-compat alias for tests
__all__ = list(set(globals().get("__all__", []))) + ["basic_clean"]


def basic_clean(text: str) -> str:
    return normalize_text(text)
