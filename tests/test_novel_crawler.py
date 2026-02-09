"""Regression tests for desktop crawl orchestration logic."""

from __future__ import annotations

from typing import List, Optional, Tuple

import pytest

from sagemtl_desktop.core.crawl_service import CrawlService
from sagemtl_desktop.core.crawler_interface import CrawledChapter, CrawledNovel, CrawlerInterface


class FakeCrawler(CrawlerInterface):
    """Test double implementing crawler interface for flow assertions."""

    def __init__(self):
        self.fetch_novel_calls: List[Tuple[str, Optional[int]]] = []
        self.fetch_selected_calls: List[List[Tuple[str, str]]] = []

    @staticmethod
    def is_url(input_str: str) -> bool:
        return input_str.startswith("http")

    async def fetch_novel(self, url: str, progress_callback=None, max_chapters: Optional[int] = None) -> CrawledNovel:
        self.fetch_novel_calls.append((url, max_chapters))
        chapter_total = max_chapters or 3
        chapters = [
            CrawledChapter(title=f"Chapter {i}", content=f"Content {i}", chapter_number=i)
            for i in range(1, chapter_total + 1)
        ]
        return CrawledNovel(title="Wrapper Path", author="Tester", chapters=chapters)

    async def discover_chapters(
        self,
        url: str,
        progress_callback=None
    ) -> Tuple[str, Optional[str], List[Tuple[str, str]]]:
        return (
            "Demo Novel",
            "Tester",
            [("https://example.com/ch-1", "Chapter 1"), ("https://example.com/ch-2", "Chapter 2")]
        )

    async def fetch_selected_chapters(
        self,
        url: str,
        title: str,
        author: Optional[str],
        selected_chapters: List[Tuple[str, str]],
        progress_callback=None
    ) -> CrawledNovel:
        self.fetch_selected_calls.append(selected_chapters)
        chapters = [
            CrawledChapter(
                title=chapter_title,
                content=f"Selected from {chapter_url}",
                chapter_number=idx
            )
            for idx, (chapter_url, chapter_title) in enumerate(selected_chapters, 1)
        ]
        return CrawledNovel(title=title, author=author, chapters=chapters)

    def supports_url(self, url: str) -> bool:
        return True

    def get_supported_sites(self) -> List[str]:
        return ["example.com"]


@pytest.mark.asyncio
async def test_download_strategy_uses_wrapper_fetch_for_all_chapters():
    service = CrawlService()
    crawler = FakeCrawler()
    discovered = [(f"https://example.com/ch-{i}", f"Chapter {i}") for i in range(1, 6)]

    novel = await service.download_selected_chapters(
        crawler=crawler,
        url="https://example.com/novel",
        title="Demo Novel",
        author="Tester",
        discovered_chapters=discovered,
        selected_chapters=discovered,
    )

    assert len(novel.chapters) == 3  # Fake crawler default when max_chapters is None
    assert crawler.fetch_novel_calls == [("https://example.com/novel", None)]
    assert crawler.fetch_selected_calls == []


@pytest.mark.asyncio
async def test_download_strategy_uses_wrapper_fetch_for_first_n():
    service = CrawlService()
    crawler = FakeCrawler()
    discovered = [(f"https://example.com/ch-{i}", f"Chapter {i}") for i in range(1, 6)]
    selected = discovered[:2]

    novel = await service.download_selected_chapters(
        crawler=crawler,
        url="https://example.com/novel",
        title="Demo Novel",
        author="Tester",
        discovered_chapters=discovered,
        selected_chapters=selected,
    )

    assert len(novel.chapters) == 2
    assert crawler.fetch_novel_calls == [("https://example.com/novel", 2)]
    assert crawler.fetch_selected_calls == []


@pytest.mark.asyncio
async def test_download_strategy_uses_selected_download_for_custom_range():
    service = CrawlService()
    crawler = FakeCrawler()
    discovered = [(f"https://example.com/ch-{i}", f"Chapter {i}") for i in range(1, 7)]
    selected = discovered[2:4]

    novel = await service.download_selected_chapters(
        crawler=crawler,
        url="https://example.com/novel",
        title="Demo Novel",
        author="Tester",
        discovered_chapters=discovered,
        selected_chapters=selected,
    )

    assert len(novel.chapters) == 2
    assert crawler.fetch_novel_calls == []
    assert crawler.fetch_selected_calls == [selected]


def test_build_full_text_renders_chapter_headers():
    service = CrawlService()
    novel = CrawledNovel(
        title="Demo",
        chapters=[
            CrawledChapter(title="Chapter 1", content="Alpha"),
            CrawledChapter(title="Chapter 2", content="Beta"),
        ],
    )

    full_text = service.build_full_text(novel)

    assert "=== Chapter 1 ===" in full_text
    assert "Alpha" in full_text
    assert "=== Chapter 2 ===" in full_text
    assert "Beta" in full_text
