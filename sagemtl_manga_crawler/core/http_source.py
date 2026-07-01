"""ParsedHttpSource: a Mihon-style request/parse template base.

Mirrors Tachiyomi/Mihon's HttpSource/ParsedHttpSource pattern (the request builder
and the parse step are split) so a user can add a new source in a few lines by
overriding the parse methods. THIS IS A TEMPLATE: no concrete site is bundled.
Default content type is JSON; override ``_fetch`` (e.g. parse HTML with
BeautifulSoup) for scraped sources. Frame any source you add for content you have a
right to access (see LICENSES-MANGA.md / spec section 16).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from .fetch import MangaFetcher
from .models import ChapterRef, PageImage, SeriesResult
from .source_base import MangaSource

__all__ = ["ParsedHttpSource"]


class ParsedHttpSource(MangaSource):
    """Template source: wire request/parse, implement the parse methods.

    Subclasses set ``base_url``/``name``/``lang`` and implement ``search_parse``,
    ``series_parse``, and ``page_list_parse``; optionally override the ``*_request``
    builders and ``_fetch`` (JSON by default).
    """

    def __init__(self, fetcher: Optional[MangaFetcher] = None) -> None:
        self._fetcher = fetcher or MangaFetcher()

    # -- request builders (override to customize) ---------------------------

    def search_request(self, query: str) -> tuple[str, Optional[dict]]:
        raise NotImplementedError("override search_request")

    def series_request(self, url: str) -> str:
        return url

    def page_list_request(self, chapter: ChapterRef) -> str:
        return chapter.url

    # -- parse steps (MUST override) ----------------------------------------

    def search_parse(self, payload) -> list[SeriesResult]:
        raise NotImplementedError("override search_parse")

    def series_parse(self, payload, url: str) -> tuple[dict, list[ChapterRef]]:
        raise NotImplementedError("override series_parse")

    def page_list_parse(self, payload, chapter: ChapterRef) -> list[PageImage]:
        raise NotImplementedError("override page_list_parse")

    # -- fetch (JSON by default; override for HTML) -------------------------

    def _fetch(self, url: str, params: Optional[dict] = None):
        return self._fetcher.get_json(url, params=params)

    # -- MangaSource implementation -----------------------------------------

    def search(self, query: str) -> Iterable[SeriesResult]:
        url, params = self.search_request(query)
        return self.search_parse(self._fetch(url, params))

    def read_series(self, url: str) -> tuple[dict, list[ChapterRef]]:
        return self.series_parse(self._fetch(self.series_request(url)), url)

    def fetch_page_list(self, chapter: ChapterRef) -> list[PageImage]:
        return self.page_list_parse(self._fetch(self.page_list_request(chapter)), chapter)

    def download_page(self, page: PageImage, dest: Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = self._fetcher.get_bytes(page.url, referer=page.referer, headers=page.headers or None)
        if not data:
            raise RuntimeError(f"empty download for page {page.index} ({page.url})")
        dest.write_bytes(data)
        return dest
