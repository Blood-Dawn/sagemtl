"""Unit tests for LightNovelCrawlerWrapper helper paths."""

from __future__ import annotations

from typing import Optional

import pytest

from sagemtl_desktop.core.crawler_interface import CrawledChapter, CrawledNovel
from sagemtl_desktop.core.lightnovel_crawler_wrapper import LightNovelCrawlerWrapper


@pytest.mark.asyncio
async def test_discover_chapters_delegates_to_generic(monkeypatch):
    class FakeGenericCrawler:
        def __init__(self, base_url: str, crawl_settings=None):
            self.base_url = base_url
            self.closed = False

        def discover_chapters(self, progress_callback=None):
            if progress_callback:
                progress_callback(100, 100, "done")
            return (
                "Delegated Novel",
                "Delegated Author",
                [("https://example.com/ch-1", "Chapter 1")]
            )

        def close(self):
            self.closed = True

    monkeypatch.setattr(
        "sagemtl_desktop.core.lightnovel_crawler_wrapper.LIGHTNOVEL_CRAWLER_AVAILABLE",
        True
    )
    monkeypatch.setattr(
        "sagemtl_desktop.core.lightnovel_crawler_wrapper.GenericNovelCrawler",
        FakeGenericCrawler
    )

    wrapper = LightNovelCrawlerWrapper()
    title, author, chapters = await wrapper.discover_chapters("https://example.com/novel")

    assert title == "Delegated Novel"
    assert author == "Delegated Author"
    assert chapters == [("https://example.com/ch-1", "Chapter 1")]


@pytest.mark.asyncio
async def test_fetch_selected_chapters_uses_configured_worker_bound(monkeypatch):
    observed: dict[str, Optional[int]] = {"max_workers": None}

    class FakeGenericCrawler:
        def __init__(self, base_url: str, crawl_settings=None):
            self.base_url = base_url

        def fetch_chapters(
            self,
            chapter_links,
            title: str,
            author: Optional[str],
            progress_callback=None,
            max_workers: int = 4
        ):
            observed["max_workers"] = max_workers
            chapters = [
                CrawledChapter(title=chapter_title, content=chapter_url, chapter_number=idx)
                for idx, (chapter_url, chapter_title) in enumerate(chapter_links, 1)
            ]
            return CrawledNovel(title=title, author=author, chapters=chapters)

        def close(self):
            return None

    monkeypatch.setattr(
        "sagemtl_desktop.core.lightnovel_crawler_wrapper.LIGHTNOVEL_CRAWLER_AVAILABLE",
        True
    )
    monkeypatch.setattr(
        "sagemtl_desktop.core.lightnovel_crawler_wrapper.GenericNovelCrawler",
        FakeGenericCrawler
    )

    wrapper = LightNovelCrawlerWrapper(chapter_download_workers=3)
    novel = await wrapper.fetch_selected_chapters(
        url="https://example.com/novel",
        title="Demo",
        author="Tester",
        selected_chapters=[
            ("https://example.com/ch-1", "Chapter 1"),
            ("https://example.com/ch-2", "Chapter 2"),
        ],
    )

    assert observed["max_workers"] == 3
    assert len(novel.chapters) == 2
    assert novel.chapters[0].title == "Chapter 1"
