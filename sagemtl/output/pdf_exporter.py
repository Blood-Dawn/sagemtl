"""PDF exporter for SageMTL."""

from __future__ import annotations

from typing import List

from .base import (
    BaseExporter,
    ExportCapability,
    ExportConfig,
    ExportResult,
    NovelData,
)

try:
    from weasyprint import HTML, CSS
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False


class PdfExporter(BaseExporter):
    """Export novel to PDF format.

    Features:
    - Full metadata support
    - Cover page
    - Table of contents with bookmarks
    - Custom styling
    - Page numbers
    """

    @classmethod
    def name(cls) -> str:
        return "PDF"

    @classmethod
    def extensions(cls) -> List[str]:
        return ["pdf"]

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
        return HAS_WEASYPRINT

    def export(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> ExportResult:
        """Export novel to PDF file."""
        if not HAS_WEASYPRINT:
            return ExportResult.failure(
                "weasyprint is required for PDF export. "
                "Install with: pip install weasyprint"
            )

        output_path = self._get_output_path(novel, config)

        try:
            # Generate HTML content
            html_content = self._generate_html(novel, config)

            # Generate CSS
            css_content = self._get_css(config)

            # Create PDF
            html = HTML(string=html_content)
            css = CSS(string=css_content)
            html.write_pdf(str(output_path), stylesheets=[css])

            return ExportResult.ok(output_path)

        except Exception as e:
            return ExportResult.failure(str(e))

    def _generate_html(self, novel: NovelData, config: ExportConfig) -> str:
        """Generate HTML content for PDF."""
        sections = []

        # Cover page
        if config.include_cover:
            cover_html = self._generate_cover(novel, config)
            sections.append(cover_html)

        # Table of contents
        if config.include_toc:
            toc_html = self._generate_toc(novel)
            sections.append(toc_html)

        # Chapters
        current_volume = None
        for chapter in novel.chapters:
            # Volume page
            if chapter.volume_index is not None and chapter.volume_index != current_volume:
                current_volume = chapter.volume_index
                volume = next(
                    (v for v in novel.volumes if v.index == current_volume),
                    None
                )
                if volume:
                    sections.append(f'''
                        <div class="volume-page">
                            <h2 class="volume-title">{self._escape_html(volume.title)}</h2>
                        </div>
                    ''')

            # Chapter
            content = chapter.html_content or self._text_to_html(chapter.content)
            sections.append(f'''
                <div class="chapter" id="chapter-{chapter.index}">
                    <h3 class="chapter-title">{self._escape_html(chapter.title)}</h3>
                    <div class="chapter-content">
                        {content}
                    </div>
                </div>
            ''')

        body = '\n'.join(sections)

        return f'''<!DOCTYPE html>
<html lang="{config.language}">
<head>
    <meta charset="utf-8">
    <title>{self._escape_html(config.title or novel.title)}</title>
</head>
<body>
    {body}
</body>
</html>'''

    def _generate_cover(self, novel: NovelData, config: ExportConfig) -> str:
        """Generate cover page HTML."""
        title = config.title or novel.title
        author = config.author or novel.author

        cover_img = ""
        if novel.cover_path and novel.cover_path.exists():
            cover_img = f'<img src="file://{novel.cover_path}" class="cover-image" alt="Cover"/>'

        return f'''
            <div class="cover-page">
                {cover_img}
                <h1 class="book-title">{self._escape_html(title)}</h1>
                {f'<p class="book-author">by {self._escape_html(author)}</p>' if author else ''}
                {f'<p class="book-description">{self._escape_html(novel.description)}</p>' if novel.description else ''}
            </div>
        '''

    def _generate_toc(self, novel: NovelData) -> str:
        """Generate table of contents HTML."""
        items = []
        current_volume = None

        for chapter in novel.chapters:
            # Volume header
            if chapter.volume_index is not None and chapter.volume_index != current_volume:
                current_volume = chapter.volume_index
                volume = next(
                    (v for v in novel.volumes if v.index == current_volume),
                    None
                )
                if volume:
                    items.append(f'<li class="toc-volume">{self._escape_html(volume.title)}</li>')

            items.append(
                f'<li class="toc-chapter">'
                f'<a href="#chapter-{chapter.index}">{self._escape_html(chapter.title)}</a>'
                f'</li>'
            )

        return f'''
            <div class="toc-page">
                <h2 class="toc-title">Table of Contents</h2>
                <ul class="toc-list">
                    {''.join(items)}
                </ul>
            </div>
        '''

    def _get_css(self, config: ExportConfig) -> str:
        """Generate CSS for PDF."""
        custom_css = config.custom_css or ""

        return f'''
@page {{
    size: A5;
    margin: 2cm;
    @bottom-center {{
        content: counter(page);
        font-size: 10pt;
    }}
}}

body {{
    font-family: {config.font_family}, Georgia, serif;
    font-size: {config.font_size}pt;
    line-height: 1.6;
}}

/* Cover page */
.cover-page {{
    page-break-after: always;
    text-align: center;
    padding-top: 20%;
}}

.cover-image {{
    max-width: 80%;
    max-height: 50%;
    margin-bottom: 2em;
}}

.book-title {{
    font-size: 24pt;
    font-weight: bold;
    margin-bottom: 0.5em;
}}

.book-author {{
    font-size: 14pt;
    font-style: italic;
    margin-bottom: 2em;
}}

.book-description {{
    font-size: 11pt;
    max-width: 80%;
    margin: 0 auto;
    text-align: justify;
}}

/* Table of contents */
.toc-page {{
    page-break-after: always;
}}

.toc-title {{
    font-size: 18pt;
    text-align: center;
    margin-bottom: 1em;
}}

.toc-list {{
    list-style: none;
    padding: 0;
}}

.toc-list li {{
    margin: 0.3em 0;
}}

.toc-list a {{
    text-decoration: none;
    color: black;
}}

.toc-volume {{
    font-weight: bold;
    margin-top: 1em;
}}

.toc-chapter {{
    padding-left: 1em;
}}

/* Volume page */
.volume-page {{
    page-break-before: always;
    page-break-after: always;
    text-align: center;
    padding-top: 40%;
}}

.volume-title {{
    font-size: 20pt;
    font-weight: bold;
}}

/* Chapter */
.chapter {{
    page-break-before: always;
}}

.chapter-title {{
    font-size: 16pt;
    font-weight: bold;
    text-align: center;
    margin-bottom: 1em;
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

{custom_css}
'''
