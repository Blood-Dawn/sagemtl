"""LightNovel-Crawler adapter for SageMTL.

This module provides integration with the lightnovel-crawler package (GPLv3).
The lightnovel-crawler must be installed separately:

    pip install lightnovel-crawler

License: GNU General Public License v3.0 (inherited from lightnovel-crawler)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Check if lightnovel-crawler is available
try:
    import lncrawl
    from lncrawl.core.app import App as LNCrawlApp
    LNCRAWL_AVAILABLE = True
except ImportError:
    LNCRAWL_AVAILABLE = False
    LNCrawlApp = None


@dataclass
class NovelDataset:
    """Novel dataset metadata."""
    id: str
    name: str
    url: str
    path: Path
    chapter_count: int
    author: Optional[str] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    language: str = "en"
    created_at: str = ""
    total_words: int = 0


def is_lncrawl_available() -> bool:
    """Check if lightnovel-crawler is installed."""
    return LNCRAWL_AVAILABLE


def fetch_novel(
    url: str,
    *,
    output_dir: Path,
    dataset_name: Optional[str] = None,
    start_chapter: int = 1,
    end_chapter: Optional[int] = None,
    format: str = "txt",
) -> NovelDataset:
    """
    Fetch a novel using lightnovel-crawler.

    This function requires lightnovel-crawler to be installed separately:
        pip install lightnovel-crawler

    Args:
        url: URL of the novel
        output_dir: Base directory for datasets
        dataset_name: Optional dataset name (auto-generated if not provided)
        start_chapter: First chapter to download (default: 1)
        end_chapter: Last chapter to download (None = all)
        format: Output format (txt, epub, json)

    Returns:
        NovelDataset with metadata

    Raises:
        ImportError: If lightnovel-crawler is not installed
        ValueError: If the URL is not supported
        RuntimeError: If crawling fails
    """
    if not LNCRAWL_AVAILABLE:
        raise ImportError(
            "lightnovel-crawler is not installed. "
            "Install it with: pip install lightnovel-crawler"
        )

    # Create output directory
    if dataset_name:
        novel_dir = output_dir / dataset_name
    else:
        # Generate name from URL
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        novel_dir = output_dir / f"novel-{url_hash}"

    novel_dir.mkdir(parents=True, exist_ok=True)
    files_dir = novel_dir / "files"
    files_dir.mkdir(exist_ok=True)

    # Configure LNCrawl
    app = LNCrawlApp()
    app.user_input = url
    app.output_path = str(files_dir)
    app.output_formats = {format: True}

    # Set chapter range
    if start_chapter > 1:
        app.start_chapter = start_chapter
    if end_chapter:
        app.end_chapter = end_chapter

    try:
        # Initialize crawler
        app.initialize()

        # Check if URL is supported
        if not app.crawler:
            raise ValueError(f"URL not supported by lightnovel-crawler: {url}")

        # Fetch novel info
        app.crawler.read_novel_info()

        # Get metadata
        novel_title = app.crawler.novel_title or "Unknown Novel"
        novel_author = getattr(app.crawler, 'novel_author', None)
        novel_cover = getattr(app.crawler, 'novel_cover', None)
        novel_synopsis = getattr(app.crawler, 'novel_synopsis', None)

        # Fetch chapters
        app.crawler.download_chapters()
        app.crawler.pack_volumes()

        # Count chapters
        chapter_count = len(app.crawler.chapters) if hasattr(app.crawler, 'chapters') else 0

        # Calculate total words (estimate from file sizes)
        total_words = 0
        chapter_files = list(files_dir.glob(f"*.{format}"))
        for chapter_file in chapter_files:
            if format == "txt":
                content = chapter_file.read_text(encoding="utf-8", errors="ignore")
                total_words += len(content.split())

        # Create metadata
        meta = {
            "type": "novel",
            "title": novel_title,
            "author": novel_author,
            "description": novel_synopsis,
            "cover_url": novel_cover,
            "source_url": url,
            "chapter_count": chapter_count,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "total_words": total_words,
            "language": "en",  # Most light novels are translated to English
            "format": format,
            "crawled_with": "lightnovel-crawler",
        }

        # Save metadata
        meta_file = novel_dir / "meta.json"
        meta_file.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return NovelDataset(
            id=novel_dir.name,
            name=novel_title,
            url=url,
            path=novel_dir,
            chapter_count=chapter_count,
            author=novel_author,
            cover_url=novel_cover,
            description=novel_synopsis,
            language="en",
            created_at=meta["created_at"],
            total_words=total_words,
        )

    except Exception as exc:
        raise RuntimeError(f"Failed to crawl novel: {exc}") from exc


def get_supported_sources() -> list[str]:
    """
    Get list of supported novel sources.

    Returns:
        List of source names (empty if lncrawl not available)
    """
    if not LNCRAWL_AVAILABLE:
        return []

    try:
        from lncrawl.sources import crawler_list
        return [crawler.name for crawler in crawler_list]
    except (ImportError, AttributeError):
        return []


def check_url_support(url: str) -> tuple[bool, Optional[str]]:
    """
    Check if a URL is supported by lightnovel-crawler.

    Args:
        url: URL to check

    Returns:
        Tuple of (is_supported, source_name)
    """
    if not LNCRAWL_AVAILABLE:
        return False, None

    try:
        from lncrawl.core.sources import get_crawler_by_url

        crawler = get_crawler_by_url(url)
        if crawler:
            return True, getattr(crawler, 'name', 'Unknown')
        return False, None
    except Exception:
        return False, None
