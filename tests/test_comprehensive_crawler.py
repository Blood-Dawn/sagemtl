"""Unit tests for LightNovelCrawlerWrapper helper paths."""

from __future__ import annotations

import time
from types import SimpleNamespace
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


def test_normalize_search_results_handles_combined_search_shape(monkeypatch):
    """
    Regression test: lncrawl now returns CombinedSearchResult entries
    with nested `novels` instead of legacy `result.novel`.
    """
    monkeypatch.setattr(
        "sagemtl_desktop.core.lightnovel_crawler_wrapper.LIGHTNOVEL_CRAWLER_AVAILABLE",
        True
    )
    wrapper = LightNovelCrawlerWrapper()

    query_title = "In the universe online game, I can specify the drop"
    raw_results = [
        SimpleNamespace(
            title=query_title,
            novels=[
                SimpleNamespace(
                    title=query_title,
                    url="https://novel-site-a.example/books/drop-system",
                    info="novel-site-a.example",
                )
            ],
        ),
        # Duplicate URL should be de-duplicated.
        SimpleNamespace(
            title=query_title,
            novels=[
                SimpleNamespace(
                    title=query_title,
                    url="https://novel-site-a.example/books/drop-system/",
                    info="",
                )
            ],
        ),
    ]

    normalized = wrapper._normalize_search_results(raw_results)

    assert len(normalized) == 1
    assert normalized[0]["title"] == query_title
    assert normalized[0]["url"] == "https://novel-site-a.example/books/drop-system"
    assert normalized[0]["site"] == "novel-site-a.example"
    assert normalized[0]["info"] == "novel-site-a.example"


def test_normalize_search_results_handles_legacy_shape(monkeypatch):
    monkeypatch.setattr(
        "sagemtl_desktop.core.lightnovel_crawler_wrapper.LIGHTNOVEL_CRAWLER_AVAILABLE",
        True
    )
    wrapper = LightNovelCrawlerWrapper()

    raw_results = [
        SimpleNamespace(
            novel=SimpleNamespace(
                title="Legacy Result Title",
                url="https://legacy-source.example/novel/123",
            ),
            origin="legacy-source.example",
        )
    ]

    normalized = wrapper._normalize_search_results(raw_results)

    assert normalized == [
        {
            "title": "Legacy Result Title",
            "url": "https://legacy-source.example/novel/123",
            "site": "legacy-source.example",
            "info": "legacy-source.example",
        }
    ]


def test_normalize_search_results_keeps_rows_without_info_site(monkeypatch):
    """
    Regression test for the reported failure:
    "Raw results count: 10" then "Found 0 results".
    """
    monkeypatch.setattr(
        "sagemtl_desktop.core.lightnovel_crawler_wrapper.LIGHTNOVEL_CRAWLER_AVAILABLE",
        True
    )
    wrapper = LightNovelCrawlerWrapper()

    query_title = "In the universe online game, I can specify the drop"
    raw_results = [
        SimpleNamespace(
            title=f"{query_title} {idx}",
            novels=[
                SimpleNamespace(
                    title=f"{query_title} {idx}",
                    url=f"https://site-{idx}.example/novel/drop-{idx}",
                )
            ],
        )
        for idx in range(1, 11)
    ]

    normalized = wrapper._normalize_search_results(raw_results)

    assert len(normalized) == 10
    for idx, item in enumerate(normalized, 1):
        assert item["title"] == f"{query_title} {idx}"
        assert item["url"] == f"https://site-{idx}.example/novel/drop-{idx}"
        assert item["site"] == f"site-{idx}.example"
        assert item["info"] == f"site-{idx}.example"


def test_run_search_with_live_progress_emits_incremental_updates(monkeypatch):
    monkeypatch.setattr(
        "sagemtl_desktop.core.lightnovel_crawler_wrapper.LIGHTNOVEL_CRAWLER_AVAILABLE",
        True
    )
    wrapper = LightNovelCrawlerWrapper()

    class FakeApp:
        def __init__(self):
            self.search_progress = 0

        def search_novel(self):
            for step in (10, 25, 40, 55, 70, 85, 100):
                self.search_progress = step
                time.sleep(0.05)

    app = FakeApp()
    observed_progress: list[int] = []
    observed_messages: list[str] = []

    def progress_callback(current, total, message):
        del total
        observed_progress.append(int(current))
        observed_messages.append(message)

    wrapper._run_search_with_live_progress(app, progress_callback)

    assert len(observed_progress) >= 3
    assert observed_progress == sorted(observed_progress)
    assert observed_progress[0] >= 30
    assert observed_progress[-1] >= 85
    assert any("Searching sites..." in message for message in observed_messages)


def test_run_search_with_live_progress_propagates_search_error(monkeypatch):
    monkeypatch.setattr(
        "sagemtl_desktop.core.lightnovel_crawler_wrapper.LIGHTNOVEL_CRAWLER_AVAILABLE",
        True
    )
    wrapper = LightNovelCrawlerWrapper()

    class FakeApp:
        search_progress = 0

        def search_novel(self):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        wrapper._run_search_with_live_progress(FakeApp(), lambda *_: None)
