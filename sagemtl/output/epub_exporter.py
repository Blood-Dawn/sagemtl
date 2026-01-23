"""EPUB exporter for SageMTL."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import uuid

from .base import (
    BaseExporter,
    ExportCapability,
    ExportConfig,
    ExportResult,
    NovelData,
)

try:
    from ebooklib import epub
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False


class EpubExporter(BaseExporter):
    """Export novel to EPUB format.

    Features:
    - Full metadata support
    - Cover image embedding
    - Table of contents with navigation
    - Volume grouping
    - Custom CSS styling
    """

    @classmethod
    def name(cls) -> str:
        return "EPUB"

    @classmethod
    def extensions(cls) -> List[str]:
        return ["epub"]

    @classmethod
    def capabilities(cls) -> ExportCapability:
        return (
            ExportCapability.COVER |
            ExportCapability.TOC |
            ExportCapability.METADATA |
            ExportCapability.STYLES |
            ExportCapability.IMAGES |
            ExportCapability.VOLUMES |
            ExportCapability.BOOKMARKS |
            ExportCapability.HYPERLINKS
        )

    @classmethod
    def is_available(cls) -> bool:
        return HAS_EBOOKLIB

    def export(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> ExportResult:
        """Export novel to EPUB file."""
        if not HAS_EBOOKLIB:
            return ExportResult.failure(
                "ebooklib is required for EPUB export. "
                "Install with: pip install ebooklib"
            )

        output_path = self._get_output_path(novel, config)

        try:
            book = epub.EpubBook()

            # Set metadata
            book.set_identifier(f"sagemtl-{uuid.uuid4().hex[:12]}")
            book.set_title(config.title or novel.title)
            book.set_language(config.language or novel.language)
            if novel.author:
                book.add_author(config.author or novel.author)

            # Add description
            if novel.description:
                book.add_metadata('DC', 'description', novel.description)

            # Add genres as subjects
            for genre in novel.genres:
                book.add_metadata('DC', 'subject', genre)

            # Add source URL
            if novel.source_url:
                book.add_metadata('DC', 'source', novel.source_url)

            # Add cover image
            if config.include_cover:
                self._add_cover(book, novel)

            # Create CSS
            css_content = self._get_css(config)
            css_item = epub.EpubItem(
                uid="style",
                file_name="style/main.css",
                media_type="text/css",
                content=css_content.encode('utf-8')
            )
            book.add_item(css_item)

            # Create chapters
            epub_chapters = []
            toc_items = []
            current_volume = None
            volume_chapters = []

            for chapter in novel.chapters:
                # Handle volume grouping
                if chapter.volume_index is not None and chapter.volume_index != current_volume:
                    if current_volume is not None and volume_chapters:
                        # Add previous volume to TOC
                        volume = next(
                            (v for v in novel.volumes if v.index == current_volume),
                            None
                        )
                        if volume:
                            toc_items.append((
                                epub.Section(volume.title),
                                volume_chapters
                            ))
                        volume_chapters = []
                    current_volume = chapter.volume_index

                # Create chapter
                epub_chapter = self._create_chapter(chapter, css_item)
                book.add_item(epub_chapter)
                epub_chapters.append(epub_chapter)
                volume_chapters.append(epub_chapter)

            # Handle last volume
            if volume_chapters:
                if current_volume is not None:
                    volume = next(
                        (v for v in novel.volumes if v.index == current_volume),
                        None
                    )
                    if volume:
                        toc_items.append((
                            epub.Section(volume.title),
                            volume_chapters
                        ))
                    else:
                        toc_items.extend(volume_chapters)
                else:
                    toc_items.extend(volume_chapters)

            # Set TOC
            if config.include_toc:
                book.toc = toc_items if toc_items else tuple(epub_chapters)

            # Add navigation files
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # Set spine
            book.spine = ['nav'] + epub_chapters

            # Write EPUB file
            epub.write_epub(str(output_path), book, {})

            return ExportResult.ok(output_path)

        except Exception as e:
            return ExportResult.failure(str(e))

    def _add_cover(self, book: epub.EpubBook, novel: NovelData) -> None:
        """Add cover image to the book."""
        cover_data = None
        cover_ext = "jpg"

        # Try to load cover from file
        if novel.cover_path and novel.cover_path.exists():
            cover_data = novel.cover_path.read_bytes()
            cover_ext = novel.cover_path.suffix.lstrip('.') or "jpg"

        # TODO: Download cover from URL if not available locally

        if cover_data:
            # Add cover image
            book.set_cover(f"cover.{cover_ext}", cover_data)

    def _create_chapter(
        self,
        chapter,
        css_item: epub.EpubItem,
    ) -> epub.EpubHtml:
        """Create an EPUB chapter."""
        filename = f'chapter_{chapter.index:05d}.xhtml'

        epub_chapter = epub.EpubHtml(
            title=chapter.title,
            file_name=filename,
            lang='en'
        )

        # Use HTML content if available, otherwise convert plain text
        if chapter.html_content:
            content = chapter.html_content
        else:
            content = self._text_to_html(chapter.content)

        epub_chapter.content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{self._escape_html(chapter.title)}</title>
    <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
    <h1 class="chapter-title">{self._escape_html(chapter.title)}</h1>
    <div class="chapter-content">
        {content}
    </div>
</body>
</html>'''

        epub_chapter.add_item(css_item)
        return epub_chapter

    def _get_css(self, config: ExportConfig) -> str:
        """Generate CSS for the EPUB."""
        custom_css = config.custom_css or ""

        return f'''
@namespace epub "http://www.idpf.org/2007/ops";

body {{
    font-family: {config.font_family}, Georgia, serif;
    font-size: {config.font_size}pt;
    line-height: 1.6;
    margin: 1em;
    padding: 0;
}}

h1.chapter-title {{
    font-size: 1.5em;
    font-weight: bold;
    text-align: center;
    margin: 1em 0 2em 0;
    padding-bottom: 0.5em;
    border-bottom: 1px solid #ccc;
}}

.chapter-content {{
    text-align: justify;
}}

.chapter-content p {{
    text-indent: 1.5em;
    margin: 0.5em 0;
}}

.chapter-content p:first-child {{
    text-indent: 0;
}}

/* Volume title */
h2.volume-title {{
    font-size: 1.8em;
    text-align: center;
    margin: 2em 0;
    page-break-before: always;
}}

/* Emphasis */
em, i {{
    font-style: italic;
}}

strong, b {{
    font-weight: bold;
}}

/* Links */
a {{
    color: #0066cc;
    text-decoration: none;
}}

a:hover {{
    text-decoration: underline;
}}

{custom_css}
'''
