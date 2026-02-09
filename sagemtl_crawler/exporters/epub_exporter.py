"""EPUB exporter for novel data"""

from pathlib import Path
from typing import List
from datetime import datetime
import html

try:
    from ebooklib import epub
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False

from ..core.models import NovelTOC, ChapterContent


class EPUBExporter:
    """Export novel to EPUB format"""

    @staticmethod
    def export(
        toc: NovelTOC,
        chapters: List[ChapterContent],
        output_path: Path
    ):
        """
        Export novel to EPUB file.

        Args:
            toc: Novel table of contents
            chapters: List of downloaded chapters
            output_path: Path to output EPUB file

        Raises:
            ImportError: If ebooklib is not installed
        """
        if not HAS_EBOOKLIB:
            raise ImportError(
                "ebooklib is required for EPUB export. "
                "Install with: pip install ebooklib"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create book
        book = epub.EpubBook()

        # Set metadata
        book.set_identifier(f"sagemtl-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        book.set_title(toc.title)
        book.set_language('en')
        book.add_author(toc.author)

        # Add cover if available
        # TODO: Download and add cover image

        # Create chapters
        epub_chapters = []
        for chapter in chapters:
            filename = f'chapter_{chapter.ref.index:05d}.xhtml'

            # Create chapter
            c = epub.EpubHtml(
                title=chapter.ref.title,
                file_name=filename,
                lang='en'
            )

            # Set content (use HTML if available, otherwise plain text)
            content_html = chapter.html if chapter.html else chapter.text.replace('\n', '<br/>\n')

            # Escape HTML entities
            content_html = html.unescape(content_html)

            c.content = f'''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{html.escape(chapter.ref.title)}</title>
</head>
<body>
    <h1>{html.escape(chapter.ref.title)}</h1>
    {content_html}
</body>
</html>'''

            book.add_item(c)
            epub_chapters.append(c)

        # Define Table Of Contents
        book.toc = tuple(epub_chapters)

        # Add default NCX and Nav files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Define CSS style (optional)
        style = '''
        @namespace epub "http://www.idpf.org/2007/ops";
        body {
            font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
        }
        h1 {
            text-align: center;
            text-transform: uppercase;
            font-weight: 200;
        }
        '''
        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style
        )
        book.add_item(nav_css)

        # Create spine
        book.spine = ['nav'] + epub_chapters

        # Write EPUB file
        epub.write_epub(str(output_path), book, {})
