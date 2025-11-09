"""
Tests for EPUB writer module.
"""

import pytest
from pathlib import Path
from sagemtl_desktop.core.epub_writer import EPUBWriter


class TestEPUBWriter:
    """Test cases for EPUBWriter class"""

    def test_epub_writer_available(self):
        """Test that EPUBWriter checks for ebooklib"""
        writer = EPUBWriter()
        # Should return bool
        assert isinstance(writer.is_available(), bool)

    def test_epub_written(self, tmp_path):
        """Test that EPUB file is created"""
        writer = EPUBWriter()

        # Skip if ebooklib not available
        if not writer.is_available():
            pytest.skip("ebooklib not installed")

        # Create test chapters
        chapters = [
            ("Chapter 1", "This is the first chapter."),
            ("Chapter 2", "This is the second chapter."),
            ("Chapter 3", "This is the third chapter."),
        ]

        # Create EPUB
        epub_path = writer.create_epub(
            title="Test Novel",
            chapters=chapters,
            output_path=str(tmp_path),
            author="Test Author",
            language="en"
        )

        # Verify file exists
        assert Path(epub_path).exists()
        assert epub_path.endswith(".epub")

        # Verify file size (should be > 0)
        assert Path(epub_path).stat().st_size > 0

    def test_epub_handles_empty_chapter(self, tmp_path, capsys):
        """Test that empty chapters are logged and skipped"""
        writer = EPUBWriter()

        # Skip if ebooklib not available
        if not writer.is_available():
            pytest.skip("ebooklib not installed")

        # Create chapters with empty one
        chapters = [
            ("Chapter 1", "Content here"),
            ("Chapter 2", ""),  # Empty
            ("Chapter 3", "More content"),
        ]

        # Create EPUB
        epub_path = writer.create_epub(
            title="Test Novel",
            chapters=chapters,
            output_path=str(tmp_path)
        )

        # Should still succeed
        assert Path(epub_path).exists()

        # Should print warning about empty chapter
        captured = capsys.readouterr()
        assert "Skipping empty chapter" in captured.out

    def test_epub_sanitizes_html(self, tmp_path):
        """Test that HTML content is sanitized"""
        writer = EPUBWriter()

        # Skip if ebooklib not available
        if not writer.is_available():
            pytest.skip("ebooklib not installed")

        # Create chapter with special characters
        chapters = [
            ("Chapter 1", "Test <>&\"' characters"),
        ]

        # Should not raise
        epub_path = writer.create_epub(
            title="Test Novel",
            chapters=chapters,
            output_path=str(tmp_path)
        )

        assert Path(epub_path).exists()

    def test_epub_with_no_chapters_raises(self):
        """Test that creating EPUB with no chapters raises ValueError"""
        writer = EPUBWriter()

        # Skip if ebooklib not available
        if not writer.is_available():
            pytest.skip("ebooklib not installed")

        with pytest.raises(ValueError, match="Cannot create EPUB with no chapters"):
            writer.create_epub(
                title="Test",
                chapters=[],
                output_path="/tmp"
            )
