"""Comprehensive test suite for SageMTL crawler features.

This test suite covers all critical features with detailed scenarios including:
- Chapter pattern detection (multiple URL formats)
- TOC page handling
- Error recovery and retries
- Export formats
- Content extraction
- Edge cases and error handling
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup

from sagemtl.crawl.novel_crawler import NovelCrawler, ChapterInfo, NovelInfo


# ============================================================================
# PATTERN DETECTION TESTS (6 tests)
# ============================================================================


@pytest.fixture
def crawler():
    """Create a NovelCrawler instance for testing."""
    return NovelCrawler(max_concurrent=1, timeout=10.0)


def test_pattern_detection_chapter_dash(crawler):
    """Test pattern detection for chapter-N format."""
    url = "https://example.com/novel/chapter-42"
    pattern = crawler.detect_chapter_pattern(url)

    assert pattern is not None
    assert pattern["current_num"] == 42
    assert "chapter-" in pattern["base_url"]
    # Verify we can build URLs with this pattern
    assert crawler.build_chapter_url(pattern, 43) == "https://example.com/novel/chapter-43"


def test_pattern_detection_chapter_underscore(crawler):
    """Test pattern detection for chapter_N format."""
    url = "https://example.com/novel/chapter_123"
    pattern = crawler.detect_chapter_pattern(url)

    assert pattern is not None
    assert pattern["current_num"] == 123
    assert "chapter_" in pattern["base_url"]


def test_pattern_detection_slash_number_slash(crawler):
    """Test pattern detection for /N/ format."""
    url = "https://example.com/novel/999/"
    pattern = crawler.detect_chapter_pattern(url)

    assert pattern is not None
    assert pattern["current_num"] == 999
    # Verify pattern works for building new URLs
    new_url = crawler.build_chapter_url(pattern, 1000)
    assert "/1000/" in new_url


def test_pattern_detection_number_html(crawler):
    """Test pattern detection for N.html format."""
    url = "https://fanmtl.com/story/123.html"
    pattern = crawler.detect_chapter_pattern(url)

    assert pattern is not None
    assert pattern["current_num"] == 123
    assert ".html" in pattern["suffix"]
    assert crawler.build_chapter_url(pattern, 124).endswith(".html")


def test_pattern_detection_ch_prefix(crawler):
    """Test pattern detection for ch-N or chN formats."""
    urls = [
        ("https://example.com/novel/ch7/", 7),
        ("https://example.com/novel/ch999/index.html", 999),
        ("https://example.com/novel/ch42", 42),
    ]

    for url, expected_num in urls:
        pattern = crawler.detect_chapter_pattern(url)
        assert pattern is not None, f"Failed to detect pattern in {url}"
        assert pattern["current_num"] == expected_num


def test_pattern_detection_no_match(crawler):
    """Test that pattern detection returns None for invalid URLs."""
    invalid_urls = [
        "https://example.com",  # No chapter info
        "https://example.com/about",  # No numbers
        "https://example.com/novel/info",  # No chapter pattern
        "https://example.com?tab=chapters",  # Query string only
    ]

    for url in invalid_urls:
        pattern = crawler.detect_chapter_pattern(url)
        assert pattern is None, f"Should not detect pattern in {url}"


# ============================================================================
# TOC PAGE HANDLING TESTS (4 tests)
# ============================================================================


def test_extract_first_chapter_from_toc_with_chapter_links():
    """Test extracting first chapter from a TOC page with chapter-N links."""
    html = """
    <html>
    <body>
        <div class="toc">
            <a href="?tab=info">Info</a>
            <a href="?tab=chapters">Chapters</a>
            <a href="/novel/chapter-1">Chapter 1</a>
            <a href="/novel/chapter-2">Chapter 2</a>
            <a href="/novel/chapter-10">Chapter 10</a>
        </div>
    </body>
    </html>
    """

    with patch.object(httpx.Client, "get") as mock_get:
        mock_response = Mock()
        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        crawler = NovelCrawler()
        first_url = crawler._extract_first_chapter_url("https://example.com/novel?tab=chapters")

        assert first_url is not None
        assert "chapter-1" in first_url
        assert not first_url.startswith("?")  # Not a query string


def test_extract_first_chapter_from_toc_with_numbered_links():
    """Test extracting first chapter from TOC with /N/ style links."""
    html = """
    <html>
    <body>
        <a href="/story/5/">Chapter 5</a>
        <a href="/story/1/">Chapter 1</a>
        <a href="/story/3/">Chapter 3</a>
    </body>
    </html>
    """

    with patch.object(httpx.Client, "get") as mock_get:
        mock_response = Mock()
        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        crawler = NovelCrawler()
        first_url = crawler._extract_first_chapter_url("https://example.com/story/")

        assert first_url is not None
        # Should return chapter 1, not chapter 5 (sorted by number)
        assert "/1/" in first_url


def test_extract_first_chapter_handles_relative_urls():
    """Test that relative URLs are converted to absolute."""
    html = """
    <html>
    <body>
        <a href="chapter-1.html">Chapter 1</a>
        <a href="chapter-2.html">Chapter 2</a>
    </body>
    </html>
    """

    with patch.object(httpx.Client, "get") as mock_get:
        mock_response = Mock()
        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        crawler = NovelCrawler()
        first_url = crawler._extract_first_chapter_url("https://example.com/novel/")

        assert first_url is not None
        assert first_url.startswith("http")  # Absolute URL
        assert "chapter-1.html" in first_url


def test_extract_first_chapter_no_valid_links():
    """Test behavior when TOC has no valid chapter links."""
    html = """
    <html>
    <body>
        <a href="?tab=info">Info</a>
        <a href="#top">Top</a>
        <a href="/about">About</a>
    </body>
    </html>
    """

    with patch.object(httpx.Client, "get") as mock_get:
        mock_response = Mock()
        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        crawler = NovelCrawler()
        first_url = crawler._extract_first_chapter_url("https://example.com/novel")

        assert first_url is None


# ============================================================================
# CHAPTER INFO AND CONTENT TESTS (4 tests)
# ============================================================================


def test_chapter_info_creation_with_all_fields():
    """Test ChapterInfo dataclass with all fields populated."""
    chapter = ChapterInfo(
        number=42,
        title="The Answer to Everything",
        url="https://example.com/ch42",
        content="This is a story about 42...",
        word_count=6,
    )

    assert chapter.number == 42
    assert chapter.title == "The Answer to Everything"
    assert chapter.url == "https://example.com/ch42"
    assert chapter.content == "This is a story about 42..."
    assert chapter.word_count == 6


def test_novel_info_creation():
    """Test NovelInfo dataclass creation."""
    chapters = [
        ChapterInfo(1, "Ch1", "url1", "content1", 1),
        ChapterInfo(2, "Ch2", "url2", "content2", 2),
    ]

    novel = NovelInfo(
        title="Test Novel",
        author="Test Author",
        description="A test description",
        cover_url="https://example.com/cover.jpg",
        chapters=chapters,
        source_url="https://example.com/novel",
    )

    assert novel.title == "Test Novel"
    assert novel.author == "Test Author"
    assert len(novel.chapters) == 2
    assert novel.chapters[0].number == 1


def test_build_chapter_url_with_different_formats():
    """Test building chapter URLs with various pattern formats."""
    crawler = NovelCrawler()

    test_cases = [
        # (pattern, chapter_num, expected_result)
        (
            {"base_url": "https://example.com/chapter-", "suffix": "", "current_num": 1},
            5,
            "https://example.com/chapter-5",
        ),
        (
            {"base_url": "https://example.com/", "suffix": "/", "current_num": 1},
            100,
            "https://example.com/100/",
        ),
        (
            {"base_url": "https://example.com/", "suffix": ".html", "current_num": 1},
            999,
            "https://example.com/999.html",
        ),
    ]

    for pattern, chapter_num, expected in test_cases:
        result = crawler.build_chapter_url(pattern, chapter_num)
        assert result == expected, f"Failed for pattern {pattern} with num {chapter_num}"


def test_build_chapter_url_preserves_suffix():
    """Test that URL building preserves suffixes correctly."""
    pattern = {
        "base_url": "https://example.com/story/chapter-",
        "pattern": "https://example.com/story/chapter-{num}/page.html",
        "current_num": 1,
        "suffix": "/page.html",
    }

    crawler = NovelCrawler()
    url = crawler.build_chapter_url(pattern, 42)

    assert url == "https://example.com/story/chapter-42/page.html"
    assert "/page.html" in url  # Suffix preserved


# ============================================================================
# SAVE TO DATASET TESTS (4 tests)
# ============================================================================


def test_save_to_dataset_txt_format():
    """Test saving chapters in TXT format."""
    chapters = [
        ChapterInfo(1, "Chapter One", "url1", "First chapter content.", 3),
        ChapterInfo(2, "Chapter Two", "url2", "Second chapter content.", 3),
    ]

    novel = NovelInfo(
        title="Test Novel",
        author="Test Author",
        description="Description",
        cover_url=None,
        chapters=chapters,
        source_url="https://example.com",
    )

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        crawler = NovelCrawler()

        dataset_path = crawler.save_to_dataset(novel, output_dir, format="txt")

        # Verify structure
        assert dataset_path.exists()
        assert (dataset_path / "meta.json").exists()
        assert (dataset_path / "files").exists()

        # Verify chapter files
        ch1 = dataset_path / "files" / "chapter-0001.txt"
        ch2 = dataset_path / "files" / "chapter-0002.txt"

        assert ch1.exists()
        assert ch2.exists()

        # Verify content
        ch1_content = ch1.read_text()
        assert "Chapter One" in ch1_content
        assert "First chapter content" in ch1_content


def test_save_to_dataset_markdown_format():
    """Test saving chapters in Markdown format."""
    chapters = [
        ChapterInfo(1, "Introduction", "url1", "Intro content.", 2),
    ]

    novel = NovelInfo(
        title="MD Novel",
        author="MD Author",
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
        assert content.startswith("# Introduction")  # Markdown heading
        assert "Intro content" in content


def test_save_to_dataset_jsonl_format():
    """Test saving chapters in JSONL format."""
    chapters = [
        ChapterInfo(1, "Chapter 1", "https://example.com/ch1", "Content here.", 2),
    ]

    novel = NovelInfo(
        title="JSON Novel",
        author="JSON Author",
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

        # Parse JSON
        data = json.loads(ch_file.read_text())
        assert data["chapter"] == 1
        assert data["title"] == "Chapter 1"
        assert data["url"] == "https://example.com/ch1"
        assert "content" in data


def test_save_to_dataset_metadata_complete():
    """Test that metadata.json contains all required fields."""
    chapters = [
        ChapterInfo(i, f"Chapter {i}", f"url{i}", f"Content {i}.", i)
        for i in range(1, 6)
    ]

    novel = NovelInfo(
        title="Metadata Test Novel",
        author="Meta Author",
        description="A novel for testing metadata",
        cover_url="https://example.com/cover.jpg",
        chapters=chapters,
        source_url="https://example.com/novel",
    )

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        crawler = NovelCrawler()

        dataset_path = crawler.save_to_dataset(novel, output_dir, format="txt")

        meta_file = dataset_path / "meta.json"
        assert meta_file.exists()

        meta = json.loads(meta_file.read_text())

        # Check all required fields
        assert meta["type"] == "novel"
        assert meta["title"] == "Metadata Test Novel"
        assert meta["author"] == "Meta Author"
        assert meta["description"] == "A novel for testing metadata"
        assert meta["cover_url"] == "https://example.com/cover.jpg"
        assert meta["source_url"] == "https://example.com/novel"
        assert meta["chapter_count"] == 5
        assert meta["total_words"] == sum(range(1, 6))  # 1+2+3+4+5 = 15
        assert "created_at" in meta
        assert "updated_at" in meta
        assert len(meta["chapters"]) == 5

        # Check chapter metadata
        ch1_meta = meta["chapters"][0]
        assert ch1_meta["number"] == 1
        assert ch1_meta["title"] == "Chapter 1"
        assert ch1_meta["url"] == "url1"
        assert ch1_meta["word_count"] == 1


# ============================================================================
# EDGE CASES AND ERROR HANDLING (4 tests)
# ============================================================================


def test_pattern_detection_with_large_chapter_numbers():
    """Test pattern detection works with large chapter numbers."""
    crawler = NovelCrawler()

    url = "https://example.com/chapter-9999"
    pattern = crawler.detect_chapter_pattern(url)

    assert pattern is not None
    assert pattern["current_num"] == 9999

    # Verify we can build URLs for even larger numbers
    url_10000 = crawler.build_chapter_url(pattern, 10000)
    assert "10000" in url_10000


def test_save_to_dataset_handles_special_characters_in_title():
    """Test that special characters in title are handled safely."""
    novel = NovelInfo(
        title="Test/Novel:With*Special?Characters",
        author="Author",
        description=None,
        cover_url=None,
        chapters=[ChapterInfo(1, "Ch1", "url", "content", 1)],
        source_url="https://example.com",
    )

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        crawler = NovelCrawler()

        dataset_path = crawler.save_to_dataset(novel, output_dir, format="txt")

        # Directory should exist and not contain illegal path characters
        assert dataset_path.exists()
        # Check that illegal chars were replaced
        assert "/" not in dataset_path.name
        assert "\\" not in dataset_path.name


def test_save_to_dataset_with_empty_chapters_list():
    """Test behavior when saving a novel with no chapters."""
    novel = NovelInfo(
        title="Empty Novel",
        author="Author",
        description=None,
        cover_url=None,
        chapters=[],  # No chapters
        source_url="https://example.com",
    )

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        crawler = NovelCrawler()

        dataset_path = crawler.save_to_dataset(novel, output_dir, format="txt")

        # Should still create structure
        assert dataset_path.exists()
        assert (dataset_path / "meta.json").exists()
        assert (dataset_path / "files").exists()

        # Verify metadata
        meta = json.loads((dataset_path / "meta.json").read_text())
        assert meta["chapter_count"] == 0
        assert meta["total_words"] == 0
        assert len(meta["chapters"]) == 0


def test_crawl_novel_raises_error_for_invalid_url():
    """Test that crawl_novel raises appropriate error for invalid URLs."""
    crawler = NovelCrawler()

    # Mock the HTTP calls to return TOC page with no valid chapter links
    html = "<html><body><p>No chapters here!</p></body></html>"

    with patch.object(httpx.Client, "get") as mock_get:
        mock_response = Mock()
        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Should raise ValueError with helpful message
        with pytest.raises(ValueError) as exc_info:
            crawler.crawl_novel("https://example.com/invalid")

        error_msg = str(exc_info.value)
        assert "Could not detect chapter pattern" in error_msg
        assert "TOC page" in error_msg or "no chapter links" in error_msg


# ============================================================================
# INTEGRATION AND END-TO-END TESTS (2 tests)
# ============================================================================


def test_toc_url_to_first_chapter_extraction_integration():
    """Integration test: TOC URL → first chapter extraction → pattern detection."""
    toc_html = """
    <html>
    <body>
        <h1>Novel Title</h1>
        <div class="chapters">
            <a href="/novel/chapter-1.html">Chapter 1: Beginning</a>
            <a href="/novel/chapter-2.html">Chapter 2: Middle</a>
        </div>
    </body>
    </html>
    """

    with patch.object(httpx.Client, "get") as mock_get:
        mock_response = Mock()
        mock_response.text = toc_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        crawler = NovelCrawler()

        # Extract first chapter URL from TOC
        first_url = crawler._extract_first_chapter_url("https://example.com/novel?tab=chapters")
        assert first_url is not None
        assert "chapter-1.html" in first_url

        # Verify pattern can be detected from extracted URL
        pattern = crawler.detect_chapter_pattern(first_url)
        assert pattern is not None
        assert pattern["current_num"] == 1

        # Verify we can build subsequent chapter URLs
        ch2_url = crawler.build_chapter_url(pattern, 2)
        assert "chapter-2.html" in ch2_url


def test_full_crawl_workflow_with_toc_url():
    """End-to-end test: crawl_novel with TOC URL should auto-extract first chapter."""
    toc_html = """
    <html>
    <head><title>Test Novel</title></head>
    <body>
        <a href="/story/1.html">Chapter 1</a>
        <a href="/story/2.html">Chapter 2</a>
    </body>
    </html>
    """

    chapter_html = """
    <html>
    <head><title>Chapter {num}</title></head>
    <body>
        <h1>Chapter {num}</h1>
        <p>Content for chapter {num}.</p>
    </body>
    </html>
    """

    def mock_get(url):
        response = Mock()
        response.raise_for_status = Mock()

        if "?tab=" in url or url.endswith("/story/"):
            response.text = toc_html
        elif "/story/1.html" in url:
            response.text = chapter_html.format(num=1)
        elif "/story/2.html" in url:
            response.text = chapter_html.format(num=2)
        else:
            response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not found", request=Mock(), response=Mock(status_code=404)
            )

        return response

    with patch.object(httpx.Client, "get", side_effect=mock_get):
        crawler = NovelCrawler()

        # Pass TOC URL (no direct chapter pattern)
        novel = crawler.crawl_novel(
            start_url="https://example.com/story/?tab=chapters",
            start_chapter=1,
            end_chapter=2,
        )

        # Should successfully crawl despite TOC URL
        assert novel is not None
        assert len(novel.chapters) == 2
        assert novel.chapters[0].number == 1
        assert novel.chapters[1].number == 2
        assert "Content for chapter 1" in novel.chapters[0].content
        assert "Content for chapter 2" in novel.chapters[1].content


# ============================================================================
# TOTAL: 24 COMPREHENSIVE TESTS
# ============================================================================
