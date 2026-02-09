"""Tests for crawl service milestone-A capabilities."""

from __future__ import annotations

from sagemtl_desktop.core.crawl_service import CrawlService
from sagemtl_desktop.core.crawl_settings import CrawlSettings
from sagemtl_desktop.core.crawler_interface import CrawledChapter, CrawledNovel


class _FakeSettingsBackend:
    def __init__(self):
        self.data = {}

    def value(self, key, default=None):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value


def test_normalize_batch_urls_filters_and_deduplicates():
    raw = """
https://example.com/a
invalid line
https://example.com/a
http://example.org/b;https://example.net/c
"""
    urls = CrawlService.normalize_batch_urls(raw)
    assert urls == [
        "https://example.com/a",
        "http://example.org/b",
        "https://example.net/c",
    ]


def test_filter_pending_chapters_for_resume():
    selected = [
        ("https://example.com/ch-1", "Chapter 1"),
        ("https://example.com/ch-2", "Chapter 2"),
        ("https://example.com/ch-3", "Chapter 3"),
    ]
    existing_urls = ["https://example.com/ch-1", "https://example.com/ch-3"]

    pending, skipped = CrawlService.filter_pending_chapters_for_resume(selected, existing_urls)

    assert skipped == 2
    assert pending == [("https://example.com/ch-2", "Chapter 2")]


def test_site_profile_round_trip():
    settings_backend = _FakeSettingsBackend()
    crawl_settings = CrawlSettings(
        request_delay_seconds=0.5,
        max_retries=4,
        ignore_robots_txt=True,
        chapter_download_workers=3,
    )

    CrawlService.save_site_profile(settings_backend, "https://example.com/novel", crawl_settings)
    loaded = CrawlService.get_site_profile(settings_backend, "https://example.com/novel")

    assert loaded.request_delay_seconds == 0.5
    assert loaded.max_retries == 4
    assert loaded.ignore_robots_txt is True
    assert loaded.chapter_download_workers == 3


def test_export_crawled_epub_uses_writer(monkeypatch, tmp_path):
    calls = {}

    class FakeWriter:
        def is_available(self):
            return True

        def create_epub(self, title, chapters, output_path, author):
            calls["title"] = title
            calls["chapters"] = chapters
            calls["output_path"] = output_path
            calls["author"] = author
            return str(tmp_path / "demo.epub")

    monkeypatch.setattr("sagemtl_desktop.core.crawl_service.EPUBWriter", FakeWriter)

    novel = CrawledNovel(
        title="Demo",
        author="Tester",
        chapters=[
            CrawledChapter(title="Chapter 1", content="Alpha"),
            CrawledChapter(title="Chapter 2", content="Beta"),
        ],
    )

    epub_path = CrawlService.export_crawled_epub(novel, str(tmp_path))

    assert epub_path.endswith("demo.epub")
    assert calls["title"] == "Demo"
    assert calls["author"] == "Tester"
    assert len(calls["chapters"]) == 2
