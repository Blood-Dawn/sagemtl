"""Tests for generic crawler chapter download behavior."""

from __future__ import annotations

import threading
import time

from sagemtl_desktop.core.generic_crawler import GenericNovelCrawler


def test_fetch_chapters_preserves_input_order_with_concurrency(monkeypatch):
    crawler = GenericNovelCrawler("https://example.com/novel")
    chapter_links = [
        ("https://example.com/ch-1", "Chapter 1"),
        ("https://example.com/ch-2", "Chapter 2"),
        ("https://example.com/ch-3", "Chapter 3"),
        ("https://example.com/ch-4", "Chapter 4"),
    ]

    active_count = 0
    peak_active = 0
    lock = threading.Lock()

    def fake_fetch(url: str) -> str:
        nonlocal active_count, peak_active
        with lock:
            active_count += 1
            peak_active = max(peak_active, active_count)
        time.sleep(0.05)
        with lock:
            active_count -= 1
        return f"content from {url}"

    monkeypatch.setattr(crawler, "_fetch_chapter_content", fake_fetch)

    novel = crawler.fetch_chapters(
        chapter_links=chapter_links,
        title="Demo",
        author="Tester",
        max_workers=2
    )

    crawler.close()

    assert len(novel.chapters) == len(chapter_links)
    assert peak_active <= 2
    assert peak_active >= 2
    assert [chapter.title for chapter in novel.chapters] == [title for _, title in chapter_links]
    assert [chapter.chapter_number for chapter in novel.chapters] == [1, 2, 3, 4]


def test_fetch_chapters_reports_progress(monkeypatch):
    crawler = GenericNovelCrawler("https://example.com/novel")
    chapter_links = [
        ("https://example.com/ch-1", "Chapter 1"),
        ("https://example.com/ch-2", "Chapter 2"),
    ]

    progress_messages = []

    def fake_fetch(url: str) -> str:
        return f"content from {url}"

    def progress_callback(current, total, message):
        progress_messages.append((current, total, message))

    monkeypatch.setattr(crawler, "_fetch_chapter_content", fake_fetch)

    novel = crawler.fetch_chapters(
        chapter_links=chapter_links,
        title="Demo",
        author="Tester",
        progress_callback=progress_callback,
        max_workers=2
    )

    crawler.close()

    assert len(novel.chapters) == 2
    assert progress_messages[0][0] == 0
    assert progress_messages[-1][0] == 100
    assert any("Downloaded" in msg for _, _, msg in progress_messages)
