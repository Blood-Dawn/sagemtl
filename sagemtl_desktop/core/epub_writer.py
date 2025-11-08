"""
EPUB writer for exporting translated novels.
"""

from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
import html
import re


class EPUBWriter:
    """Create EPUB files from translated text"""

    def __init__(self):
        self._epub_available = False
        self._check_ebooklib()

    def _check_ebooklib(self):
        """Check if ebooklib is available"""
        try:
            import ebooklib
            self._epub_available = True
        except ImportError:
            print("Warning: ebooklib not installed. EPUB export will not work.")
            print("Install with: pip install ebooklib")

    def is_available(self) -> bool:
        """Check if EPUB export is available"""
        return self._epub_available

    def create_epub(
        self,
        title: str,
        chapters: List[Tuple[str, str]],  # (chapter_title, chapter_text)
        output_path: str,
        author: str = "Unknown",
        language: str = "en",
        cover_path: Optional[str] = None
    ) -> str:
        """
        Create an EPUB file from chapters.

        Args:
            title: Book title
            chapters: List of (chapter_title, chapter_text) tuples
            output_path: Output directory
            author: Author name
            language: Language code
            cover_path: Optional path to cover image

        Returns:
            Path to created EPUB file

        Raises:
            RuntimeError: If ebooklib is not available
            ValueError: If chapters is empty or invalid
        """
        if not self._epub_available:
            raise RuntimeError(
                "ebooklib is not installed. "
                "Install with: pip install ebooklib"
            )

        if not chapters:
            raise ValueError("Cannot create EPUB with no chapters")

        from ebooklib import epub

        # Create book
        book = epub.EpubBook()

        # Set metadata
        book.set_identifier(f"sagemtl-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        book.set_title(title or "Untitled Novel")
        book.set_language(language)
        book.add_author(author)

        # Add cover if provided
        if cover_path and Path(cover_path).exists():
            try:
                with open(cover_path, 'rb') as f:
                    cover_data = f.read()
                book.set_cover('cover.jpg', cover_data)
            except Exception as e:
                print(f"Warning: Failed to add cover: {e}")

        # Add chapters
        epub_chapters = []
        toc = []

        for i, (chapter_title, chapter_text) in enumerate(chapters, 1):
            # Skip empty chapters
            if not chapter_text or not chapter_text.strip():
                print(f"Warning: Skipping empty chapter {i}: {chapter_title}")
                continue

            # Sanitize chapter title
            safe_title = chapter_title or f"Chapter {i}"
            safe_title = self._sanitize_text(safe_title)

            # Sanitize and format chapter content
            safe_content = self._sanitize_html(chapter_text)

            # Create chapter
            chapter = epub.EpubHtml(
                title=safe_title,
                file_name=f'chapter_{i:04d}.xhtml',
                lang=language
            )

            # Set chapter content with basic HTML structure
            chapter.content = f'''
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{safe_title}</title>
    <meta charset="UTF-8"/>
</head>
<body>
    <h1>{safe_title}</h1>
    {safe_content}
</body>
</html>
            '''.strip()

            book.add_item(chapter)
            epub_chapters.append(chapter)
            toc.append(epub.Link(f'chapter_{i:04d}.xhtml', safe_title, f'chapter_{i}'))

        if not epub_chapters:
            raise ValueError("All chapters were empty or invalid")

        # Define Table of Contents
        book.toc = toc

        # Add default NCX and Nav files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Define CSS style (optional)
        style = '''
body {
    font-family: Georgia, serif;
    line-height: 1.6;
    margin: 1em;
}
h1 {
    text-align: center;
    margin: 1em 0;
    font-size: 1.5em;
}
p {
    text-indent: 1.5em;
    margin: 0.5em 0;
}
        '''
        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style
        )
        book.add_item(nav_css)

        # Define spine (reading order)
        book.spine = ['nav'] + epub_chapters

        # Ensure output directory exists
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate safe filename
        safe_filename = self._sanitize_filename(title or "untitled")
        epub_file = output_dir / f"{safe_filename}.epub"

        # Handle existing file
        counter = 1
        while epub_file.exists():
            epub_file = output_dir / f"{safe_filename}_{counter}.epub"
            counter += 1

        # Write EPUB
        epub.write_epub(str(epub_file), book, {})

        return str(epub_file)

    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text for safe use in EPUB.

        Args:
            text: Input text

        Returns:
            Sanitized text
        """
        # HTML escape
        text = html.escape(text)
        # Remove control characters except newlines
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        return text.strip()

    def _sanitize_html(self, text: str) -> str:
        """
        Sanitize HTML content for EPUB chapters.
        Converts plain text to paragraphs and escapes HTML entities.

        Args:
            text: Input text

        Returns:
            Sanitized HTML
        """
        # Escape HTML entities
        text = html.escape(text)

        # Split into paragraphs (by double newlines)
        paragraphs = text.split('\n\n')

        # Wrap each paragraph in <p> tags
        html_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para:
                # Replace single newlines within paragraphs with <br/>
                para = para.replace('\n', '<br/>\n')
                html_paragraphs.append(f'<p>{para}</p>')

        return '\n'.join(html_paragraphs)

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe filesystem use.

        Args:
            filename: Input filename

        Returns:
            Safe filename
        """
        # Remove invalid characters
        safe = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace spaces with underscores
        safe = safe.replace(' ', '_')
        # Limit length
        safe = safe[:100]
        # Ensure not empty
        if not safe:
            safe = "untitled"
        return safe
