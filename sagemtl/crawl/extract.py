# Blood-Dawn — extractor
from __future__ import annotations

from collections import Counter
import re
from html import unescape
from typing import Iterable

from bs4 import BeautifulSoup

from sagemtl.clean.text_normalize import normalize_text

_STRUCTURAL_SELECTORS = ("header", "footer", "nav", "aside")
_BOILERPLATE_RE = re.compile(
    r"(breadcrumb|copyright|cookie|footer|header|menu|masthead|navbar|nav|newsletter|promo|subscribe)",
    re.IGNORECASE,
)


def _iter_attr_values(value: object) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


def _drop_boilerplate_tags(soup: BeautifulSoup) -> None:
    for selector in _STRUCTURAL_SELECTORS:
        for tag in soup.select(selector):
            tag.decompose()

    for tag in list(soup.find_all(True)):
        attr_values = list(_iter_attr_values(tag.get("class"))) + list(
            _iter_attr_values(tag.get("id"))
        )
        if any(_BOILERPLATE_RE.search(val) for val in attr_values):
            tag.decompose()


def _strip_repeated_edges(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text

    stripped_counts = Counter(line.strip() for line in lines if line.strip())

    def should_trim(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return True
        if len(stripped) > 120:
            return False
        return stripped_counts.get(stripped, 0) >= 2

    start = 0
    end = len(lines)
    while start < end and should_trim(lines[start]):
        start += 1
    while end > start and should_trim(lines[end - 1]):
        end -= 1

    if start >= end:
        return text

    trimmed = "\n".join(lines[start:end])
    return trimmed


def extract_main_text(html: str) -> str:
    # Parse and drop noise
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    _drop_boilerplate_tags(soup)

    # Raw text with stable separators
    text = soup.get_text(separator="\n")

    # Decode entities (&nbsp; -> \xa0, etc.) then normalize typography/newlines
    text = unescape(text)
    text = text.replace("\ufeff", "")  # strip BOM if present
    text = re.sub(r"\n{3,}", "\n\n", text)  # collapse huge gaps
    text = _strip_repeated_edges(text)

    # Run through canonical normalizer (quotes/dashes/nbsp/newlines)
    text = normalize_text(text)
    return text
