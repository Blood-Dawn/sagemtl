"""Novel crawler with chapter detection and optional lightnovel-crawler integration.

This module provides:
1. Built-in chapter detection for common novel site patterns
2. Optional integration with lightnovel-crawler (GPLv3) when available
3. Automatic URL pattern recognition
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .boilerplate import extract_main_content


@dataclass
class ChapterInfo:
    """Information about a single chapter."""

    number: int
    title: str
    url: str
    content: str
    word_count: int


@dataclass
class NovelInfo:
    """Information about a novel."""

    title: str
    author: Optional[str]
    description: Optional[str]
    cover_url: Optional[str]
    chapters: list[ChapterInfo]
    source_url: str


class NovelCrawler:
    """Built-in novel crawler with chapter detection."""

    def __init__(
        self,
        max_concurrent: int = 3,
        timeout: float = 30.0,
        user_agent: str = "SageMTL/1.0",
    ):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.user_agent = user_agent
        self.client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )

    def detect_chapter_pattern(self, url: str) -> Optional[dict[str, str]]:
        """
        Detect chapter URL pattern from a given chapter URL.

        Returns a dict with 'base_url' and 'pattern' keys, or None.

        Examples:
            https://example.com/novel/chapter-1 -> base=.../chapter-, pattern={num}
            https://example.com/novel/1.html -> base=.../, pattern={num}.html
        """
        patterns = [
            # chapter-1, chapter-2, etc.
            (r"(.*chapter[-_])(\d+)(.*)", r"\1{num}\3"),
            # /1/, /2/, etc.
            (r"(.*/)(\d+)(/.*)", r"\1{num}\3"),
            # /1.html, /2.html, etc.
            (r"(.*/)(\d+)(\.html?)", r"\1{num}\3"),
            # /ch1/, /ch2/, etc.
            (r"(.*ch)(\d+)(.*)", r"\1{num}\3"),
        ]

        for regex, template in patterns:
            match = re.match(regex, url, re.IGNORECASE)
            if match:
                # Expand template using match groups (e.g., \1{num}\3 -> base_url{num}suffix)
                expanded_pattern = match.expand(template)
                return {
                    "base_url": match.group(1),
                    "pattern": expanded_pattern,
                    "current_num": int(match.group(2)),
                    "suffix": match.group(3),
                }

        return None

    def build_chapter_url(self, pattern: dict[str, str], chapter_num: int) -> str:
        """Build a chapter URL from a pattern and chapter number."""
        return pattern["pattern"].format(num=chapter_num)

    def fetch_chapter(
        self,
        url: str,
        chapter_num: int,
        allow_selectors: Optional[list[str]] = None,
        block_selectors: Optional[list[str]] = None,
    ) -> Optional[ChapterInfo]:
        """
        Fetch and extract a single chapter.

        Returns ChapterInfo or None if the chapter doesn't exist or fails.
        """
        try:
            response = self.client.get(url)
            response.raise_for_status()
            html = response.text

            # Extract content
            result = extract_main_content(
                html,
                allow_selectors=allow_selectors,
                block_selectors=block_selectors,
            )

            # Extract title
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("h1") or soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else f"Chapter {chapter_num}"

            word_count = len(result["text"].split())

            return ChapterInfo(
                number=chapter_num,
                title=title,
                url=url,
                content=result["text"],
                word_count=word_count,
            )
        except (httpx.HTTPError, Exception) as exc:
            print(f"Failed to fetch chapter {chapter_num} from {url}: {exc}")
            return None

    def crawl_novel(
        self,
        start_url: str,
        start_chapter: int = 1,
        end_chapter: int = 10,
        allow_selectors: Optional[list[str]] = None,
        block_selectors: Optional[list[str]] = None,
        dataset_name: Optional[str] = None,
    ) -> NovelInfo:
        """
        Crawl a novel's chapters from start to end.

        This uses pattern detection to automatically find subsequent chapters.
        """
        # Detect pattern from start URL
        pattern = self.detect_chapter_pattern(start_url)
        if not pattern:
            raise ValueError(f"Could not detect chapter pattern from URL: {start_url}")

        # Adjust start URL if needed
        if pattern["current_num"] != start_chapter:
            start_url = self.build_chapter_url(pattern, start_chapter)

        # Fetch novel metadata from first chapter
        first_response = self.client.get(start_url)
        first_response.raise_for_status()
        first_soup = BeautifulSoup(first_response.text, "lxml")

        # Extract novel info
        title_tag = first_soup.find("h1") or first_soup.find("title")
        novel_title = title_tag.get_text(strip=True) if title_tag else "Unknown Novel"

        # Try to find author
        author = None
        author_patterns = [
            ("meta", {"name": "author"}),
            ("span", {"class": re.compile(r"author", re.I)}),
            ("div", {"class": re.compile(r"author", re.I)}),
        ]
        for tag_name, attrs in author_patterns:
            author_tag = first_soup.find(tag_name, attrs)
            if author_tag:
                author = author_tag.get("content") if tag_name == "meta" else author_tag.get_text(strip=True)
                break

        # Try to find cover image
        cover_url = None
        og_image = first_soup.find("meta", property="og:image")
        if og_image:
            cover_url = og_image.get("content")

        # Crawl chapters
        chapters: list[ChapterInfo] = []
        for chapter_num in range(start_chapter, end_chapter + 1):
            chapter_url = self.build_chapter_url(pattern, chapter_num)
            print(f"Fetching chapter {chapter_num} from {chapter_url}...")

            chapter_info = self.fetch_chapter(
                chapter_url,
                chapter_num,
                allow_selectors=allow_selectors,
                block_selectors=block_selectors,
            )

            if chapter_info:
                chapters.append(chapter_info)
            else:
                print(f"Stopping at chapter {chapter_num} (not found or error)")
                break

        return NovelInfo(
            title=novel_title,
            author=author,
            description=None,
            cover_url=cover_url,
            chapters=chapters,
            source_url=start_url,
        )

    def save_to_dataset(
        self,
        novel_info: NovelInfo,
        output_dir: Path,
        format: str = "txt",
    ) -> Path:
        """
        Save novel chapters to a dataset directory.

        Args:
            novel_info: The novel information with chapters
            output_dir: Base directory for datasets
            format: Output format ('txt', 'md', or 'jsonl')

        Returns:
            Path to the created dataset directory
        """
        import json
        from datetime import datetime, UTC

        # Create dataset directory
        dataset_dir = output_dir / novel_info.title.replace("/", "_").replace("\\", "_")
        dataset_dir.mkdir(parents=True, exist_ok=True)

        files_dir = dataset_dir / "files"
        files_dir.mkdir(exist_ok=True)

        # Save chapters
        for chapter in novel_info.chapters:
            filename = f"chapter-{chapter.number:04d}.{format}"
            file_path = files_dir / filename

            if format == "txt":
                content = f"{chapter.title}\n\n{chapter.content}"
            elif format == "md":
                content = f"# {chapter.title}\n\n{chapter.content}"
            elif format == "jsonl":
                content = json.dumps(
                    {
                        "chapter": chapter.number,
                        "title": chapter.title,
                        "content": chapter.content,
                        "url": chapter.url,
                    },
                    ensure_ascii=False,
                )
            else:
                content = chapter.content

            file_path.write_text(content, encoding="utf-8")

        # Save metadata
        meta = {
            "type": "novel",
            "title": novel_info.title,
            "author": novel_info.author,
            "description": novel_info.description,
            "cover_url": novel_info.cover_url,
            "source_url": novel_info.source_url,
            "chapter_count": len(novel_info.chapters),
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "total_words": sum(ch.word_count for ch in novel_info.chapters),
            "chapters": [
                {
                    "number": ch.number,
                    "title": ch.title,
                    "url": ch.url,
                    "word_count": ch.word_count,
                }
                for ch in novel_info.chapters
            ],
        }

        meta_file = dataset_dir / "meta.json"
        meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

        return dataset_dir


def try_lightnovel_crawler_integration(url: str, output_dir: Path) -> Optional[Path]:
    """
    Attempt to use lightnovel-crawler if it's installed.

    This is an optional integration for users who have lightnovel-crawler
    installed separately. The lightnovel-crawler package is GPLv3 licensed.

    Returns the dataset path if successful, None otherwise.

    Note: This function is deprecated. Use lncrawl_adapter.fetch_novel() instead.
    """
    try:
        # Try to import lightnovel-crawler (optional dependency)
        from lncrawl.core.app import App  # noqa: F401

        # This integration is now handled by lncrawl_adapter.py
        print("lightnovel-crawler available - use lncrawl_adapter.fetch_novel()")
        return None

    except ImportError:
        print("lightnovel-crawler not installed (optional GPLv3 component)")
        return None
