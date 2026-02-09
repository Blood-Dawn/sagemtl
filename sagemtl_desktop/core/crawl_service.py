"""
Crawler orchestration helpers used by the desktop UI.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .crawler_interface import CrawlerInterface, CrawledNovel


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
        return await crawler.discover_chapters(url, progress_callback)

    @staticmethod
    def choose_download_strategy(
        discovered_chapters: List[Tuple[str, str]],
        selected_chapters: List[Tuple[str, str]]
    ) -> Tuple[bool, Optional[int]]:
        """
        Decide whether we can use the wrapper full-download path.

        Returns:
            (use_wrapper_fetch_novel, max_chapters_for_wrapper)
        """
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
        progress_callback=None
    ) -> CrawledNovel:
        use_wrapper_fetch, max_chapters = self.choose_download_strategy(
            discovered_chapters,
            selected_chapters
        )

        if use_wrapper_fetch:
            return await crawler.fetch_novel(
                url,
                progress_callback=progress_callback,
                max_chapters=max_chapters
            )

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
