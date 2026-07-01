"""Source plugin contract (spec 9.1).

``MangaSource`` is the ABC every source implements. Network methods are split
into a request builder and a parse step (Mihon's ``*_request`` / ``*_parse``
pattern) so HTML, JSON, and API sources share plumbing. Concrete sources and the
default ``download_page`` land in Phase 7; the abstract surface is defined here so
the registry and models stay decoupled.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 9.1.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from .models import ChapterRef, PageImage, SeriesResult

__all__ = ["MangaSource"]


class MangaSource(ABC):
    """Abstract base for a page-image source."""

    base_url: str = ""
    lang: str = ""                 # 'ja','ko','zh','en',...
    name: str = ""
    is_webtoon: bool = False
    nsfw: bool = False
    can_search: bool = True

    @abstractmethod
    def search(self, query: str) -> Iterable[SeriesResult]:
        """Return series matching ``query``."""

    @abstractmethod
    def read_series(self, url: str) -> tuple[dict, list[ChapterRef]]:
        """Return ``(meta, chapters)`` for a series URL."""

    @abstractmethod
    def fetch_page_list(self, chapter: ChapterRef) -> list[PageImage]:
        """Return the ordered page images for a chapter (the core manga method)."""

    def download_page(self, page: PageImage, dest: Path) -> Path:
        """Download a page, preserving format and setting Referer (Phase 7)."""

        raise NotImplementedError("download_page is implemented in Phase 7.")
