"""Suwayomi-Server bridge source.

Suwayomi-Server runs the actual Mihon/Tachiyomi extension APKs on the JVM and
exposes them over an HTTP API, so this source reaches the whole Mihon catalog
WITHOUT SageMTL bundling any scraper -- the user runs their own Suwayomi instance
with their chosen extensions (the spec's recommended "bring your own extensions"
path, section 9.4 / 16). Targets the Suwayomi REST compatibility API; exact field
shapes vary slightly by Suwayomi version, so parsing is tolerant.

Pure parse helpers (search/series/pages) are unit-testable without a server.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

from ..core.fetch import MangaFetcher
from ..core.models import ChapterRef, PageImage, SeriesResult
from ..core.source_base import MangaSource

__all__ = [
    "SuwayomiSource",
    "suwayomi_search_parse",
    "suwayomi_series_parse",
    "suwayomi_page_list",
]

_MANGA_RE = re.compile(r"/manga/(\d+)")
_CHAPTER_RE = re.compile(r"/manga/(\d+)/chapter/(\d+)")


def _abs_cover(server: str, thumb) -> Optional[str]:
    if not thumb:
        return None
    return thumb if str(thumb).startswith("http") else f"{server}{thumb}"


def suwayomi_search_parse(payload: dict, server: str) -> list[SeriesResult]:
    results: list[SeriesResult] = []
    items = payload.get("mangaList", payload.get("data", [])) if isinstance(payload, dict) else (payload or [])
    for item in items:
        manga_id = item.get("id")
        results.append(
            SeriesResult(
                title=item.get("title", ""),
                url=f"{server}/api/v1/manga/{manga_id}",
                source="suwayomi",
                cover=_abs_cover(server, item.get("thumbnailUrl")),
            )
        )
    return results


def _chapter_items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("chapters", payload.get("data", []))
    return []


def suwayomi_series_parse(meta: dict, chapters_payload, manga_id, server: str) -> tuple[dict, list[ChapterRef]]:
    meta = meta or {}
    info = {
        "id": str(manga_id),
        "title": meta.get("title", ""),
        "cover": _abs_cover(server, meta.get("thumbnailUrl")),
        "lang": meta.get("sourceLang", meta.get("lang", "")),
    }
    chapters: list[ChapterRef] = []
    for item in _chapter_items(chapters_payload):
        index = item.get("index", item.get("chapterNumber"))
        chapters.append(
            ChapterRef(
                id=str(index),
                number=str(item.get("chapterNumber", index) or ""),
                title=item.get("name", item.get("title", "")) or "",
                url=f"{server}/api/v1/manga/{manga_id}/chapter/{index}",
                lang=info["lang"] or "en",
            )
        )
    return info, chapters


def suwayomi_page_list(payload: dict, manga_id, chapter_index, server: str) -> list[PageImage]:
    page_count = int((payload or {}).get("pageCount", 0))
    return [
        PageImage(
            index=i,
            url=f"{server}/api/v1/manga/{manga_id}/chapter/{chapter_index}/page/{i}",
            referer=server,
        )
        for i in range(page_count)
    ]


class SuwayomiSource(MangaSource):
    """Bridge to a user-run Suwayomi-Server (their own Mihon extensions)."""

    name = "suwayomi"
    lang = "en"
    base_url = ""  # set at runtime from config (server URL)

    def __init__(self, server_url: str, source_id: str = "", fetcher: Optional[MangaFetcher] = None) -> None:
        self.server_url = (server_url or "").rstrip("/")
        self.base_url = self.server_url
        self.source_id = source_id
        self._fetcher = fetcher or MangaFetcher()

    def search(self, query: str) -> Iterable[SeriesResult]:
        if not self.server_url or not self.source_id:
            raise RuntimeError("Suwayomi server URL and source id must be configured")
        payload = self._fetcher.get_json(
            f"{self.server_url}/api/v1/source/{self.source_id}/search",
            params={"searchTerm": query, "pageNum": 1},
        )
        return suwayomi_search_parse(payload, self.server_url)

    def read_series(self, url: str) -> tuple[dict, list[ChapterRef]]:
        match = _MANGA_RE.search(url)
        manga_id = match.group(1) if match else url.rstrip("/").rsplit("/", 1)[-1]
        meta = self._fetcher.get_json(f"{self.server_url}/api/v1/manga/{manga_id}/")
        chapters = self._fetcher.get_json(f"{self.server_url}/api/v1/manga/{manga_id}/chapters")
        return suwayomi_series_parse(meta, chapters, manga_id, self.server_url)

    def fetch_page_list(self, chapter: ChapterRef) -> list[PageImage]:
        match = _CHAPTER_RE.search(chapter.url)
        if match:
            manga_id, index = match.group(1), match.group(2)
        else:
            manga_id, index = "", chapter.id
        payload = self._fetcher.get_json(
            f"{self.server_url}/api/v1/manga/{manga_id}/chapter/{index}"
        )
        return suwayomi_page_list(payload, manga_id, index, self.server_url)

    def download_page(self, page: PageImage, dest: Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = self._fetcher.get_bytes(page.url, referer=page.referer)
        if not data:
            raise RuntimeError(f"empty download for page {page.index} ({page.url})")
        dest.write_bytes(data)
        return dest
