"""Manga library persistence (mirrors ``novel_library.py``).

Disk layout under ``~/.sagemtl/library/manga/`` (spec 10.2)::

    manga/
      index.json                    # series metadata only (fast listing)
      {series_id}/
        series.json                 # full MangaSeries (chapters + page records)
        cover.jpg
        raw/{chapter_id}/{page}.ext  # downloaded originals
        out/{chapter_id}/{page}.png  # rendered translated pages

Image bytes live on disk; ``index.json`` holds metadata only so the library list
loads fast. ``upsert_series_from_crawled`` resumes by ``source_url`` and honors a
title lock so user renames persist across re-crawls (same semantics as the novel
library). Per-series glossaries reuse ``GlossaryManager`` keyed by ``series_id``.

No heavy imports; pure stdlib + the manga dataclasses.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import MangaChapter, MangaSeries

__all__ = ["MangaLibrary"]


def _default_storage_path() -> Path:
    return Path.home() / ".sagemtl" / "library" / "manga"


class MangaLibrary:
    """Persistent storage for manga series (metadata + on-disk images)."""

    def __init__(self, storage_path: Optional[str | Path] = None) -> None:
        self.storage_dir = Path(storage_path) if storage_path else _default_storage_path()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self._series: dict[str, MangaSeries] = {}
        self._load()

    # -- persistence --------------------------------------------------------

    def _load(self) -> None:
        if not self.index_file.exists():
            return
        try:
            index = json.loads(self.index_file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return
        for entry in index.get("series", []):
            series_id = entry.get("series_id")
            if not series_id:
                continue
            series_json = self.series_dir(series_id) / "series.json"
            if series_json.exists():
                try:
                    data = json.loads(series_json.read_text(encoding="utf-8"))
                    self._series[series_id] = MangaSeries.from_dict(data)
                except (ValueError, OSError):
                    continue

    def _save_index(self) -> None:
        index = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "series": [
                {
                    "series_id": s.series_id,
                    "title": s.title,
                    "source_url": s.source_url,
                    "source_name": s.source_name,
                    "cover_path": s.cover_path,
                    "lang": s.lang,
                    "chapter_count": len(s.chapters),
                    "updated_at": s.updated_at,
                }
                for s in self._series.values()
            ],
        }
        self.index_file.write_text(
            json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _save_series(self, series: MangaSeries) -> None:
        series.updated_at = datetime.now().isoformat()
        path = self.series_dir(series.series_id) / "series.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(series.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # -- path helpers -------------------------------------------------------

    def series_dir(self, series_id: str) -> Path:
        return self.storage_dir / series_id

    def cover_path(self, series_id: str) -> Path:
        return self.series_dir(series_id) / "cover.jpg"

    def raw_chapter_dir(self, series_id: str, chapter_id: str) -> Path:
        return self.series_dir(series_id) / "raw" / chapter_id

    def out_chapter_dir(self, series_id: str, chapter_id: str) -> Path:
        return self.series_dir(series_id) / "out" / chapter_id

    def save_page_image(
        self, series_id: str, chapter_id: str, page_index: int, data: bytes,
        *, ext: str = "png", kind: str = "raw",
    ) -> Path:
        """Write a raw or rendered page image to disk and return its path."""

        base = self.raw_chapter_dir(series_id, chapter_id) if kind == "raw" else self.out_chapter_dir(series_id, chapter_id)
        base.mkdir(parents=True, exist_ok=True)
        dest = base / f"{page_index + 1:03d}.{ext.lstrip('.')}"
        dest.write_bytes(data)
        return dest

    # -- CRUD ---------------------------------------------------------------

    def add_series(self, series: MangaSeries) -> MangaSeries:
        if not series.series_id:
            series.series_id = str(uuid.uuid4())[:8]
        self._series[series.series_id] = series
        self._save_series(series)
        self._save_index()
        return series

    def update_series(self, series: MangaSeries) -> MangaSeries:
        self._series[series.series_id] = series
        self._save_series(series)
        self._save_index()
        return series

    def get_series(self, series_id: str) -> Optional[MangaSeries]:
        return self._series.get(series_id)

    def get_series_by_url(self, source_url: str) -> Optional[MangaSeries]:
        return next((s for s in self._series.values() if s.source_url == source_url), None)

    def get_all_series(self) -> list[MangaSeries]:
        return list(self._series.values())

    def remove_series(self, series_id: str) -> bool:
        if series_id not in self._series:
            return False
        del self._series[series_id]
        import shutil

        target = self.series_dir(series_id)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        self._save_index()
        return True

    @property
    def series_count(self) -> int:
        return len(self._series)

    # -- crawler integration ------------------------------------------------

    @staticmethod
    def _chapter_identity(source_url: str, number: str, title: str, chapter_id: str) -> str:
        """Stable merge key from durable fields (never the minted uuid).

        Mirrors ``novel_library._chapter_identity`` so re-crawls dedup even when a
        source emits only chapter number + title (no stable url/id).
        """
        if source_url and source_url.strip():
            return f"url:{source_url.strip()}"
        num = (number or "").strip()
        normalized_title = (title or "").strip().lower()
        if num or normalized_title:
            return f"num:{num}|{normalized_title}"
        return f"id:{chapter_id}"

    @staticmethod
    def _chapter_from_ref(ref) -> MangaChapter:
        return MangaChapter(
            chapter_id=getattr(ref, "id", "") or str(uuid.uuid4())[:8],
            number=getattr(ref, "number", "") or "",
            title=getattr(ref, "title", "") or "",
            source_url=getattr(ref, "url", "") or "",
            lang=getattr(ref, "lang", "") or "",
            pages=[],
        )

    def upsert_series_from_crawled(
        self,
        meta: dict,
        chapters,
        source_url: str,
        source_name: str = "mangadex",
        *,
        resume_existing: bool = True,
    ) -> MangaSeries:
        """Create or merge a series from crawler output (meta dict + ChapterRefs)."""

        existing = self.get_series_by_url(source_url) if resume_existing else None
        title = meta.get("title", "") if isinstance(meta, dict) else ""
        cover = (meta.get("cover") or "") if isinstance(meta, dict) else ""
        lang = (meta.get("lang") or "") if isinstance(meta, dict) else ""

        if existing is None:
            series = MangaSeries(
                series_id=str(uuid.uuid4())[:8],
                title=title,
                source_url=source_url,
                source_name=source_name,
                cover_path=cover,
                lang=lang,
                chapters=[self._chapter_from_ref(c) for c in chapters],
            )
            return self.add_series(series)

        # merge by a STABLE identity (durable fields, not the minted chapter uuid)
        index = {
            self._chapter_identity(ch.source_url, ch.number, ch.title, ch.chapter_id): ch
            for ch in existing.chapters
        }
        for ref in chapters:
            chapter = self._chapter_from_ref(ref)
            key = self._chapter_identity(
                chapter.source_url, chapter.number, chapter.title, chapter.chapter_id
            )
            if key in index:
                target = index[key]  # keep the existing chapter_id + pages
                target.number = chapter.number or target.number
                target.title = chapter.title or target.title
                target.lang = chapter.lang or target.lang
            else:
                existing.chapters.append(chapter)
                index[key] = chapter

        if not existing.title_locked and title:
            existing.title = title
        if cover:
            existing.cover_path = cover
        return self.update_series(existing)

    def set_title(self, series_id: str, title: str, *, lock: bool = True) -> Optional[MangaSeries]:
        """Rename a series and (by default) lock the title against re-crawl overwrite."""

        series = self._series.get(series_id)
        if not series:
            return None
        series.title = title
        series.title_locked = lock
        return self.update_series(series)
