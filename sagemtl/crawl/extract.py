# Blood-Dawn — extractor
from __future__ import annotations

import re
from html import unescape

from bs4 import BeautifulSoup

from sagemtl.clean.text_normalize import normalize_text


def extract_main_text(html: str) -> str:
    # Parse and drop noise
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Raw text with stable separators
    text = soup.get_text(separator="\n")

    # Decode entities (&nbsp; -> \xa0, etc.) then normalize typography/newlines
    text = unescape(text)
    text = text.replace("\ufeff", "")  # strip BOM if present
    text = re.sub(r"\n{3,}", "\n\n", text)  # collapse huge gaps

    # Run through canonical normalizer (quotes/dashes/nbsp/newlines)
    text = normalize_text(text)
    return text
