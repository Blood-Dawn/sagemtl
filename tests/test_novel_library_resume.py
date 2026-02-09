"""Tests for resume-aware novel library upsert behavior."""

from __future__ import annotations

from sagemtl_desktop.core.crawler_interface import CrawledChapter, CrawledNovel
from sagemtl_desktop.core.novel_library import NovelLibrary


def test_upsert_novel_from_crawled_merges_existing_by_url(tmp_path):
    library = NovelLibrary(storage_path=str(tmp_path))

    first = CrawledNovel(
        title="Demo Novel",
        author="Author A",
        chapters=[
            CrawledChapter(
                title="Chapter 1",
                content="old content 1",
                chapter_number=1,
                url="https://example.com/ch-1",
            ),
            CrawledChapter(
                title="Chapter 2",
                content="old content 2",
                chapter_number=2,
                url="https://example.com/ch-2",
            ),
        ],
    )
    saved_first = library.upsert_novel_from_crawled(
        first,
        source_url="https://example.com/novel",
        resume_existing=True,
    )

    second = CrawledNovel(
        title="Demo Novel",
        author="Author A",
        chapters=[
            CrawledChapter(
                title="Chapter 2",
                content="new content 2",
                chapter_number=2,
                url="https://example.com/ch-2",
            ),
            CrawledChapter(
                title="Chapter 3",
                content="new content 3",
                chapter_number=3,
                url="https://example.com/ch-3",
            ),
        ],
    )
    saved_second = library.upsert_novel_from_crawled(
        second,
        source_url="https://example.com/novel",
        resume_existing=True,
    )

    assert saved_second.novel_id == saved_first.novel_id
    assert len(saved_second.chapters) == 3
    by_url = {chapter.url: chapter for chapter in saved_second.chapters}
    assert by_url["https://example.com/ch-2"].content == "new content 2"
    assert by_url["https://example.com/ch-3"].content == "new content 3"


def test_upsert_preserves_user_locked_title(tmp_path):
    library = NovelLibrary(storage_path=str(tmp_path))

    first = CrawledNovel(
        title="Action",
        author="Author A",
        chapters=[
            CrawledChapter(
                title="Chapter 1",
                content="old content 1",
                chapter_number=1,
                url="https://example.com/ch-1",
            ),
        ],
    )
    saved = library.upsert_novel_from_crawled(
        first,
        source_url="https://example.com/novel",
        resume_existing=True,
    )

    saved.title = "My Real Novel Title"
    saved.title_locked = True
    library.update_novel(saved)

    second = CrawledNovel(
        title="Action",
        author="Author A",
        chapters=[
            CrawledChapter(
                title="Chapter 2",
                content="new content 2",
                chapter_number=2,
                url="https://example.com/ch-2",
            ),
        ],
    )
    updated = library.upsert_novel_from_crawled(
        second,
        source_url="https://example.com/novel",
        resume_existing=True,
    )

    assert updated.title == "My Real Novel Title"
    assert updated.title_locked is True


def test_upsert_updates_title_when_not_locked(tmp_path):
    library = NovelLibrary(storage_path=str(tmp_path))

    first = CrawledNovel(
        title="Old Title",
        author="Author A",
        chapters=[
            CrawledChapter(
                title="Chapter 1",
                content="old content 1",
                chapter_number=1,
                url="https://example.com/ch-1",
            ),
        ],
    )
    library.upsert_novel_from_crawled(
        first,
        source_url="https://example.com/novel",
        resume_existing=True,
    )

    second = CrawledNovel(
        title="Updated Crawler Title",
        author="Author A",
        chapters=[
            CrawledChapter(
                title="Chapter 2",
                content="new content 2",
                chapter_number=2,
                url="https://example.com/ch-2",
            ),
        ],
    )
    updated = library.upsert_novel_from_crawled(
        second,
        source_url="https://example.com/novel",
        resume_existing=True,
    )

    assert updated.title == "Updated Crawler Title"
    assert updated.title_locked is False
