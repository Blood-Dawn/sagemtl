"""Legacy helpers that wrap the crawl pipeline."""

from __future__ import annotations

from .pipeline import CrawlOptions, crawl_html

__all__ = ["CrawlOptions", "crawl_html", "extract_main_text"]


def extract_main_text(html: str, *, options: CrawlOptions | None = None) -> str:
    """Return the concatenated text content for backwards compatibility."""

    result = crawl_html(html, options=options)
    text = result.text
    if not text.endswith("\n"):
        text += "\n"
    return text
