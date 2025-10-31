# Kheiven D'Haiti — cleaner
import re, unicodedata

def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u2014", "-")         # no em dashes
    s = s.replace("\u00A0", " ")         # no hard spaces
    return s

def _quotes(s: str) -> str:
    # straighten quotes
    s = s.replace("“","\"").replace("”","\"").replace("‘","'").replace("’","'")
    return s

def _whitespace(s: str) -> str:
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def clean_text(s: str) -> str:
    s = _normalize(s)
    s = _quotes(s)
    s = _whitespace(s)
    return s
