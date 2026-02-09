"""
Crawler orchestration helpers used by the desktop UI.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from .crawler_interface import CrawlerInterface, CrawledNovel
from .crawl_settings import CrawlSettings
from .epub_writer import EPUBWriter


class CrawlService:
    """
    Encapsulates crawl/discovery flow decisions away from MainWindow.
    """

    async def discover_chapters(
        self,
        crawler: CrawlerInterface,
        url: str,
        progress_callback=None
    ) -> Tuple[str, Optional[str], List[Tuple[str, str]]]:
        if progress_callback:
            progress_callback(0, 100, "Stage 1/3: Preparing chapter discovery...")
        return await crawler.discover_chapters(url, progress_callback)

    async def discover_chapter_count(
        self,
        crawler: CrawlerInterface,
        url: str
    ) -> Optional[int]:
        """
        Discover and return chapter count for a URL without starting downloads.
        """
        _, _, chapters = await self.discover_chapters(crawler, url)
        return len(chapters) if chapters is not None else None

    @staticmethod
    def choose_download_strategy(
        discovered_chapters: List[Tuple[str, str]],
        selected_chapters: List[Tuple[str, str]],
        force_selected_download: bool = False
    ) -> Tuple[bool, Optional[int]]:
        """
        Decide whether we can use the wrapper full-download path.

        Returns:
            (use_wrapper_fetch_novel, max_chapters_for_wrapper)
        """
        if force_selected_download:
            return False, None

        if not selected_chapters:
            return False, None

        if len(selected_chapters) == len(discovered_chapters):
            return True, None

        # First-N selection can still use wrapper fetch_novel with max_chapters.
        if discovered_chapters[: len(selected_chapters)] == selected_chapters:
            return True, len(selected_chapters)

        return False, None

    async def download_selected_chapters(
        self,
        crawler: CrawlerInterface,
        url: str,
        title: str,
        author: Optional[str],
        discovered_chapters: List[Tuple[str, str]],
        selected_chapters: List[Tuple[str, str]],
        progress_callback=None,
        force_selected_download: bool = False
    ) -> CrawledNovel:
        if progress_callback:
            progress_callback(0, 100, "Stage 1/3: Selecting download strategy...")

        use_wrapper_fetch, max_chapters = self.choose_download_strategy(
            discovered_chapters,
            selected_chapters,
            force_selected_download=force_selected_download
        )

        if use_wrapper_fetch:
            if progress_callback:
                strategy_text = (
                    "wrapper full download"
                    if max_chapters is None
                    else f"wrapper first-{max_chapters} download"
                )
                progress_callback(5, 100, f"Stage 2/3: Using {strategy_text} path...")
            return await crawler.fetch_novel(
                url,
                progress_callback=progress_callback,
                max_chapters=max_chapters
            )

        if progress_callback:
            progress_callback(5, 100, "Stage 2/3: Using selected-chapter fallback path...")
        return await crawler.fetch_selected_chapters(
            url=url,
            title=title,
            author=author,
            selected_chapters=selected_chapters,
            progress_callback=progress_callback
        )

    @staticmethod
    def build_full_text(novel: CrawledNovel) -> str:
        full_text_parts: List[str] = []
        for chapter in novel.chapters:
            full_text_parts.append(f"=== {chapter.title} ===\n\n")
            full_text_parts.append(chapter.content)
            full_text_parts.append("\n\n")
        return "".join(full_text_parts)

    @staticmethod
    def filter_pending_chapters_for_resume(
        selected_chapters: List[Tuple[str, str]],
        existing_chapter_urls: List[str]
    ) -> Tuple[List[Tuple[str, str]], int]:
        """Skip selected chapters already present in existing novel data."""
        if not selected_chapters:
            return [], 0
        existing_url_set = {url for url in existing_chapter_urls if url}
        if not existing_url_set:
            return selected_chapters, 0

        pending = [chapter for chapter in selected_chapters if chapter[0] not in existing_url_set]
        skipped = len(selected_chapters) - len(pending)
        return pending, skipped

    @staticmethod
    def normalize_batch_urls(raw_text: str) -> List[str]:
        """Extract and deduplicate HTTP(S) URLs from free-form batch input."""
        candidates = [part.strip() for part in re.split(r"[\r\n,;]+", raw_text or "")]
        urls: List[str] = []
        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            parsed = urlparse(candidate)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            urls.append(candidate)
        return urls

    @staticmethod
    def site_key(url: str) -> str:
        """Return host key used for site-specific profile storage."""
        parsed = urlparse(url.strip())
        return parsed.netloc.lower()

    @staticmethod
    def default_epub_output_dir() -> str:
        return str(Path.home() / "Documents" / "Webnovels" / "epub")

    @staticmethod
    def export_crawled_epub(
        novel: CrawledNovel,
        output_dir: str,
        author_fallback: str = "Unknown"
    ) -> str:
        """
        Export crawled chapters directly to EPUB without intermediate conversion.
        """
        writer = EPUBWriter()
        if not writer.is_available():
            raise RuntimeError("EPUB export is unavailable (ebooklib not installed)")

        chapters = [(chapter.title, chapter.content) for chapter in novel.chapters if chapter.content]
        if not chapters:
            raise ValueError("No chapter content available for EPUB export")

        return writer.create_epub(
            title=novel.title,
            chapters=chapters,
            output_path=output_dir,
            author=novel.author or author_fallback
        )

    @staticmethod
    def get_site_profile(settings_backend, url: str) -> CrawlSettings:
        """
        Load site-specific crawl settings from a settings backend (QSettings-like).
        """
        key = CrawlService.site_key(url)
        raw_value = settings_backend.value(f"crawl_site_profiles/{key}", {})
        if isinstance(raw_value, str):
            try:
                import json
                raw_value = json.loads(raw_value)
            except Exception:
                raw_value = {}
        return CrawlSettings.from_dict(raw_value)

    @staticmethod
    def save_site_profile(settings_backend, url: str, crawl_settings: CrawlSettings):
        """
        Persist site-specific crawl settings to a settings backend (QSettings-like).
        """
        key = CrawlService.site_key(url)
        settings_backend.setValue(f"crawl_site_profiles/{key}", crawl_settings.to_dict())
