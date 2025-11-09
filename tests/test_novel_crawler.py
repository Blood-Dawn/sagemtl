"""Tests for novel crawler with pattern detection."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from sagemtl.crawl.novel_crawler import NovelCrawler, ChapterInfo


@pytest.fixture
def crawler():
    """Create a NovelCrawler instance."""
    return NovelCrawler(max_concurrent=1, timeout=10.0)


def test_detect_chapter_pattern_dash(crawler):
    """Test pattern detection for chapter-N URLs."""
    url = "https://example.com/novel/chapter-1"
    pattern = crawler.detect_chapter_pattern(url)

    assert pattern is not None
    assert pattern["current_num"] == 1
    assert "chapter-" in pattern["base_url"]


def test_detect_chapter_pattern_slash_number(crawler):
    """Test pattern detection for /N/ URLs."""
    url = "https://example.com/novel/123/"
    pattern = crawler.detect_chapter_pattern(url)

    assert pattern is not None
    assert pattern["current_num"] == 123


def test_detect_chapter_pattern_html(crawler):
    """Test pattern detection for N.html URLs."""
    url = "https://example.com/novel/45.html"
    pattern = crawler.detect_chapter_pattern(url)

    assert pattern is not None
    assert pattern["current_num"] == 45
    assert ".html" in pattern["pattern"]


def test_detect_chapter_pattern_ch_prefix(crawler):
    """Test pattern detection for ch-N URLs."""
    url = "https://example.com/novel/ch7/index.html"
    pattern = crawler.detect_chapter_pattern(url)

    assert pattern is not None
    assert pattern["current_num"] == 7


def test_build_chapter_url(crawler):
    """Test building chapter URLs from patterns."""
    pattern = {
        "base_url": "https://example.com/chapter-",
        "pattern": "https://example.com/chapter-{num}",
        "current_num": 1,
        "suffix": "",
    }

    url = crawler.build_chapter_url(pattern, 5)
    assert url == "https://example.com/chapter-5"


def test_chapter_info_creation():
    """Test ChapterInfo dataclass creation."""
    chapter = ChapterInfo(
        number=1,
        title="Prologue",
        url="https://example.com/ch1",
        content="This is the beginning...",
        word_count=4,
    )

    assert chapter.number == 1
    assert chapter.title == "Prologue"
    assert chapter.word_count == 4


def test_save_to_dataset():
    """Test saving novel chapters to dataset."""
    from sagemtl.crawl.novel_crawler import NovelInfo

    chapters = [
        ChapterInfo(
            number=1,
            title="Chapter 1",
            url="https://example.com/ch1",
            content="First chapter content.",
            word_count=3,
        ),
        ChapterInfo(
            number=2,
            title="Chapter 2",
            url="https://example.com/ch2",
            content="Second chapter content.",
            word_count=3,
        ),
    ]

    novel = NovelInfo(
        title="Test Novel",
        author="Test Author",
        description="A test novel",
        cover_url="https://example.com/cover.jpg",
        chapters=chapters,
        source_url="https://example.com/ch1",
    )

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        crawler = NovelCrawler()

        dataset_path = crawler.save_to_dataset(novel, output_dir, format="txt")

        # Verify dataset structure
        assert dataset_path.exists()
        assert (dataset_path / "meta.json").exists()
        assert (dataset_path / "files").exists()

        # Verify metadata
        import json

        meta = json.loads((dataset_path / "meta.json").read_text())
        assert meta["type"] == "novel"
        assert meta["title"] == "Test Novel"
        assert meta["author"] == "Test Author"
        assert meta["chapter_count"] == 2
        assert meta["total_words"] == 6

        # Verify chapter files
        ch1_file = dataset_path / "files" / "chapter-0001.txt"
        ch2_file = dataset_path / "files" / "chapter-0002.txt"

        assert ch1_file.exists()
        assert ch2_file.exists()

        # Verify content
        ch1_content = ch1_file.read_text()
        assert "Chapter 1" in ch1_content
        assert "First chapter content" in ch1_content


def test_save_to_dataset_markdown():
    """Test saving chapters in markdown format."""
    from sagemtl.crawl.novel_crawler import NovelInfo

    chapters = [
        ChapterInfo(
            number=1,
            title="Chapter 1",
            url="https://example.com/ch1",
            content="Content here.",
            word_count=2,
        ),
    ]

    novel = NovelInfo(
        title="Test Novel",
        author=None,
        description=None,
        cover_url=None,
        chapters=chapters,
        source_url="https://example.com",
    )

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        crawler = NovelCrawler()

        dataset_path = crawler.save_to_dataset(novel, output_dir, format="md")

        ch_file = dataset_path / "files" / "chapter-0001.md"
        assert ch_file.exists()

        content = ch_file.read_text()
        assert "# Chapter 1" in content  # Markdown heading


def test_save_to_dataset_jsonl():
    """Test saving chapters in JSONL format."""
    from sagemtl.crawl.novel_crawler import NovelInfo
    import json

    chapters = [
        ChapterInfo(
            number=1,
            title="Chapter 1",
            url="https://example.com/ch1",
            content="Content here.",
            word_count=2,
        ),
    ]

    novel = NovelInfo(
        title="Test Novel",
        author=None,
        description=None,
        cover_url=None,
        chapters=chapters,
        source_url="https://example.com",
    )

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        crawler = NovelCrawler()

        dataset_path = crawler.save_to_dataset(novel, output_dir, format="jsonl")

        ch_file = dataset_path / "files" / "chapter-0001.jsonl"
        assert ch_file.exists()

        content = json.loads(ch_file.read_text())
        assert content["chapter"] == 1
        assert content["title"] == "Chapter 1"
        assert "url" in content


def test_no_pattern_detection():
    """Test behavior when pattern can't be detected."""
    crawler = NovelCrawler()
    url = "https://example.com/some/random/path/without/numbers"
    pattern = crawler.detect_chapter_pattern(url)

    assert pattern is None


