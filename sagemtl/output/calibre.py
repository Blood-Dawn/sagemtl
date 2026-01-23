"""Calibre integration for additional export formats.

This module provides integration with Calibre's ebook-convert tool
to support additional formats like MOBI, AZW3, FB2, and LRF.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from .base import (
    BaseExporter,
    ExportCapability,
    ExportConfig,
    ExportResult,
    NovelData,
)
from .epub_exporter import EpubExporter

logger = logging.getLogger(__name__)

# Calibre ebook-convert path
_CALIBRE_PATH: Optional[Path] = None


def has_calibre() -> bool:
    """Check if Calibre's ebook-convert is available."""
    return get_calibre_path() is not None


def get_calibre_path() -> Optional[Path]:
    """Get the path to Calibre's ebook-convert executable."""
    global _CALIBRE_PATH

    if _CALIBRE_PATH is not None:
        return _CALIBRE_PATH

    # Try to find ebook-convert in PATH
    path = shutil.which("ebook-convert")
    if path:
        _CALIBRE_PATH = Path(path)
        return _CALIBRE_PATH

    # Check common installation locations
    common_paths = [
        # Windows
        Path("C:/Program Files/Calibre2/ebook-convert.exe"),
        Path("C:/Program Files (x86)/Calibre2/ebook-convert.exe"),
        # macOS
        Path("/Applications/calibre.app/Contents/MacOS/ebook-convert"),
        # Linux
        Path("/usr/bin/ebook-convert"),
        Path("/usr/local/bin/ebook-convert"),
    ]

    for p in common_paths:
        if p.exists():
            _CALIBRE_PATH = p
            return _CALIBRE_PATH

    return None


class CalibreExporter(BaseExporter):
    """Export novel using Calibre's ebook-convert.

    Supports formats:
    - MOBI (Kindle legacy)
    - AZW3 (Kindle KF8)
    - FB2 (FictionBook)
    - LRF (Sony Reader)
    - And any other format supported by Calibre

    Requires Calibre to be installed.
    """

    # Format-specific settings
    FORMAT_OPTIONS = {
        "mobi": [
            "--mobi-file-type=both",
            "--personal-doc=[PDOC]",
        ],
        "azw3": [
            "--no-inline-toc",
        ],
        "fb2": [
            "--fb2-genre=sf_fantasy",
        ],
        "lrf": [
            "--lrf-parser=",
        ],
    }

    def __init__(self, target_format: str = "mobi"):
        """Initialize with target format.

        Args:
            target_format: Target format (mobi, azw3, fb2, lrf, etc.)
        """
        self._target_format = target_format.lower()

    @classmethod
    def name(cls) -> str:
        return "Calibre"

    @classmethod
    def extensions(cls) -> List[str]:
        return ["mobi", "azw3", "fb2", "lrf"]

    @classmethod
    def capabilities(cls) -> ExportCapability:
        return (
            ExportCapability.COVER |
            ExportCapability.TOC |
            ExportCapability.METADATA |
            ExportCapability.STYLES |
            ExportCapability.IMAGES |
            ExportCapability.VOLUMES |
            ExportCapability.BOOKMARKS
        )

    @classmethod
    def is_available(cls) -> bool:
        return has_calibre()

    def export(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> ExportResult:
        """Export novel using Calibre."""
        calibre_path = get_calibre_path()
        if not calibre_path:
            return ExportResult.failure(
                "Calibre is required for this format. "
                "Download from: https://calibre-ebook.com/download"
            )

        # Generate output path
        output_path = self._get_output_path(
            novel, config, extension=self._target_format
        )

        try:
            # First, export to EPUB (as intermediate format)
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_epub = Path(temp_dir) / "temp.epub"

                # Export to EPUB
                epub_exporter = EpubExporter()
                epub_config = ExportConfig(
                    output_path=Path(temp_dir),
                    filename_template="temp",
                    include_cover=config.include_cover,
                    include_toc=config.include_toc,
                    include_metadata=config.include_metadata,
                    custom_css=config.custom_css,
                    font_family=config.font_family,
                    font_size=config.font_size,
                    title=config.title,
                    author=config.author,
                    language=config.language,
                )
                epub_result = epub_exporter.export(novel, epub_config)

                if not epub_result.success:
                    return ExportResult.failure(
                        f"Failed to create intermediate EPUB: {epub_result.error}"
                    )

                # Convert EPUB to target format using Calibre
                cmd = [
                    str(calibre_path),
                    str(temp_epub),
                    str(output_path),
                ]

                # Add format-specific options
                if self._target_format in self.FORMAT_OPTIONS:
                    cmd.extend(self.FORMAT_OPTIONS[self._target_format])

                # Add metadata options
                title = config.title or novel.title
                author = config.author or novel.author

                cmd.extend([
                    f"--title={title}",
                ])
                if author:
                    cmd.extend([f"--authors={author}"])

                # Run conversion
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )

                if result.returncode != 0:
                    return ExportResult.failure(
                        f"Calibre conversion failed: {result.stderr}"
                    )

                if not output_path.exists():
                    return ExportResult.failure(
                        "Calibre conversion completed but output file not found"
                    )

            return ExportResult.ok(output_path)

        except subprocess.TimeoutExpired:
            return ExportResult.failure("Calibre conversion timed out")
        except Exception as e:
            return ExportResult.failure(str(e))


def convert_with_calibre(
    input_path: Path,
    output_path: Path,
    **options,
) -> bool:
    """Convert an ebook using Calibre.

    Args:
        input_path: Input file path
        output_path: Output file path
        **options: Additional options for ebook-convert

    Returns:
        True if conversion succeeded, False otherwise
    """
    calibre_path = get_calibre_path()
    if not calibre_path:
        logger.error("Calibre not found")
        return False

    cmd = [str(calibre_path), str(input_path), str(output_path)]

    # Add options
    for key, value in options.items():
        if value is True:
            cmd.append(f"--{key}")
        elif value is not False and value is not None:
            cmd.append(f"--{key}={value}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Calibre conversion failed: {e}")
        return False


def list_calibre_formats() -> List[str]:
    """List all output formats supported by Calibre."""
    calibre_path = get_calibre_path()
    if not calibre_path:
        return []

    try:
        # Get help output which lists formats
        result = subprocess.run(
            [str(calibre_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Parse supported formats (this is a simplified list)
        # Full list depends on Calibre version
        return [
            "azw3", "docx", "epub", "fb2", "htmlz", "lit",
            "lrf", "mobi", "oeb", "pdb", "pdf", "pml",
            "rb", "rtf", "snb", "tcr", "txt", "txtz", "zip"
        ]
    except Exception:
        return []
