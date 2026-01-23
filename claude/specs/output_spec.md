# Output System Specification

## Overview

The output system handles conversion of translated novels into various e-book formats. It supports 15+ formats with sensible defaults (EPUB, PDF, TXT), proper metadata and TOC embedding, volume-wise organization, and global/per-job format selection.

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Output System                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐                       │
│  │ ExporterRegistry │    │   OutputConfig   │                       │
│  │ (Plugin System)  │    │  (Settings)      │                       │
│  └────────┬─────────┘    └──────────────────┘                       │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                       Exporters                           │       │
│  ├──────────┬──────────┬──────────┬──────────┬─────────────┤       │
│  │   EPUB   │   PDF    │   TXT    │   DOCX   │    HTML     │       │
│  │(ebooklib)│(weasypr) │ (native) │(python-  │  (native)   │       │
│  │          │          │          │  docx)   │             │       │
│  ├──────────┴──────────┴──────────┴──────────┴─────────────┤       │
│  │   JSON   │    MD    │   RTF    │   MOBI   │   AZW3      │       │
│  │ (native) │ (native) │ (native) │(calibre) │ (calibre)   │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐                       │
│  │  MetadataManager │    │   TOCGenerator   │                       │
│  │  (Cover, Author) │    │  (Multi-level)   │                       │
│  └──────────────────┘    └──────────────────┘                       │
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐                       │
│  │  ChapterStore    │    │  CalibreWrapper  │                       │
│  │  (Interim HTML)  │    │  (ebook-convert) │                       │
│  └──────────────────┘    └──────────────────┘                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Translated Chapters (in memory or HTML files)
        │
        ▼
┌───────────────┐
│ MetadataLoad  │ ─── Load title, author, cover
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  TOC Generate │ ─── Build chapter/volume structure
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Format Select │ ─── Get enabled formats
└───────┬───────┘
        │
        ├──────────────────────────────┐
        ▼                              ▼
┌───────────────┐              ┌───────────────┐
│ Native Export │              │Calibre Convert│
│ (EPUB/PDF/TXT)│              │ (MOBI/AZW3)   │
└───────┬───────┘              └───────┬───────┘
        │                              │
        ▼                              ▼
┌─────────────────────────────────────────────┐
│          Output Directory                    │
│  ~/Documents/lightnovels/{Novel Name}/       │
│  ├── {Novel}.epub                           │
│  ├── {Novel}.pdf                            │
│  ├── {Novel}.txt                            │
│  ├── {Novel}.mobi                           │
│  └── chapters/                              │
│      ├── 001.html                           │
│      └── ...                                │
└─────────────────────────────────────────────┘
```

---

## Core Components

### 1. Exporter Protocol

```python
# Location: sagemtl_crawler/exporters/base.py

from typing import Protocol, List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Flag, auto


class ExporterCapability(Flag):
    """Capabilities of an exporter."""
    COVER = auto()           # Can embed cover image
    TOC = auto()             # Can embed table of contents
    METADATA = auto()        # Can embed metadata (title, author)
    IMAGES = auto()          # Can embed inline images
    STYLING = auto()         # Supports text styling (bold, italic)
    BOOKMARKS = auto()       # Supports navigation bookmarks
    VOLUMES = auto()         # Can separate volumes


@dataclass
class ExportMetadata:
    """Metadata for export."""
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    language: str = "en"
    cover_path: Optional[Path] = None
    cover_data: Optional[bytes] = None
    series: Optional[str] = None
    series_index: Optional[int] = None
    publisher: str = "SageMTL"
    source_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ExportChapter:
    """Chapter for export."""
    title: str
    content: str  # HTML content
    chapter_number: int
    volume_number: Optional[int] = None
    volume_title: Optional[str] = None


@dataclass
class ExportVolume:
    """Volume containing chapters."""
    title: str
    volume_number: int
    chapters: List[ExportChapter]


@dataclass
class ExportJob:
    """Complete export job."""
    metadata: ExportMetadata
    chapters: List[ExportChapter]
    volumes: Optional[List[ExportVolume]] = None
    output_path: Path = None


class Exporter(Protocol):
    """Protocol for format exporters."""

    # Class attributes
    format_name: str                     # e.g., "EPUB"
    file_extension: str                  # e.g., ".epub"
    capabilities: ExporterCapability
    is_native: bool = True               # False if requires external tools

    def export(self, job: ExportJob, output_path: Path) -> Path:
        """Export the job to the specified format."""
        ...

    def can_export(self) -> bool:
        """Check if export is possible (dependencies available)."""
        ...

    def get_default_options(self) -> Dict[str, Any]:
        """Get default export options."""
        ...
```

### 2. Exporter Registry

```python
# Location: sagemtl_crawler/exporters/registry.py

from typing import Dict, Type, List, Optional
from pathlib import Path
import importlib
import pkgutil


class ExporterRegistry:
    """Registry for format exporters."""

    _exporters: Dict[str, Type[Exporter]] = {}

    @classmethod
    def register(cls, exporter_class: Type[Exporter]):
        """Register an exporter."""
        ext = exporter_class.file_extension.lower().lstrip('.')
        cls._exporters[ext] = exporter_class

    @classmethod
    def get_exporter(cls, format_name: str) -> Optional[Exporter]:
        """Get exporter by format name or extension."""
        key = format_name.lower().lstrip('.')
        if key in cls._exporters:
            return cls._exporters[key]()
        return None

    @classmethod
    def list_exporters(cls) -> List[Dict]:
        """List all registered exporters."""
        result = []
        for ext, exporter_class in cls._exporters.items():
            exporter = exporter_class()
            result.append({
                'format': exporter_class.format_name,
                'extension': ext,
                'capabilities': exporter_class.capabilities,
                'is_native': exporter_class.is_native,
                'available': exporter.can_export(),
            })
        return result

    @classmethod
    def discover_exporters(cls):
        """Auto-discover exporters from the exporters package."""
        package = importlib.import_module('sagemtl_crawler.exporters')
        package_dir = Path(package.__file__).parent

        for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
            if module_name.endswith('_exporter'):
                module = importlib.import_module(f'sagemtl_crawler.exporters.{module_name}')
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        hasattr(attr, 'format_name') and
                        hasattr(attr, 'file_extension')):
                        cls.register(attr)
```

### 3. Output Manager

```python
# Location: sagemtl_crawler/exporters/output_manager.py

from typing import List, Dict, Optional, Callable
from pathlib import Path
from dataclasses import dataclass
import asyncio


@dataclass
class OutputConfig:
    """Configuration for output generation."""
    output_directory: Path
    enabled_formats: List[str] = None  # None = all available
    per_volume: bool = False           # Generate separate files per volume
    include_interim: bool = True       # Keep interim chapter files
    cover_generation: bool = True      # Generate cover if missing


class OutputManager:
    """Manages novel export to multiple formats."""

    def __init__(self, config: OutputConfig):
        self.config = config
        ExporterRegistry.discover_exporters()

    def export_novel(
        self,
        job: ExportJob,
        formats: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Path]:
        """Export novel to specified formats.

        Args:
            job: Export job with chapters and metadata
            formats: List of formats to export (None = use config defaults)
            progress_callback: Called with (format, progress) during export

        Returns:
            Dict mapping format name to output file path
        """
        formats = formats or self.config.enabled_formats or ['epub', 'pdf', 'txt']
        results = {}

        # Create output directory
        novel_dir = self.config.output_directory / self._sanitize_name(job.metadata.title)
        novel_dir.mkdir(parents=True, exist_ok=True)
        job.output_path = novel_dir

        # Store interim chapters if enabled
        if self.config.include_interim:
            self._store_interim_chapters(job, novel_dir)

        # Export to each format
        total_formats = len(formats)
        for i, fmt in enumerate(formats):
            exporter = ExporterRegistry.get_exporter(fmt)
            if not exporter:
                continue

            if not exporter.can_export():
                continue

            try:
                output_file = novel_dir / f"{self._sanitize_name(job.metadata.title)}{exporter.file_extension}"

                if self.config.per_volume and job.volumes:
                    # Export each volume separately
                    for volume in job.volumes:
                        volume_job = ExportJob(
                            metadata=job.metadata,
                            chapters=volume.chapters,
                            volumes=[volume],
                        )
                        volume_file = novel_dir / f"{self._sanitize_name(job.metadata.title)} - Volume {volume.volume_number}{exporter.file_extension}"
                        exporter.export(volume_job, volume_file)
                else:
                    # Export entire novel
                    exporter.export(job, output_file)

                results[fmt] = output_file

                if progress_callback:
                    progress_callback(fmt, (i + 1) / total_formats * 100)

            except Exception as e:
                # Log error but continue with other formats
                print(f"Failed to export {fmt}: {e}")

        return results

    def _store_interim_chapters(self, job: ExportJob, output_dir: Path):
        """Store chapters as HTML files for future reference."""
        chapters_dir = output_dir / "chapters"
        chapters_dir.mkdir(exist_ok=True)

        for chapter in job.chapters:
            chapter_file = chapters_dir / f"{chapter.chapter_number:04d}.html"
            html = self._wrap_chapter_html(chapter)
            chapter_file.write_text(html, encoding='utf-8')

    def _wrap_chapter_html(self, chapter: ExportChapter) -> str:
        """Wrap chapter content in full HTML."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{chapter.title}</title>
    <style>
        body {{ font-family: Georgia, serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ font-size: 1.5em; margin-bottom: 1em; }}
        p {{ margin-bottom: 1em; text-indent: 2em; }}
    </style>
</head>
<body>
    <h1>{chapter.title}</h1>
    {chapter.content}
</body>
</html>"""

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize name for filesystem."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()[:200]
```

---

## Native Exporters

### EPUB Exporter

```python
# Location: sagemtl_crawler/exporters/epub_exporter.py

from ebooklib import epub
from pathlib import Path
from typing import Optional
import uuid


class EPUBExporter:
    """Export to EPUB format using ebooklib."""

    format_name = "EPUB"
    file_extension = ".epub"
    capabilities = (
        ExporterCapability.COVER |
        ExporterCapability.TOC |
        ExporterCapability.METADATA |
        ExporterCapability.IMAGES |
        ExporterCapability.STYLING |
        ExporterCapability.VOLUMES
    )
    is_native = True

    def can_export(self) -> bool:
        try:
            import ebooklib
            return True
        except ImportError:
            return False

    def get_default_options(self) -> dict:
        return {
            'epub_version': '3.0',
            'include_cover': True,
            'include_toc': True,
            'css_style': self._default_css(),
        }

    def export(self, job: ExportJob, output_path: Path) -> Path:
        """Export to EPUB."""
        book = epub.EpubBook()

        # Set metadata
        book.set_identifier(str(uuid.uuid4()))
        book.set_title(job.metadata.title)
        book.set_language(job.metadata.language)

        if job.metadata.author:
            book.add_author(job.metadata.author)

        if job.metadata.description:
            book.add_metadata('DC', 'description', job.metadata.description)

        # Add cover
        if job.metadata.cover_path:
            cover_content = job.metadata.cover_path.read_bytes()
            book.set_cover("cover.jpg", cover_content)
        elif job.metadata.cover_data:
            book.set_cover("cover.jpg", job.metadata.cover_data)

        # Add CSS
        css = epub.EpubItem(
            uid="style",
            file_name="style/main.css",
            media_type="text/css",
            content=self._default_css()
        )
        book.add_item(css)

        # Create chapters
        epub_chapters = []
        spine = ['nav']
        toc = []

        if job.volumes:
            # Organize by volume
            for volume in job.volumes:
                volume_items = []
                for chapter in volume.chapters:
                    epub_chapter = self._create_chapter(chapter, css)
                    book.add_item(epub_chapter)
                    epub_chapters.append(epub_chapter)
                    spine.append(epub_chapter)
                    volume_items.append(epub_chapter)

                # Add volume to TOC
                toc.append((
                    epub.Section(volume.title),
                    tuple(volume_items)
                ))
        else:
            # Flat chapter list
            for chapter in job.chapters:
                epub_chapter = self._create_chapter(chapter, css)
                book.add_item(epub_chapter)
                epub_chapters.append(epub_chapter)
                spine.append(epub_chapter)
                toc.append(epub_chapter)

        # Set TOC and spine
        book.toc = toc
        book.spine = spine

        # Add navigation
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Write file
        epub.write_epub(str(output_path), book)
        return output_path

    def _create_chapter(self, chapter: ExportChapter, css: epub.EpubItem) -> epub.EpubHtml:
        """Create EPUB chapter."""
        filename = f"chapter_{chapter.chapter_number:04d}.xhtml"

        epub_chapter = epub.EpubHtml(
            title=chapter.title,
            file_name=filename,
            lang='en'
        )

        content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{chapter.title}</title>
    <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
    <h1>{chapter.title}</h1>
    {chapter.content}
</body>
</html>"""

        epub_chapter.set_content(content)
        epub_chapter.add_item(css)

        return epub_chapter

    def _default_css(self) -> str:
        return """
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.6;
    margin: 5%;
    text-align: justify;
}

h1 {
    font-size: 1.5em;
    font-weight: bold;
    margin-bottom: 1em;
    text-align: center;
}

p {
    margin-bottom: 1em;
    text-indent: 2em;
}

p:first-of-type {
    text-indent: 0;
}

.chapter-title {
    font-size: 1.3em;
    font-weight: bold;
    margin-bottom: 1.5em;
    text-align: center;
}

.volume-title {
    font-size: 1.8em;
    font-weight: bold;
    margin: 2em 0;
    text-align: center;
    page-break-before: always;
}
"""


# Register exporter
ExporterRegistry.register(EPUBExporter)
```

### PDF Exporter

```python
# Location: sagemtl_crawler/exporters/pdf_exporter.py

from pathlib import Path
from typing import Optional


class PDFExporter:
    """Export to PDF format using WeasyPrint."""

    format_name = "PDF"
    file_extension = ".pdf"
    capabilities = (
        ExporterCapability.COVER |
        ExporterCapability.TOC |
        ExporterCapability.METADATA |
        ExporterCapability.IMAGES |
        ExporterCapability.STYLING |
        ExporterCapability.BOOKMARKS |
        ExporterCapability.VOLUMES
    )
    is_native = True

    def can_export(self) -> bool:
        try:
            from weasyprint import HTML, CSS
            return True
        except ImportError:
            return False

    def get_default_options(self) -> dict:
        return {
            'page_size': 'A5',
            'margin': '2cm',
            'font_size': '11pt',
            'include_toc': True,
        }

    def export(self, job: ExportJob, output_path: Path) -> Path:
        """Export to PDF."""
        from weasyprint import HTML, CSS

        # Build HTML document
        html_content = self._build_html(job)

        # Create PDF
        html = HTML(string=html_content)
        css = CSS(string=self._get_css())

        html.write_pdf(str(output_path), stylesheets=[css])

        return output_path

    def _build_html(self, job: ExportJob) -> str:
        """Build complete HTML document for PDF conversion."""
        parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            f'<title>{job.metadata.title}</title>',
            '<meta charset="utf-8">',
            '</head>',
            '<body>',
        ]

        # Cover page
        parts.append(f'''
        <div class="cover-page">
            <h1 class="book-title">{job.metadata.title}</h1>
            {'<p class="book-author">by ' + job.metadata.author + '</p>' if job.metadata.author else ''}
        </div>
        ''')

        # Table of contents
        parts.append('<div class="toc">')
        parts.append('<h2>Table of Contents</h2>')
        parts.append('<ul>')

        if job.volumes:
            for volume in job.volumes:
                parts.append(f'<li class="volume-toc">{volume.title}')
                parts.append('<ul>')
                for chapter in volume.chapters:
                    anchor = f"chapter-{chapter.chapter_number}"
                    parts.append(f'<li><a href="#{anchor}">{chapter.title}</a></li>')
                parts.append('</ul>')
                parts.append('</li>')
        else:
            for chapter in job.chapters:
                anchor = f"chapter-{chapter.chapter_number}"
                parts.append(f'<li><a href="#{anchor}">{chapter.title}</a></li>')

        parts.append('</ul>')
        parts.append('</div>')

        # Chapters
        if job.volumes:
            for volume in job.volumes:
                parts.append(f'<h2 class="volume-title">{volume.title}</h2>')
                for chapter in volume.chapters:
                    parts.append(self._chapter_html(chapter))
        else:
            for chapter in job.chapters:
                parts.append(self._chapter_html(chapter))

        parts.append('</body>')
        parts.append('</html>')

        return '\n'.join(parts)

    def _chapter_html(self, chapter: ExportChapter) -> str:
        """Generate HTML for a chapter."""
        anchor = f"chapter-{chapter.chapter_number}"
        return f'''
        <div class="chapter" id="{anchor}">
            <h3 class="chapter-title">{chapter.title}</h3>
            <div class="chapter-content">
                {chapter.content}
            </div>
        </div>
        '''

    def _get_css(self) -> str:
        """Get CSS for PDF styling."""
        return """
@page {
    size: A5;
    margin: 2cm;

    @bottom-center {
        content: counter(page);
    }
}

body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 11pt;
    line-height: 1.5;
}

.cover-page {
    page-break-after: always;
    text-align: center;
    padding-top: 40%;
}

.book-title {
    font-size: 24pt;
    margin-bottom: 1em;
}

.book-author {
    font-size: 14pt;
    color: #666;
}

.toc {
    page-break-after: always;
}

.toc h2 {
    text-align: center;
    margin-bottom: 1em;
}

.toc ul {
    list-style: none;
    padding-left: 0;
}

.toc li {
    margin-bottom: 0.5em;
}

.toc a {
    text-decoration: none;
    color: inherit;
}

.toc a::after {
    content: target-counter(attr(href), page);
    float: right;
}

.volume-title {
    page-break-before: always;
    text-align: center;
    font-size: 18pt;
    margin-top: 40%;
    margin-bottom: 2em;
}

.chapter {
    page-break-before: always;
}

.chapter-title {
    font-size: 14pt;
    text-align: center;
    margin-bottom: 1.5em;
}

.chapter-content p {
    text-indent: 2em;
    margin-bottom: 0.5em;
}

.chapter-content p:first-of-type {
    text-indent: 0;
}
"""


# Register exporter
ExporterRegistry.register(PDFExporter)
```

### TXT Exporter

```python
# Location: sagemtl_crawler/exporters/txt_exporter.py

from pathlib import Path
from typing import Optional
import re


class TXTExporter:
    """Export to plain text format."""

    format_name = "TXT"
    file_extension = ".txt"
    capabilities = ExporterCapability.VOLUMES
    is_native = True

    def can_export(self) -> bool:
        return True  # Always available

    def get_default_options(self) -> dict:
        return {
            'line_width': 80,
            'chapter_separator': '=' * 60,
            'volume_separator': '#' * 60,
            'encoding': 'utf-8',
            'line_ending': '\n',  # or '\r\n' for Windows
        }

    def export(self, job: ExportJob, output_path: Path) -> Path:
        """Export to plain text."""
        lines = []

        # Title
        lines.append(job.metadata.title)
        if job.metadata.author:
            lines.append(f"by {job.metadata.author}")
        lines.append('')
        lines.append('=' * 60)
        lines.append('')

        # Table of contents
        lines.append("TABLE OF CONTENTS")
        lines.append('-' * 40)

        if job.volumes:
            for volume in job.volumes:
                lines.append(f"\n{volume.title}")
                for chapter in volume.chapters:
                    lines.append(f"  {chapter.chapter_number}. {chapter.title}")
        else:
            for chapter in job.chapters:
                lines.append(f"{chapter.chapter_number}. {chapter.title}")

        lines.append('')
        lines.append('=' * 60)
        lines.append('')

        # Chapters
        if job.volumes:
            for volume in job.volumes:
                lines.append('#' * 60)
                lines.append(volume.title.upper())
                lines.append('#' * 60)
                lines.append('')

                for chapter in volume.chapters:
                    lines.extend(self._format_chapter(chapter))
        else:
            for chapter in job.chapters:
                lines.extend(self._format_chapter(chapter))

        # Write file
        content = '\n'.join(lines)
        output_path.write_text(content, encoding='utf-8')

        return output_path

    def _format_chapter(self, chapter: ExportChapter) -> list:
        """Format a chapter as plain text lines."""
        lines = []
        lines.append('=' * 60)
        lines.append(f"Chapter {chapter.chapter_number}: {chapter.title}")
        lines.append('=' * 60)
        lines.append('')

        # Strip HTML and convert to plain text
        text = self._html_to_text(chapter.content)
        lines.append(text)
        lines.append('')
        lines.append('')

        return lines

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # Replace <br> and </p> with newlines
        for br in soup.find_all('br'):
            br.replace_with('\n')
        for p in soup.find_all('p'):
            p.append('\n\n')

        # Get text
        text = soup.get_text()

        # Clean up
        text = re.sub(r'\n{3,}', '\n\n', text)  # Collapse multiple newlines
        text = re.sub(r'[ \t]+', ' ', text)     # Collapse spaces
        text = text.strip()

        return text


# Register exporter
ExporterRegistry.register(TXTExporter)
```

### HTML Exporter

```python
# Location: sagemtl_crawler/exporters/html_exporter.py

from pathlib import Path


class HTMLExporter:
    """Export to single HTML file."""

    format_name = "HTML"
    file_extension = ".html"
    capabilities = (
        ExporterCapability.COVER |
        ExporterCapability.TOC |
        ExporterCapability.METADATA |
        ExporterCapability.IMAGES |
        ExporterCapability.STYLING |
        ExporterCapability.VOLUMES
    )
    is_native = True

    def can_export(self) -> bool:
        return True

    def get_default_options(self) -> dict:
        return {
            'inline_css': True,
            'include_nav': True,
        }

    def export(self, job: ExportJob, output_path: Path) -> Path:
        """Export to single HTML file."""
        html = self._build_html(job)
        output_path.write_text(html, encoding='utf-8')
        return output_path

    def _build_html(self, job: ExportJob) -> str:
        """Build complete HTML document."""
        parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            f'<title>{job.metadata.title}</title>',
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f'<meta name="author" content="{job.metadata.author or ""}">',
            '<style>',
            self._get_css(),
            '</style>',
            '</head>',
            '<body>',
        ]

        # Navigation
        parts.append('<nav class="sidebar">')
        parts.append('<h3>Contents</h3>')
        parts.append('<ul>')

        if job.volumes:
            for volume in job.volumes:
                parts.append(f'<li class="volume">{volume.title}')
                parts.append('<ul>')
                for chapter in volume.chapters:
                    anchor = f"ch{chapter.chapter_number}"
                    parts.append(f'<li><a href="#{anchor}">{chapter.title}</a></li>')
                parts.append('</ul></li>')
        else:
            for chapter in job.chapters:
                anchor = f"ch{chapter.chapter_number}"
                parts.append(f'<li><a href="#{anchor}">{chapter.title}</a></li>')

        parts.append('</ul>')
        parts.append('</nav>')

        # Main content
        parts.append('<main>')
        parts.append(f'<h1>{job.metadata.title}</h1>')

        if job.volumes:
            for volume in job.volumes:
                parts.append(f'<h2 class="volume-title">{volume.title}</h2>')
                for chapter in volume.chapters:
                    parts.append(self._chapter_html(chapter))
        else:
            for chapter in job.chapters:
                parts.append(self._chapter_html(chapter))

        parts.append('</main>')
        parts.append('</body>')
        parts.append('</html>')

        return '\n'.join(parts)

    def _chapter_html(self, chapter: ExportChapter) -> str:
        anchor = f"ch{chapter.chapter_number}"
        return f'''
<article class="chapter" id="{anchor}">
    <h3>{chapter.title}</h3>
    {chapter.content}
</article>
'''

    def _get_css(self) -> str:
        return """
* { box-sizing: border-box; }

body {
    font-family: Georgia, serif;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    display: flex;
}

.sidebar {
    width: 280px;
    height: 100vh;
    position: fixed;
    overflow-y: auto;
    padding: 20px;
    background: #f5f5f5;
    border-right: 1px solid #ddd;
}

.sidebar h3 {
    margin-top: 0;
}

.sidebar ul {
    list-style: none;
    padding-left: 0;
}

.sidebar li {
    margin-bottom: 4px;
}

.sidebar a {
    color: #333;
    text-decoration: none;
}

.sidebar a:hover {
    color: #0066cc;
}

main {
    margin-left: 280px;
    max-width: 800px;
    padding: 40px;
}

h1 { font-size: 2em; margin-bottom: 1em; }
h2 { font-size: 1.5em; margin-top: 2em; }
h3 { font-size: 1.2em; margin-bottom: 1em; }

.chapter {
    margin-bottom: 3em;
    padding-bottom: 2em;
    border-bottom: 1px solid #eee;
}

p {
    margin-bottom: 1em;
    text-indent: 2em;
}

@media (max-width: 900px) {
    .sidebar { display: none; }
    main { margin-left: 0; }
}
"""


# Register exporter
ExporterRegistry.register(HTMLExporter)
```

### DOCX Exporter

```python
# Location: sagemtl_crawler/exporters/docx_exporter.py

from pathlib import Path


class DOCXExporter:
    """Export to Microsoft Word format."""

    format_name = "DOCX"
    file_extension = ".docx"
    capabilities = (
        ExporterCapability.TOC |
        ExporterCapability.METADATA |
        ExporterCapability.STYLING |
        ExporterCapability.VOLUMES
    )
    is_native = True

    def can_export(self) -> bool:
        try:
            from docx import Document
            return True
        except ImportError:
            return False

    def get_default_options(self) -> dict:
        return {
            'font_name': 'Times New Roman',
            'font_size': 12,
            'include_toc': True,
        }

    def export(self, job: ExportJob, output_path: Path) -> Path:
        """Export to DOCX."""
        from docx import Document
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Set default font
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(12)

        # Title page
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run(job.metadata.title)
        run.bold = True
        run.font.size = Pt(24)

        if job.metadata.author:
            author_para = doc.add_paragraph()
            author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            author_para.add_run(f"by {job.metadata.author}")

        doc.add_page_break()

        # Table of contents placeholder
        doc.add_heading("Table of Contents", level=1)
        if job.volumes:
            for volume in job.volumes:
                doc.add_paragraph(volume.title, style='TOC Heading')
                for chapter in volume.chapters:
                    doc.add_paragraph(f"    {chapter.title}", style='TOC 1')
        else:
            for chapter in job.chapters:
                doc.add_paragraph(chapter.title, style='TOC 1')

        doc.add_page_break()

        # Chapters
        if job.volumes:
            for volume in job.volumes:
                doc.add_heading(volume.title, level=1)
                for chapter in volume.chapters:
                    self._add_chapter(doc, chapter)
        else:
            for chapter in job.chapters:
                self._add_chapter(doc, chapter)

        # Save
        doc.save(str(output_path))
        return output_path

    def _add_chapter(self, doc, chapter: ExportChapter):
        """Add a chapter to the document."""
        from bs4 import BeautifulSoup

        doc.add_heading(chapter.title, level=2)

        # Parse HTML content
        soup = BeautifulSoup(chapter.content, 'html.parser')

        for element in soup.find_all(['p', 'br']):
            if element.name == 'p':
                text = element.get_text().strip()
                if text:
                    doc.add_paragraph(text)
            elif element.name == 'br':
                doc.add_paragraph()


# Register exporter
ExporterRegistry.register(DOCXExporter)
```

### JSON Exporter

```python
# Location: sagemtl_crawler/exporters/json_exporter.py

from pathlib import Path
import json
from bs4 import BeautifulSoup


class JSONExporter:
    """Export to structured JSON format."""

    format_name = "JSON"
    file_extension = ".json"
    capabilities = (
        ExporterCapability.METADATA |
        ExporterCapability.VOLUMES
    )
    is_native = True

    def can_export(self) -> bool:
        return True

    def get_default_options(self) -> dict:
        return {
            'include_html': False,  # Include raw HTML content
            'indent': 2,
        }

    def export(self, job: ExportJob, output_path: Path) -> Path:
        """Export to JSON."""
        data = {
            'metadata': {
                'title': job.metadata.title,
                'author': job.metadata.author,
                'description': job.metadata.description,
                'language': job.metadata.language,
                'source_url': job.metadata.source_url,
                'tags': job.metadata.tags,
            },
            'statistics': {
                'total_chapters': len(job.chapters),
                'total_volumes': len(job.volumes) if job.volumes else 0,
            }
        }

        if job.volumes:
            data['volumes'] = [
                {
                    'title': v.title,
                    'volume_number': v.volume_number,
                    'chapters': [
                        self._chapter_to_dict(c)
                        for c in v.chapters
                    ]
                }
                for v in job.volumes
            ]
        else:
            data['chapters'] = [
                self._chapter_to_dict(c)
                for c in job.chapters
            ]

        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        return output_path

    def _chapter_to_dict(self, chapter: ExportChapter) -> dict:
        """Convert chapter to dictionary."""
        soup = BeautifulSoup(chapter.content, 'html.parser')
        text = soup.get_text().strip()

        return {
            'chapter_number': chapter.chapter_number,
            'title': chapter.title,
            'content': text,
            'word_count': len(text.split()),
        }


# Register exporter
ExporterRegistry.register(JSONExporter)
```

### Markdown Exporter

```python
# Location: sagemtl_crawler/exporters/markdown_exporter.py

from pathlib import Path
import re


class MarkdownExporter:
    """Export to Markdown format."""

    format_name = "Markdown"
    file_extension = ".md"
    capabilities = (
        ExporterCapability.TOC |
        ExporterCapability.STYLING |
        ExporterCapability.VOLUMES
    )
    is_native = True

    def can_export(self) -> bool:
        return True

    def get_default_options(self) -> dict:
        return {
            'flavor': 'gfm',  # GitHub Flavored Markdown
            'include_toc': True,
        }

    def export(self, job: ExportJob, output_path: Path) -> Path:
        """Export to Markdown."""
        lines = []

        # Title
        lines.append(f"# {job.metadata.title}")
        if job.metadata.author:
            lines.append(f"\n*by {job.metadata.author}*")
        lines.append('\n---\n')

        # Table of contents
        lines.append("## Table of Contents\n")
        if job.volumes:
            for volume in job.volumes:
                lines.append(f"### {volume.title}")
                for chapter in volume.chapters:
                    anchor = self._make_anchor(chapter.title)
                    lines.append(f"- [{chapter.title}](#{anchor})")
                lines.append('')
        else:
            for chapter in job.chapters:
                anchor = self._make_anchor(chapter.title)
                lines.append(f"- [{chapter.title}](#{anchor})")

        lines.append('\n---\n')

        # Chapters
        if job.volumes:
            for volume in job.volumes:
                lines.append(f"\n# {volume.title}\n")
                for chapter in volume.chapters:
                    lines.extend(self._format_chapter(chapter))
        else:
            for chapter in job.chapters:
                lines.extend(self._format_chapter(chapter))

        content = '\n'.join(lines)
        output_path.write_text(content, encoding='utf-8')

        return output_path

    def _format_chapter(self, chapter: ExportChapter) -> list:
        """Format chapter as Markdown."""
        lines = []
        lines.append(f"\n## {chapter.title}\n")

        # Convert HTML to Markdown
        text = self._html_to_markdown(chapter.content)
        lines.append(text)

        return lines

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to Markdown."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # Convert tags
        for tag in soup.find_all('strong'):
            tag.replace_with(f"**{tag.get_text()}**")

        for tag in soup.find_all('em'):
            tag.replace_with(f"*{tag.get_text()}*")

        for tag in soup.find_all('br'):
            tag.replace_with('\n')

        # Get text and clean up
        text = soup.get_text()
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _make_anchor(self, text: str) -> str:
        """Create markdown anchor from text."""
        anchor = text.lower()
        anchor = re.sub(r'[^\w\s-]', '', anchor)
        anchor = re.sub(r'\s+', '-', anchor)
        return anchor


# Register exporter
ExporterRegistry.register(MarkdownExporter)
```

---

## Calibre Integration

```python
# Location: sagemtl_crawler/exporters/calibre_wrapper.py

import subprocess
import shutil
from pathlib import Path
from typing import Optional, List
import tempfile


class CalibreWrapper:
    """Wrapper for Calibre's ebook-convert tool."""

    SUPPORTED_OUTPUTS = ['mobi', 'azw3', 'fb2', 'lrf', 'lit', 'pdb', 'snb']

    def __init__(self):
        self._calibre_path = self._find_calibre()

    def _find_calibre(self) -> Optional[Path]:
        """Find Calibre's ebook-convert executable."""
        # Check if in PATH
        ebook_convert = shutil.which('ebook-convert')
        if ebook_convert:
            return Path(ebook_convert)

        # Common installation paths
        common_paths = [
            Path(r"C:\Program Files\Calibre2\ebook-convert.exe"),
            Path(r"C:\Program Files (x86)\Calibre2\ebook-convert.exe"),
            Path("/Applications/calibre.app/Contents/MacOS/ebook-convert"),
            Path("/usr/bin/ebook-convert"),
            Path.home() / ".local/bin/ebook-convert",
        ]

        for path in common_paths:
            if path.exists():
                return path

        return None

    def is_available(self) -> bool:
        """Check if Calibre is available."""
        return self._calibre_path is not None

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        options: Optional[dict] = None
    ) -> Path:
        """Convert ebook using Calibre.

        Args:
            input_path: Path to source ebook (usually EPUB)
            output_path: Path to output file
            options: Additional Calibre options

        Returns:
            Path to converted file
        """
        if not self.is_available():
            raise RuntimeError("Calibre not found")

        cmd = [str(self._calibre_path), str(input_path), str(output_path)]

        if options:
            for key, value in options.items():
                if value is True:
                    cmd.append(f"--{key}")
                elif value is not False and value is not None:
                    cmd.append(f"--{key}={value}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Calibre conversion failed: {result.stderr}")

        return output_path

    def get_supported_formats(self) -> List[str]:
        """Get list of formats Calibre can produce."""
        if not self.is_available():
            return []
        return self.SUPPORTED_OUTPUTS


class MOBIExporter:
    """Export to MOBI format via Calibre."""

    format_name = "MOBI"
    file_extension = ".mobi"
    capabilities = (
        ExporterCapability.COVER |
        ExporterCapability.TOC |
        ExporterCapability.METADATA
    )
    is_native = False  # Requires Calibre

    def __init__(self):
        self._calibre = CalibreWrapper()

    def can_export(self) -> bool:
        return self._calibre.is_available()

    def get_default_options(self) -> dict:
        return {
            'no_inline_toc': True,
        }

    def export(self, job: ExportJob, output_path: Path) -> Path:
        """Export to MOBI via EPUB intermediate."""
        # First create EPUB
        epub_exporter = ExporterRegistry.get_exporter('epub')

        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = Path(tmpdir) / "temp.epub"
            epub_exporter.export(job, epub_path)

            # Convert to MOBI
            self._calibre.convert(epub_path, output_path)

        return output_path


class AZW3Exporter:
    """Export to AZW3 (Kindle Format 8) via Calibre."""

    format_name = "AZW3"
    file_extension = ".azw3"
    capabilities = (
        ExporterCapability.COVER |
        ExporterCapability.TOC |
        ExporterCapability.METADATA
    )
    is_native = False

    def __init__(self):
        self._calibre = CalibreWrapper()

    def can_export(self) -> bool:
        return self._calibre.is_available()

    def get_default_options(self) -> dict:
        return {}

    def export(self, job: ExportJob, output_path: Path) -> Path:
        """Export to AZW3 via EPUB intermediate."""
        epub_exporter = ExporterRegistry.get_exporter('epub')

        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = Path(tmpdir) / "temp.epub"
            epub_exporter.export(job, epub_path)
            self._calibre.convert(epub_path, output_path)

        return output_path


# Register exporters
ExporterRegistry.register(MOBIExporter)
ExporterRegistry.register(AZW3Exporter)
```

---

## Cover Image Handling

```python
# Location: sagemtl_crawler/exporters/cover_generator.py

from pathlib import Path
from typing import Optional
import io


class CoverGenerator:
    """Generate placeholder covers for novels."""

    def __init__(self):
        pass

    def generate_cover(
        self,
        title: str,
        author: Optional[str] = None,
        width: int = 600,
        height: int = 900,
    ) -> bytes:
        """Generate a simple cover image.

        Args:
            title: Novel title
            author: Author name (optional)
            width: Image width
            height: Image height

        Returns:
            PNG image bytes
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            # Fall back to a minimal implementation
            return self._generate_minimal_cover(title, author, width, height)

        # Create image
        img = Image.new('RGB', (width, height), color='#2D3748')
        draw = ImageDraw.Draw(img)

        # Try to use a nice font, fall back to default
        try:
            title_font = ImageFont.truetype("arial.ttf", 48)
            author_font = ImageFont.truetype("arial.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            author_font = title_font

        # Draw title
        title_lines = self._wrap_text(title, title_font, width - 100)
        y = height // 3

        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y), line, fill='white', font=title_font)
            y += bbox[3] - bbox[1] + 10

        # Draw author
        if author:
            y += 40
            bbox = draw.textbbox((0, 0), author, font=author_font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y), f"by {author}", fill='#A0AEC0', font=author_font)

        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def _wrap_text(self, text: str, font, max_width: int) -> list:
        """Wrap text to fit within width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            line = ' '.join(current_line)
            # Simple width estimation
            if len(line) * 20 > max_width:  # Rough estimate
                current_line.pop()
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def _generate_minimal_cover(
        self,
        title: str,
        author: Optional[str],
        width: int,
        height: int
    ) -> bytes:
        """Generate minimal SVG cover as fallback."""
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#2D3748"/>
    <text x="50%" y="40%" font-family="Arial, sans-serif" font-size="24"
          fill="white" text-anchor="middle">{title[:40]}</text>
    {'<text x="50%" y="55%" font-family="Arial" font-size="16" fill="#A0AEC0" text-anchor="middle">by ' + author + '</text>' if author else ''}
</svg>'''

        return svg.encode('utf-8')
```

---

## Configuration

```toml
# config.toml - Output section

[output]
# Default output directory
output_directory = "~/Documents/lightnovels"

# Default formats to generate
default_formats = ["epub", "pdf", "txt"]

# Per-volume export (generate separate files per volume)
per_volume = false

# Keep interim chapter HTML files
keep_interim = true

# Generate cover if missing
auto_cover = true

[output.epub]
epub_version = "3.0"
include_toc = true

[output.pdf]
page_size = "A5"
margin = "2cm"
font_size = "11pt"
include_toc = true

[output.txt]
line_width = 80
encoding = "utf-8"

[output.calibre]
# Path to Calibre (auto-detected if not specified)
# calibre_path = "C:/Program Files/Calibre2/ebook-convert.exe"
```

---

## Testing

```python
# Location: tests/test_exporters.py

import pytest
from pathlib import Path
from sagemtl_crawler.exporters import (
    ExporterRegistry, OutputManager, OutputConfig,
    ExportJob, ExportMetadata, ExportChapter
)


@pytest.fixture
def sample_job():
    return ExportJob(
        metadata=ExportMetadata(
            title="Test Novel",
            author="Test Author",
        ),
        chapters=[
            ExportChapter(
                title="Chapter 1",
                content="<p>This is the first chapter.</p>",
                chapter_number=1,
            ),
            ExportChapter(
                title="Chapter 2",
                content="<p>This is the second chapter.</p>",
                chapter_number=2,
            ),
        ]
    )


def test_epub_export(sample_job, tmp_path):
    """Test EPUB export."""
    ExporterRegistry.discover_exporters()
    exporter = ExporterRegistry.get_exporter('epub')

    output_path = tmp_path / "test.epub"
    result = exporter.export(sample_job, output_path)

    assert result.exists()
    assert result.suffix == '.epub'


def test_pdf_export(sample_job, tmp_path):
    """Test PDF export."""
    ExporterRegistry.discover_exporters()
    exporter = ExporterRegistry.get_exporter('pdf')

    if not exporter.can_export():
        pytest.skip("WeasyPrint not available")

    output_path = tmp_path / "test.pdf"
    result = exporter.export(sample_job, output_path)

    assert result.exists()


def test_txt_export(sample_job, tmp_path):
    """Test TXT export."""
    ExporterRegistry.discover_exporters()
    exporter = ExporterRegistry.get_exporter('txt')

    output_path = tmp_path / "test.txt"
    result = exporter.export(sample_job, output_path)

    assert result.exists()
    content = result.read_text()
    assert "Test Novel" in content
    assert "Chapter 1" in content


def test_output_manager(sample_job, tmp_path):
    """Test OutputManager multi-format export."""
    config = OutputConfig(
        output_directory=tmp_path,
        enabled_formats=['txt', 'epub'],
    )

    manager = OutputManager(config)
    results = manager.export_novel(sample_job)

    assert 'txt' in results
    assert 'epub' in results
    assert results['txt'].exists()
    assert results['epub'].exists()


def test_calibre_integration(sample_job, tmp_path):
    """Test Calibre-based export (MOBI)."""
    ExporterRegistry.discover_exporters()
    exporter = ExporterRegistry.get_exporter('mobi')

    if not exporter or not exporter.can_export():
        pytest.skip("Calibre not available")

    output_path = tmp_path / "test.mobi"
    result = exporter.export(sample_job, output_path)

    assert result.exists()
```
