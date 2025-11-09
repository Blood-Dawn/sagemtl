"""
SageCrawler - First-party novel crawler for SageMTL

Built-in solution that supports:
- URL or search query input
- Multiple source adapters (FanMTL, generic, etc.)
- Chapter range selection
- Multiple export formats (JSON, EPUB, HTML, TXT, + Calibre bridge)
- Polite crawling (robots.txt, rate limiting, retries)
- Resume support
"""

from .core.engine import CrawlEngine
from .core.models import NovelTOC, ChapterContent, CrawlOptions, SearchHit

__version__ = "1.0.0"

__all__ = [
    "CrawlEngine",
    "NovelTOC",
    "ChapterContent",
    "CrawlOptions",
    "SearchHit",
]
