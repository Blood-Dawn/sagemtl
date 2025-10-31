# Kheiven D'Haiti — sagemtl.clean.text_normalize
from __future__ import annotations
import re
__all__ = ["normalize_text"]

_WS = re.compile(r"\s+", re.MULTILINE)

def normalize_text(s: str) -> str:
    # basic: strip, collapse whitespace, normalize fancy quotes/punct
    s = s.replace("\u2018", "'").replace("\u2019", "'").replace("\u201C", '"').replace("\u201D", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-")  # no em dashes, per your rule
    s = _WS.sub(" ", s).strip()
    return s
