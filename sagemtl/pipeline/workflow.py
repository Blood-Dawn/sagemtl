"""End-to-end workflow for SageMTL.

This module provides the integrated pipeline that orchestrates:
1. Novel download (crawler)
2. Translation (translation pipeline)
3. Export (output system)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    """Status of a pipeline execution."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSLATING = "translating"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineConfig:
    """Configuration for the end-to-end pipeline."""

    # Source
    url: str = ""
    novel_id: Optional[str] = None

    # Download settings
    download_chapters: bool = True
    chapter_range: Optional[tuple] = None  # (start, end) or None for all
    download_cover: bool = True
    cache_html: bool = True

    # Translation settings
    translate: bool = True
    translation_provider: str = "argos"
    source_language: str = "zh"
    target_language: str = "en"
    use_glossary: bool = True
    glossary_path: Optional[Path] = None

    # Export settings
    export_formats: List[str] = field(default_factory=lambda: ["epub"])
    output_directory: Path = field(default_factory=lambda: Path("./output"))
    include_cover: bool = True
    include_toc: bool = True

    # Advanced
    concurrent_downloads: int = 3
    request_delay_ms: int = 500
    max_retries: int = 3
    timeout_seconds: int = 30


@dataclass
class PipelineProgress:
    """Progress information for pipeline execution."""

    status: PipelineStatus = PipelineStatus.PENDING
    current_step: str = ""
    total_chapters: int = 0
    downloaded_chapters: int = 0
    translated_chapters: int = 0
    exported_formats: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def download_percent(self) -> float:
        """Get download progress percentage."""
        if self.total_chapters == 0:
            return 0.0
        return (self.downloaded_chapters / self.total_chapters) * 100

    @property
    def translation_percent(self) -> float:
        """Get translation progress percentage."""
        if self.total_chapters == 0:
            return 0.0
        return (self.translated_chapters / self.total_chapters) * 100


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""

    success: bool
    novel_id: str = ""
    novel_title: str = ""
    output_files: List[Path] = field(default_factory=list)
    progress: PipelineProgress = field(default_factory=PipelineProgress)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def failure(cls, error: str, progress: Optional[PipelineProgress] = None) -> "PipelineResult":
        """Create a failure result."""
        return cls(
            success=False,
            error=error,
            progress=progress or PipelineProgress(status=PipelineStatus.FAILED),
        )


class SageMTLPipeline:
    """End-to-end pipeline for novel processing.

    Orchestrates the complete workflow:
    1. Download novel from URL
    2. Translate content (optional)
    3. Export to desired formats

    Usage:
        pipeline = SageMTLPipeline(PipelineConfig(
            url="https://example.com/novel/123",
            translate=True,
            export_formats=["epub", "pdf"],
        ))

        result = await pipeline.run()
        if result.success:
            print(f"Created: {result.output_files}")
    """

    def __init__(
        self,
        config: PipelineConfig,
        progress_callback: Optional[Callable[[PipelineProgress], None]] = None,
    ):
        """Initialize the pipeline.

        Args:
            config: Pipeline configuration.
            progress_callback: Optional callback for progress updates.
        """
        self.config = config
        self._progress_callback = progress_callback
        self._progress = PipelineProgress()
        self._cancelled = False

    @property
    def progress(self) -> PipelineProgress:
        """Get current progress."""
        return self._progress

    def cancel(self) -> None:
        """Cancel the pipeline execution."""
        self._cancelled = True
        self._progress.status = PipelineStatus.CANCELLED

    async def run(self) -> PipelineResult:
        """Run the complete pipeline.

        Returns:
            PipelineResult with success status and output files.
        """
        self._progress.started_at = datetime.now()
        self._progress.status = PipelineStatus.PENDING
        self._notify_progress()

        try:
            # Step 1: Download
            if self._cancelled:
                return self._cancelled_result()

            novel_data = await self._download_novel()
            if novel_data is None:
                return PipelineResult.failure(
                    "Failed to download novel",
                    self._progress,
                )

            # Step 2: Translate (optional)
            if self.config.translate and not self._cancelled:
                translated_data = await self._translate_novel(novel_data)
                if translated_data is not None:
                    novel_data = translated_data

            # Step 3: Export
            if self._cancelled:
                return self._cancelled_result()

            output_files = await self._export_novel(novel_data)

            # Complete
            self._progress.status = PipelineStatus.COMPLETED
            self._progress.completed_at = datetime.now()
            self._notify_progress()

            return PipelineResult(
                success=True,
                novel_id=getattr(novel_data, "id", ""),
                novel_title=getattr(novel_data, "title", ""),
                output_files=output_files,
                progress=self._progress,
                metadata={
                    "url": self.config.url,
                    "translated": self.config.translate,
                    "formats": self.config.export_formats,
                },
            )

        except Exception as e:
            logger.exception("Pipeline failed")
            self._progress.status = PipelineStatus.FAILED
            self._progress.errors.append(str(e))
            self._notify_progress()
            return PipelineResult.failure(str(e), self._progress)

    async def _download_novel(self) -> Optional[Any]:
        """Download novel from URL."""
        self._progress.status = PipelineStatus.DOWNLOADING
        self._progress.current_step = "Downloading novel metadata..."
        self._notify_progress()

        try:
            # Import crawler components
            from sagemtl_crawler.core.adapter_base import AdapterRegistry
            from sagemtl_crawler.core.fetch_httpx import HttpxFetcher

            # Get adapter for URL
            adapter = AdapterRegistry.get_adapter_for_url(self.config.url)
            if adapter is None:
                self._progress.errors.append(f"No adapter found for URL: {self.config.url}")
                return None

            # Create fetcher
            async with HttpxFetcher() as fetcher:
                # Set adapter's fetcher
                adapter._fetcher = fetcher

                # Get table of contents
                self._progress.current_step = "Fetching table of contents..."
                self._notify_progress()

                toc = await adapter.get_toc(self.config.url)
                if toc is None:
                    self._progress.errors.append("Failed to fetch table of contents")
                    return None

                # Determine chapters to download
                chapters_to_download = list(toc.chapters)
                if self.config.chapter_range:
                    start, end = self.config.chapter_range
                    chapters_to_download = [
                        c for c in chapters_to_download
                        if start <= c.index <= end
                    ]

                self._progress.total_chapters = len(chapters_to_download)

                # Download chapters
                chapters = []
                for i, chapter_ref in enumerate(chapters_to_download):
                    if self._cancelled:
                        break

                    self._progress.current_step = f"Downloading chapter {i + 1}/{len(chapters_to_download)}"
                    self._notify_progress()

                    try:
                        content = await adapter.get_chapter(chapter_ref.url)
                        if content:
                            chapters.append(content)
                            self._progress.downloaded_chapters = i + 1
                            self._notify_progress()

                        # Delay between requests
                        if self.config.request_delay_ms > 0:
                            await asyncio.sleep(self.config.request_delay_ms / 1000)

                    except Exception as e:
                        self._progress.warnings.append(
                            f"Failed to download chapter {chapter_ref.index}: {e}"
                        )

                # Build novel data for export
                from sagemtl.output.base import NovelData, ChapterData, VolumeData

                novel_data = NovelData(
                    title=toc.title,
                    author=toc.author,
                    description=toc.synopsis or "",
                    cover_url=toc.cover_url,
                    source_url=self.config.url,
                    chapters=[
                        ChapterData(
                            index=ch.ref.index,
                            title=ch.ref.title,
                            content=ch.text,
                            html_content=ch.html,
                            volume_index=ch.ref.volume_index,
                        )
                        for ch in chapters
                    ],
                )

                return novel_data

        except ImportError as e:
            self._progress.errors.append(f"Crawler not available: {e}")
            return None
        except Exception as e:
            self._progress.errors.append(f"Download failed: {e}")
            return None

    async def _translate_novel(self, novel_data: Any) -> Optional[Any]:
        """Translate novel content."""
        self._progress.status = PipelineStatus.TRANSLATING
        self._progress.current_step = "Initializing translation..."
        self._notify_progress()

        try:
            from sagemtl.translate.pipeline import TranslationPipeline, TranslationConfig

            # Create translation pipeline
            trans_config = TranslationConfig(
                provider_name=self.config.translation_provider,
                source_lang=self.config.source_language,
                target_lang=self.config.target_language,
                use_glossary_db=self.config.use_glossary,
                glossary_path=str(self.config.glossary_path) if self.config.glossary_path else None,
            )
            pipeline = TranslationPipeline(trans_config)

            # Translate each chapter
            for i, chapter in enumerate(novel_data.chapters):
                if self._cancelled:
                    break

                self._progress.current_step = f"Translating chapter {i + 1}/{len(novel_data.chapters)}"
                self._notify_progress()

                try:
                    result = await pipeline.translate(chapter.content)
                    chapter.content = result.translated_text
                    self._progress.translated_chapters = i + 1
                    self._notify_progress()
                except Exception as e:
                    self._progress.warnings.append(
                        f"Translation failed for chapter {chapter.index}: {e}"
                    )

            return novel_data

        except ImportError as e:
            self._progress.warnings.append(f"Translation not available: {e}")
            return None
        except Exception as e:
            self._progress.warnings.append(f"Translation failed: {e}")
            return None

    async def _export_novel(self, novel_data: Any) -> List[Path]:
        """Export novel to configured formats."""
        self._progress.status = PipelineStatus.EXPORTING
        self._progress.current_step = "Exporting..."
        self._notify_progress()

        output_files = []

        try:
            from sagemtl.output.base import ExporterRegistry, ExportConfig

            export_config = ExportConfig(
                output_path=self.config.output_directory,
                include_cover=self.config.include_cover,
                include_toc=self.config.include_toc,
            )

            for format_id in self.config.export_formats:
                if self._cancelled:
                    break

                self._progress.current_step = f"Exporting to {format_id.upper()}..."
                self._notify_progress()

                exporter = ExporterRegistry.create(format_id)
                if exporter is None:
                    self._progress.warnings.append(f"Format not available: {format_id}")
                    continue

                try:
                    result = exporter.export(novel_data, export_config)
                    if result.success:
                        output_files.extend(result.files_created)
                        self._progress.exported_formats += 1
                    else:
                        self._progress.warnings.append(
                            f"Export to {format_id} failed: {result.error}"
                        )
                except Exception as e:
                    self._progress.warnings.append(f"Export to {format_id} failed: {e}")

                self._notify_progress()

        except Exception as e:
            self._progress.errors.append(f"Export failed: {e}")

        return output_files

    def _notify_progress(self) -> None:
        """Notify progress callback."""
        if self._progress_callback:
            try:
                self._progress_callback(self._progress)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")

    def _cancelled_result(self) -> PipelineResult:
        """Create a cancelled result."""
        return PipelineResult(
            success=False,
            error="Pipeline was cancelled",
            progress=self._progress,
        )


async def run_pipeline(
    url: str,
    translate: bool = True,
    export_formats: Optional[List[str]] = None,
    output_directory: Optional[Path] = None,
    progress_callback: Optional[Callable[[PipelineProgress], None]] = None,
) -> PipelineResult:
    """Convenience function to run the pipeline.

    Args:
        url: Novel URL to process.
        translate: Whether to translate content.
        export_formats: List of export formats (default: ["epub"]).
        output_directory: Output directory (default: ./output).
        progress_callback: Optional progress callback.

    Returns:
        PipelineResult with success status and output files.
    """
    config = PipelineConfig(
        url=url,
        translate=translate,
        export_formats=export_formats or ["epub"],
        output_directory=output_directory or Path("./output"),
    )

    pipeline = SageMTLPipeline(config, progress_callback)
    return await pipeline.run()
