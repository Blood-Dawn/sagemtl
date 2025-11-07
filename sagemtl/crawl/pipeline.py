"""HTML crawling helpers used by the CLI and HTTP API."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
from collections import Counter
import re
from typing import Iterable, Iterator, List, Sequence

from bs4 import BeautifulSoup, Tag

from sagemtl.clean.text_normalize import NormalizeOptions, normalize_text

__all__ = [
    "CrawlBlock",
    "CrawlOptions",
    "CrawlResult",
    "crawl_html",
]


_STRUCTURAL_SELECTORS = ("header", "footer", "nav", "aside")
_BOILERPLATE_RE = re.compile(
    r"(ad|adsense|advert|breadcrumb|copyright|cookie|footer|header|menu|masthead|navbar|nav|newsletter|promo|subscribe)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class CrawlOptions:
    depth: int = 0
    render_js: bool = False
    allow_selectors: Sequence[str] = field(default_factory=tuple)
    block_selectors: Sequence[str] = field(default_factory=tuple)
    normalize: NormalizeOptions = field(default_factory=lambda: NormalizeOptions(ensure_trailing_lf=False))


@dataclass(slots=True)
class CrawlBlock:
    order: int
    text: str
    css_path: str
    xpath: str
    lang: str | None


@dataclass(slots=True)
class CrawlResult:
    source: str
    blocks: List[CrawlBlock]
    meta: dict[str, object]

    @property
    def text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks if block.text)


def _apply_blocklist(soup: BeautifulSoup, selectors: Iterable[str]) -> None:
    for selector in selectors:
        for tag in soup.select(selector):
            tag.decompose()


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
        attr_values = list(_iter_attr_values(tag.get("class"))) + list(_iter_attr_values(tag.get("id")))
        if any(_BOILERPLATE_RE.search(val) for val in attr_values):
            tag.decompose()


def _iter_candidates(soup: BeautifulSoup, allow: Sequence[str]) -> Iterator[Tag]:
    if allow:
        seen: set[int] = set()
        for selector in allow:
            for tag in soup.select(selector):
                if id(tag) in seen:
                    continue
                seen.add(id(tag))
                yield tag
        return

    root = soup.find("article") or soup.find("main") or soup.body or soup
    for tag in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"], recursive=True):
        yield tag


def _css_path(tag: Tag) -> str:
    parts: List[str] = []
    current: Tag | None = tag
    while current and isinstance(current, Tag):
        name = current.name or "*"
        index = 1
        sibling = current.previous_sibling
        while sibling is not None:
            if isinstance(sibling, Tag) and sibling.name == name:
                index += 1
            sibling = sibling.previous_sibling
        if index > 1:
            parts.append(f"{name}:nth-of-type({index})")
        else:
            parts.append(name)
        current = current.parent  # type: ignore[assignment]
    return " > ".join(reversed(parts))


def _xpath(tag: Tag) -> str:
    parts: List[str] = []
    current: Tag | None = tag
    while current is not None and isinstance(current, Tag):
        name = current.name or "*"
        index = 1
        sibling = current.previous_sibling
        while sibling is not None:
            if isinstance(sibling, Tag) and sibling.name == name:
                index += 1
            sibling = sibling.previous_sibling
        parts.append(f"/{name}[{index}]")
        current = current.parent  # type: ignore[assignment]
    return "".join(reversed(parts)) or "/"


def _resolve_lang(tag: Tag) -> str | None:
    current: Tag | None = tag
    while current is not None and isinstance(current, Tag):
        lang = current.get("lang") or current.get("xml:lang")
        if lang:
            return lang
        current = current.parent  # type: ignore[assignment]
    return None


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

    return "\n".join(lines[start:end])


def crawl_html(html: str, *, source: str = "", options: CrawlOptions | None = None) -> CrawlResult:
    opts = options or CrawlOptions()
    cleaned_html = html.replace("\ufeff", "")
    soup = BeautifulSoup(cleaned_html, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    _apply_blocklist(soup, opts.block_selectors)
    _drop_boilerplate_tags(soup)

    blocks: List[CrawlBlock] = []
    order = 1
    for tag in _iter_candidates(soup, list(opts.allow_selectors)):
        text = tag.get_text(separator="\n")
        text = unescape(text)
        normalized = normalize_text(text, options=opts.normalize).strip()
        if not normalized:
            continue
        blocks.append(
            CrawlBlock(
                order=order,
                text=normalized,
                css_path=_css_path(tag),
                xpath=_xpath(tag),
                lang=_resolve_lang(tag),
            )
        )
        order += 1

    meta = {
        "depth": opts.depth,
        "render_js": opts.render_js,
        "block_count": len(blocks),
    }

    if not blocks:
        fallback = normalize_text(
            _strip_repeated_edges(soup.get_text(separator="\n")),
            options=opts.normalize,
        ).strip()
        if fallback:
            blocks.append(
                CrawlBlock(
                    order=1,
                    text=fallback,
                    css_path="body",
                    xpath="/html/body",
                    lang=soup.html.get("lang") if soup.html else None,
                )
            )
            meta["block_count"] = 1

    return CrawlResult(source=source, blocks=blocks, meta=meta)
