"""
Data models for SageCrawler
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from datetime import datetime
from pathlib import Path


class ExportFormat(Enum):
    """Supported export formats"""
    JSON = "json"
    EPUB = "epub"
    HTML = "html"
    TXT = "txt"
    # Calibre-dependent formats
    DOCX = "docx"
    MOBI = "mobi"
    PDF = "pdf"
    RTF = "rtf"
    AZW3 = "azw3"
    FB2 = "fb2"
    LIT = "lit"
    LRF = "lrf"
    OEB = "oeb"
    PDB = "pdb"
    RB = "rb"
    SNB = "snb"
    TCR = "tcr"

    @property
    def requires_calibre(self) -> bool:
        """Check if format requires Calibre ebook-convert"""
        native = {ExportFormat.JSON, ExportFormat.EPUB, ExportFormat.HTML, ExportFormat.TXT}
        return self not in native


class UpdateMode(Enum):
    """How to handle existing novel directories"""
    UPDATE_ONLY = "update_only"  # Download remaining chapters only
    FRESH = "fresh"  # Remove old folder and start fresh


@dataclass
class ChapterRef:
    """Reference to a chapter"""
    index: int
    title: str
    url: str
    volume: Optional[str] = None


@dataclass
class ChapterContent:
    """Downloaded chapter content"""
    ref: ChapterRef
    html: str
    text: str  # Plain text version
    images: List[str] = field(default_factory=list)  # Image URLs found in content
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NovelTOC:
    """Novel table of contents"""
    title: str
    author: str
    url: str
    cover_url: Optional[str] = None
    description: Optional[str] = None
    chapters: List[ChapterRef] = field(default_factory=list)
    volumes: List[str] = field(default_factory=list)
    status: str = "Unknown"  # Ongoing, Completed, Hiatus, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)


@dataclass
class SearchHit:
    """Search result from a source"""
    title: str
    author: str
    url: str
    source: str  # Source adapter name (e.g., "fanmtl")
    cover_url: Optional[str] = None
    description: Optional[str] = None
    chapter_count: Optional[int] = None
    status: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrawlOptions:
    """Options for crawling a novel"""
    url: str
    output_dir: Path
    novel_name: Optional[str] = None

    # Chapter selection
    first_chapter: Optional[int] = None
    last_chapter: Optional[int] = None
    chapter_range: Optional[Tuple[int, int]] = None
    chapter_indices: Optional[List[int]] = None

    # Export formats
    formats: List[ExportFormat] = field(default_factory=lambda: [
        ExportFormat.JSON, ExportFormat.EPUB, ExportFormat.HTML
    ])

    # Update mode
    update_mode: UpdateMode = UpdateMode.UPDATE_ONLY

    # Fetching options
    use_browser: bool = False  # Use Playwright for JS-rendered pages
    max_concurrency: int = 6
    delay_ms: Tuple[int, int] = (500, 1500)  # Min/max delay between requests
    respect_robots: bool = True
    user_agent: str = "SageMTL Crawler/1.0 (https://github.com/sagemtl)"

    # Export options
    author_override: Optional[str] = None

    def get_selected_chapters(self, toc: NovelTOC) -> List[ChapterRef]:
        """Get the list of chapters to download based on selection options"""
        all_chapters = toc.chapters

        # If specific indices are provided
        if self.chapter_indices:
            return [all_chapters[i - 1] for i in self.chapter_indices if 0 < i <= len(all_chapters)]

        # If range is provided
        if self.chapter_range:
            start, end = self.chapter_range
            start_idx = max(0, start - 1)
            end_idx = min(len(all_chapters), end)
            return all_chapters[start_idx:end_idx]

        # If first/last are provided
        start_idx = (self.first_chapter - 1) if self.first_chapter else 0
        end_idx = self.last_chapter if self.last_chapter else len(all_chapters)

        start_idx = max(0, start_idx)
        end_idx = min(len(all_chapters), end_idx)

        return all_chapters[start_idx:end_idx]


@dataclass
class CrawlProgress:
    """Progress tracking for a crawl job"""
    total_chapters: int
    downloaded: int = 0
    failed: int = 0
    skipped: int = 0  # Already downloaded
    current_chapter: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    errors: List[Tuple[ChapterRef, str]] = field(default_factory=list)

    @property
    def percent_complete(self) -> float:
        if self.total_chapters == 0:
            return 0.0
        return (self.downloaded + self.failed + self.skipped) / self.total_chapters * 100

    @property
    def chapters_per_second(self) -> float:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return 0.0
        return self.downloaded / elapsed
