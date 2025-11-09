"""
Main crawl engine that orchestrates the crawling process
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime

from .models import (
    NovelTOC,
    ChapterContent,
    CrawlOptions,
    CrawlProgress,
    ExportFormat,
    UpdateMode
)
from .adapter_base import AdapterRegistry
from .fetch_httpx import PoliteFetcher
from ..exporters import JSONExporter, TXTExporter, EPUBExporter, HTMLExporter


class CrawlEngine:
    """Main engine for crawling novels"""

    def __init__(self, registry: AdapterRegistry):
        self.registry = registry

    async def crawl(
        self,
        options: CrawlOptions,
        progress_callback: Optional[Callable[[CrawlProgress], None]] = None
    ) -> Path:
        """
        Crawl a novel and export to specified formats.

        Args:
            options: Crawl options
            progress_callback: Optional callback for progress updates

        Returns:
            Path to output directory

        Raises:
            ValueError: If no adapter can handle the URL
            RuntimeError: If crawl fails
        """
        # Get appropriate adapter
        adapter_class = self.registry.get_adapter(options.url)
        if adapter_class is None:
            raise ValueError(f"No adapter found for URL: {options.url}")

        # Create fetcher
        fetcher = PoliteFetcher(
            user_agent=options.user_agent,
            delay_ms=options.delay_ms,
            max_concurrency=options.max_concurrency,
            respect_robots=options.respect_robots
        )

        try:
            async with fetcher:
                # Create adapter instance
                adapter = adapter_class(fetcher)

                # Get TOC
                toc = await adapter.get_toc(options.url)

                # Override novel name if provided
                if options.novel_name:
                    toc.title = options.novel_name

                # Override author if provided
                if options.author_override:
                    toc.author = options.author_override

                # Get selected chapters
                selected_chapters = options.get_selected_chapters(toc)

                # Check existing chapters if in UPDATE_ONLY mode
                if options.update_mode == UpdateMode.UPDATE_ONLY:
                    existing_chapters = self._get_existing_chapters(options.output_dir)
                    # Filter out already downloaded chapters
                    selected_chapters = [
                        ch for ch in selected_chapters
                        if ch.index not in existing_chapters
                    ]

                # Initialize progress
                progress = CrawlProgress(total_chapters=len(selected_chapters))

                if progress_callback:
                    progress_callback(progress)

                # Download chapters
                chapters: List[ChapterContent] = []

                for chapter_ref in selected_chapters:
                    try:
                        progress.current_chapter = chapter_ref.title

                        # Download chapter
                        chapter = await adapter.get_chapter(chapter_ref)
                        chapters.append(chapter)

                        progress.downloaded += 1

                        if progress_callback:
                            progress_callback(progress)

                    except Exception as e:
                        error_msg = f"Failed to download chapter {chapter_ref.index}: {str(e)}"
                        progress.errors.append((chapter_ref, error_msg))
                        progress.failed += 1

                        if progress_callback:
                            progress_callback(progress)

                        # Continue with next chapter
                        continue

                # Export to requested formats
                await self._export_novel(toc, chapters, options)

                return options.output_dir

        finally:
            await fetcher.close()

    def _get_existing_chapters(self, output_dir: Path) -> set:
        """Get set of existing chapter indices"""
        # Check chapters directory
        chapters_dir = output_dir / "chapters"
        if not chapters_dir.exists():
            return set()

        existing = set()
        for file in chapters_dir.glob("*.html"):
            try:
                # Extract chapter number from filename (e.g., "00042.html" -> 42)
                index = int(file.stem)
                existing.add(index)
            except ValueError:
                continue

        return existing

    async def _export_novel(
        self,
        toc: NovelTOC,
        chapters: List[ChapterContent],
        options: CrawlOptions
    ):
        """Export novel to requested formats"""
        output_dir = options.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create safe filename
        safe_title = "".join(c for c in toc.title if c.isalnum() or c in (' ', '-', '_')).strip()

        for fmt in options.formats:
            try:
                if fmt == ExportFormat.JSON:
                    JSONExporter.export(
                        toc,
                        chapters,
                        output_dir / f"{safe_title}.json"
                    )

                elif fmt == ExportFormat.TXT:
                    TXTExporter.export(
                        toc,
                        chapters,
                        output_dir / f"{safe_title}.txt"
                    )

                elif fmt == ExportFormat.EPUB:
                    EPUBExporter.export(
                        toc,
                        chapters,
                        output_dir / f"{safe_title}.epub"
                    )

                elif fmt == ExportFormat.HTML:
                    HTMLExporter.export(
                        toc,
                        chapters,
                        output_dir / f"{safe_title}.html"
                    )

                else:
                    # Calibre-dependent formats
                    print(f"Warning: Format {fmt.value} requires Calibre ebook-convert (not yet implemented)")

            except Exception as e:
                print(f"Warning: Failed to export to {fmt.value}: {e}")

        # Save individual chapter HTML files
        chapters_dir = output_dir / "chapters"
        chapters_dir.mkdir(exist_ok=True)

        for chapter in chapters:
            chapter_file = chapters_dir / f"{chapter.ref.index:05d}.html"
            with open(chapter_file, 'w', encoding='utf-8') as f:
                f.write(chapter.html)

        # Download images if any
        # TODO: Implement image downloading
        pass
