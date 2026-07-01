"""MangaDex source (flagship, official free REST API).

No scraping and no Cloudflare: search via ``/manga``, chapters via
``/manga/{id}/feed``, image delivery via ``/at-home/server/{chapterId}``. The
at-home ``baseUrl`` expires in ~15 min (re-request on 403). For images served by a
non-``mangadex.org`` node, a small success/failure report is POSTed to
``api.mangadex.network/report`` to keep the volunteer CDN healthy. Read endpoints
are public (no auth). Honors ~5 req/s, credits MangaDex and scanlation groups, and
never spoofs the User-Agent.

The network methods are split into pure parse helpers (``build_page_urls``,
``search_parse``, ``feed_parse``) so URL/JSON handling is unit-testable without
network. See ``MANGA_MODULE_BUILD_SPEC.md`` section 9.3.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlsplit

from ..core.fetch import MangaFetcher
from ..core.models import ChapterRef, PageImage, SeriesResult
from ..core.source_base import MangaSource

__all__ = ["MangaDexSource", "build_page_urls", "search_parse", "feed_parse", "extract_id"]

API_BASE = "https://api.mangadex.org"
COVERS_BASE = "https://uploads.mangadex.org/covers"
REPORT_URL = "https://api.mangadex.network/report"
SITE_BASE = "https://mangadex.org"
_UUID_LEN = 36


def extract_id(url_or_id: str) -> str:
    """Extract a MangaDex UUID from a title/chapter URL or a bare id."""

    value = (url_or_id or "").strip()
    if "/" not in value:
        return value
    parts = [p for p in urlsplit(value).path.split("/") if p]
    for i, part in enumerate(parts):
        if part in ("title", "manga", "chapter") and i + 1 < len(parts):
            return parts[i + 1]
    # fall back to the last path segment that looks like a uuid
    for part in reversed(parts):
        if len(part) == _UUID_LEN and part.count("-") == 4:
            return part
    return parts[-1] if parts else value


def _pick_title(title: dict, alt_titles: list) -> str:
    if isinstance(title, dict) and title:
        if "en" in title:
            return title["en"]
        return next(iter(title.values()))
    for alt in alt_titles or []:
        if isinstance(alt, dict) and alt:
            return alt.get("en") or next(iter(alt.values()))
    return ""


def _cover_url(item: dict) -> Optional[str]:
    manga_id = item.get("id")
    for rel in item.get("relationships", []):
        if rel.get("type") == "cover_art":
            file_name = (rel.get("attributes") or {}).get("fileName")
            if file_name and manga_id:
                return f"{COVERS_BASE}/{manga_id}/{file_name}"
    return None


def search_parse(payload: dict) -> list[SeriesResult]:
    """Parse a ``/manga`` search response into SeriesResult rows."""

    results: list[SeriesResult] = []
    for item in payload.get("data", []):
        attrs = item.get("attributes", {})
        title = _pick_title(attrs.get("title", {}), attrs.get("altTitles", []))
        results.append(
            SeriesResult(
                title=title,
                url=f"{SITE_BASE}/title/{item.get('id', '')}",
                source="mangadex",
                cover=_cover_url(item),
            )
        )
    return results


def feed_parse(payload: dict) -> list[ChapterRef]:
    """Parse a ``/manga/{id}/feed`` response into ChapterRef rows."""

    chapters: list[ChapterRef] = []
    for item in payload.get("data", []):
        attrs = item.get("attributes", {})
        chapters.append(
            ChapterRef(
                id=item.get("id", ""),
                number=attrs.get("chapter") or "",
                title=attrs.get("title") or "",
                url=f"{SITE_BASE}/chapter/{item.get('id', '')}",
                lang=attrs.get("translatedLanguage") or "",
            )
        )
    return chapters


def _url_ext(url: str) -> str:
    name = urlsplit(url).path.rsplit("/", 1)[-1]
    if "." in name:
        return "." + name.rsplit(".", 1)[-1].lower()
    return ".jpg"


def build_page_urls(at_home: dict, *, data_saver: bool = False) -> list[str]:
    """Build full page image URLs from an ``/at-home/server`` response."""

    base = at_home["baseUrl"].rstrip("/")
    chapter = at_home["chapter"]
    digest = chapter["hash"]
    key = "dataSaver" if data_saver else "data"
    segment = "data-saver" if data_saver else "data"
    return [f"{base}/{segment}/{digest}/{name}" for name in chapter.get(key, [])]


class MangaDexSource(MangaSource):
    """MangaDex official-API source."""

    base_url = API_BASE
    name = "mangadex"
    lang = "en"

    def __init__(
        self,
        fetcher: Optional[MangaFetcher] = None,
        *,
        data_saver: bool = False,
        translated_language: str = "en",
        report: bool = True,
    ) -> None:
        # /at-home is limited to 40/min; keep the default request rate conservative.
        self._fetcher = fetcher or MangaFetcher(rate_per_sec=4.0)
        self.data_saver = data_saver
        self.translated_language = translated_language
        self.report = report
        self._report_failures = 0

    # -- search / metadata --------------------------------------------------

    def search(self, query: str) -> Iterable[SeriesResult]:
        payload = self._fetcher.get_json(
            f"{API_BASE}/manga",
            params={"title": query, "limit": 20, "includes[]": "cover_art"},
        )
        return search_parse(payload)

    def read_series(self, url: str) -> tuple[dict, list[ChapterRef]]:
        manga_id = extract_id(url)
        meta_payload = self._fetcher.get_json(
            f"{API_BASE}/manga/{manga_id}", params={"includes[]": "cover_art"}
        )
        meta_item = meta_payload.get("data", {})
        attrs = meta_item.get("attributes", {})
        meta = {
            "id": manga_id,
            "title": _pick_title(attrs.get("title", {}), attrs.get("altTitles", [])),
            "cover": _cover_url(meta_item),
            "lang": (attrs.get("originalLanguage") or ""),
        }

        chapters: list[ChapterRef] = []
        offset = 0
        while True:
            page = self._fetcher.get_json(
                f"{API_BASE}/manga/{manga_id}/feed",
                params={
                    "translatedLanguage[]": self.translated_language,
                    "order[chapter]": "asc",
                    "limit": 100,
                    "offset": offset,
                },
            )
            chapters.extend(feed_parse(page))
            total = int(page.get("total", 0))
            offset += 100
            if offset >= total or not page.get("data"):
                break
        return meta, chapters

    # -- pages --------------------------------------------------------------

    def _at_home(self, chapter_id: str) -> dict:
        return self._fetcher.get_json(f"{API_BASE}/at-home/server/{chapter_id}")

    def fetch_page_list(self, chapter: ChapterRef) -> list[PageImage]:
        at_home = self._at_home(chapter.id)
        urls = build_page_urls(at_home, data_saver=self.data_saver)
        referer = chapter.url or SITE_BASE
        return [
            PageImage(index=i, url=url, referer=referer, headers={})
            for i, url in enumerate(urls)
        ]

    def download_page(self, page: PageImage, dest: Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        success = True
        data = b""
        try:
            data = self._fetcher.get_bytes(page.url, referer=page.referer)
        except Exception:
            success = False
        duration_ms = int((time.monotonic() - start) * 1000)
        self._maybe_report(page.url, success, len(data), duration_ms)
        if not success or not data:
            raise RuntimeError(f"failed to download page {page.index} from {page.url}")
        dest.write_bytes(data)
        return dest

    def download_chapter(self, chapter: ChapterRef, dest_dir: Path, *, max_athome_refresh: int = 3):
        """Download all pages of a chapter, re-requesting at-home on a stale 403.

        The at-home ``baseUrl`` expires (~15 min); a 403 mid-chapter means the URLs
        are stale, so we re-fetch ``/at-home/server`` and retry. A long chapter can
        outlive several baseUrl windows, so the refresh budget counts CONSECUTIVE
        failures at the current page (reset on each successful page); a persistent
        403 at one page still trips the budget, so the loop always terminates.
        Returns the list of written page paths.
        """

        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        pages = self.fetch_page_list(chapter)
        saved: list[Path] = []
        consecutive_refreshes = 0
        i = 0
        while i < len(pages):
            page = pages[i]
            dest = dest_dir / f"{page.index + 1:03d}{_url_ext(page.url)}"
            try:
                self.download_page(page, dest)
                saved.append(dest)
                i += 1
                consecutive_refreshes = 0  # forward progress resets the budget
            except Exception:
                if consecutive_refreshes >= max_athome_refresh:
                    raise
                consecutive_refreshes += 1
                pages = self.fetch_page_list(chapter)  # fresh baseUrl
        return saved

    def _maybe_report(self, url: str, success: bool, num_bytes: int, duration_ms: int) -> None:
        if not self.report:
            return
        host = urlsplit(url).netloc
        # Only report images served by the volunteer CDN, never mangadex.org nodes.
        if host.endswith("mangadex.org"):
            return
        payload = {
            "url": url,
            "success": success,
            "cached": False,
            "bytes": num_bytes,
            "duration": duration_ms,
        }
        # Fire-and-forget (short timeout, no retries). If the report endpoint is
        # unreachable, give up after a few failures so it never slows downloads.
        status = self._fetcher.report(REPORT_URL, payload)
        if status == 200:
            self._report_failures = 0
        else:
            self._report_failures += 1
            if self._report_failures >= 3:
                self.report = False
