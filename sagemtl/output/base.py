"""Base exporter protocol and registry for SageMTL.

This module defines the exporter interface and provides a registry
for discovering and instantiating exporters by format.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Flag, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Type, runtime_checkable

logger = logging.getLogger(__name__)


class ExportCapability(Flag):
    """Capabilities supported by an exporter."""

    NONE = 0
    COVER = auto()  # Supports cover image
    TOC = auto()  # Supports table of contents
    METADATA = auto()  # Supports metadata (title, author, etc.)
    STYLES = auto()  # Supports custom styling
    IMAGES = auto()  # Supports inline images
    VOLUMES = auto()  # Supports volume grouping
    BOOKMARKS = auto()  # Supports bookmarks/navigation
    HYPERLINKS = auto()  # Supports hyperlinks


@dataclass
class ExportConfig:
    """Configuration for export operation."""

    # Output settings
    output_path: Path = field(default_factory=lambda: Path("./output"))
    filename_template: str = "{title}"  # Supports {title}, {author}, {date}

    # Content settings
    include_cover: bool = True
    include_toc: bool = True
    include_metadata: bool = True

    # Volume handling
    split_by_volume: bool = False
    volume_page_break: bool = True

    # Styling
    custom_css: Optional[str] = None
    font_family: str = "serif"
    font_size: int = 12

    # Metadata overrides
    title: Optional[str] = None
    author: Optional[str] = None
    language: str = "en"

    # Advanced
    compress: bool = True
    extra_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportResult:
    """Result of an export operation."""

    success: bool
    output_path: Optional[Path] = None
    files_created: List[Path] = field(default_factory=list)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def failure(cls, error: str) -> "ExportResult":
        """Create a failure result."""
        return cls(success=False, error=error)

    @classmethod
    def ok(cls, output_path: Path, files: Optional[List[Path]] = None) -> "ExportResult":
        """Create a success result."""
        return cls(
            success=True,
            output_path=output_path,
            files_created=files or [output_path],
        )


@dataclass
class NovelData:
    """Novel data for export."""

    title: str
    author: str = ""
    description: str = ""
    cover_path: Optional[Path] = None
    cover_url: Optional[str] = None
    language: str = "en"
    genres: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    chapters: List["ChapterData"] = field(default_factory=list)
    volumes: List["VolumeData"] = field(default_factory=list)

    @property
    def total_chapters(self) -> int:
        """Get total chapter count."""
        return len(self.chapters)

    @property
    def total_words(self) -> int:
        """Estimate total word count."""
        return sum(ch.word_count for ch in self.chapters)


@dataclass
class VolumeData:
    """Volume data for export."""

    index: int
    title: str
    chapter_start: int  # Index of first chapter
    chapter_end: int  # Index of last chapter (inclusive)


@dataclass
class ChapterData:
    """Chapter data for export."""

    index: int
    title: str
    content: str  # Plain text content
    html_content: Optional[str] = None  # HTML formatted content
    volume_index: Optional[int] = None
    word_count: int = 0

    def __post_init__(self):
        if self.word_count == 0 and self.content:
            self.word_count = len(self.content.split())


@runtime_checkable
class Exporter(Protocol):
    """Protocol for exporters."""

    @classmethod
    def name(cls) -> str:
        """Get the exporter name."""
        ...

    @classmethod
    def extensions(cls) -> List[str]:
        """Get supported file extensions."""
        ...

    @classmethod
    def capabilities(cls) -> ExportCapability:
        """Get exporter capabilities."""
        ...

    @classmethod
    def is_available(cls) -> bool:
        """Check if the exporter dependencies are available."""
        ...

    def export(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> ExportResult:
        """Export novel to the target format."""
        ...


class BaseExporter(ABC):
    """Abstract base class for exporters."""

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """Get the exporter name."""
        pass

    @classmethod
    @abstractmethod
    def extensions(cls) -> List[str]:
        """Get supported file extensions."""
        pass

    @classmethod
    def capabilities(cls) -> ExportCapability:
        """Get exporter capabilities. Override in subclasses."""
        return ExportCapability.NONE

    @classmethod
    def is_available(cls) -> bool:
        """Check if the exporter dependencies are available."""
        return True

    @abstractmethod
    def export(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> ExportResult:
        """Export novel to the target format."""
        pass

    def _get_output_path(
        self,
        novel: NovelData,
        config: ExportConfig,
        extension: Optional[str] = None,
    ) -> Path:
        """Generate output file path."""
        ext = extension or self.extensions()[0]

        # Apply filename template
        filename = config.filename_template.format(
            title=self._sanitize_filename(config.title or novel.title),
            author=self._sanitize_filename(config.author or novel.author),
            date=__import__("datetime").datetime.now().strftime("%Y%m%d"),
        )

        if not filename.endswith(f".{ext}"):
            filename = f"{filename}.{ext}"

        output_path = config.output_path / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        return output_path

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize a string for use as a filename."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        # Remove leading/trailing whitespace and dots
        name = name.strip('. ')
        # Limit length
        if len(name) > 200:
            name = name[:200]
        return name or "untitled"

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        import html
        return html.escape(text)

    @staticmethod
    def _text_to_html(text: str) -> str:
        """Convert plain text to basic HTML."""
        import html
        escaped = html.escape(text)
        # Convert paragraphs
        paragraphs = escaped.split('\n\n')
        html_content = '\n'.join(f'<p>{p}</p>' for p in paragraphs if p.strip())
        return html_content


class ExporterRegistry:
    """Registry for discovering and instantiating exporters."""

    _exporters: Dict[str, Type[BaseExporter]] = {}

    @classmethod
    def register(cls, format_id: str, exporter_class: Type[BaseExporter]) -> None:
        """Register an exporter for a format."""
        cls._exporters[format_id.lower()] = exporter_class

    @classmethod
    def get(cls, format_id: str) -> Optional[Type[BaseExporter]]:
        """Get an exporter class by format ID."""
        return cls._exporters.get(format_id.lower())

    @classmethod
    def create(cls, format_id: str) -> Optional[BaseExporter]:
        """Create an exporter instance."""
        exporter_class = cls.get(format_id)
        if exporter_class and exporter_class.is_available():
            return exporter_class()
        return None

    @classmethod
    def list_formats(cls) -> List[str]:
        """List all registered format IDs."""
        return list(cls._exporters.keys())

    @classmethod
    def list_available(cls) -> List[str]:
        """List formats with available dependencies."""
        return [
            fmt for fmt, exp in cls._exporters.items()
            if exp.is_available()
        ]

    @classmethod
    def get_info(cls, format_id: str) -> Optional[Dict[str, Any]]:
        """Get information about an exporter."""
        exporter_class = cls.get(format_id)
        if not exporter_class:
            return None

        return {
            "format": format_id,
            "name": exporter_class.name(),
            "extensions": exporter_class.extensions(),
            "capabilities": exporter_class.capabilities(),
            "available": exporter_class.is_available(),
        }

    @classmethod
    def get_for_extension(cls, extension: str) -> Optional[Type[BaseExporter]]:
        """Get an exporter by file extension."""
        ext = extension.lstrip('.')
        for exporter_class in cls._exporters.values():
            if ext in exporter_class.extensions():
                return exporter_class
        return None


def export_novel(
    novel: NovelData,
    format_id: str,
    config: Optional[ExportConfig] = None,
) -> ExportResult:
    """Export a novel to the specified format.

    Args:
        novel: Novel data to export.
        format_id: Target format ID (e.g., "epub", "pdf").
        config: Export configuration (uses defaults if not provided).

    Returns:
        ExportResult with success status and output path.
    """
    config = config or ExportConfig()

    exporter = ExporterRegistry.create(format_id)
    if not exporter:
        available = ExporterRegistry.list_available()
        return ExportResult.failure(
            f"Format '{format_id}' is not available. "
            f"Available formats: {', '.join(available)}"
        )

    try:
        return exporter.export(novel, config)
    except Exception as e:
        logger.exception(f"Export failed for format {format_id}")
        return ExportResult.failure(str(e))
