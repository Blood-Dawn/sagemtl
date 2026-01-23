"""Tests for the export system."""

import json
import tempfile
from pathlib import Path

import pytest

from sagemtl.output.base import (
    ExporterRegistry,
    ExportConfig,
    ExportCapability,
    ExportResult,
    NovelData,
    ChapterData,
    VolumeData,
    export_novel,
)
from sagemtl.output.txt_exporter import TxtExporter
from sagemtl.output.html_exporter import HtmlExporter
from sagemtl.output.markdown_exporter import MarkdownExporter
from sagemtl.output.json_exporter import JsonExporter
from sagemtl.output.rtf_exporter import RtfExporter


@pytest.fixture
def sample_novel() -> NovelData:
    """Create a sample novel for testing."""
    return NovelData(
        title="Test Novel",
        author="Test Author",
        description="A test novel for export testing.",
        language="en",
        genres=["Fantasy", "Adventure"],
        tags=["magic", "hero"],
        source_url="https://example.com/novel",
        chapters=[
            ChapterData(
                index=1,
                title="Chapter 1: The Beginning",
                content="This is the first chapter.\n\nIt has multiple paragraphs.",
                volume_index=1,
            ),
            ChapterData(
                index=2,
                title="Chapter 2: The Journey",
                content="The journey begins.\n\nMany adventures await.",
                volume_index=1,
            ),
            ChapterData(
                index=3,
                title="Chapter 3: The End",
                content="And so it ends.\n\nThe hero returns home.",
                volume_index=2,
            ),
        ],
        volumes=[
            VolumeData(index=1, title="Volume 1: Origins", chapter_start=1, chapter_end=2),
            VolumeData(index=2, title="Volume 2: Finale", chapter_start=3, chapter_end=3),
        ],
    )


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestExporterRegistry:
    """Test the exporter registry."""

    def test_list_formats(self):
        """Test listing registered formats."""
        formats = ExporterRegistry.list_formats()
        assert "txt" in formats
        assert "html" in formats
        assert "json" in formats

    def test_list_available(self):
        """Test listing available formats."""
        available = ExporterRegistry.list_available()
        # TXT and HTML should always be available
        assert "txt" in available
        assert "html" in available

    def test_get_exporter(self):
        """Test getting an exporter class."""
        exporter_class = ExporterRegistry.get("txt")
        assert exporter_class is not None
        assert exporter_class == TxtExporter

    def test_get_nonexistent(self):
        """Test getting a nonexistent exporter."""
        exporter_class = ExporterRegistry.get("nonexistent")
        assert exporter_class is None

    def test_create_exporter(self):
        """Test creating an exporter instance."""
        exporter = ExporterRegistry.create("txt")
        assert exporter is not None
        assert isinstance(exporter, TxtExporter)

    def test_get_info(self):
        """Test getting exporter info."""
        info = ExporterRegistry.get_info("txt")
        assert info is not None
        assert info["name"] == "Plain Text"
        assert "txt" in info["extensions"]
        assert info["available"] is True


class TestExportConfig:
    """Test the export configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExportConfig()
        assert config.include_cover is True
        assert config.include_toc is True
        assert config.include_metadata is True
        assert config.language == "en"

    def test_custom_config(self):
        """Test custom configuration."""
        config = ExportConfig(
            output_path=Path("/custom/path"),
            include_cover=False,
            include_toc=False,
            font_size=14,
            language="zh",
        )
        assert config.output_path == Path("/custom/path")
        assert config.include_cover is False
        assert config.include_toc is False
        assert config.font_size == 14
        assert config.language == "zh"


class TestExportResult:
    """Test the export result."""

    def test_success_result(self):
        """Test success result creation."""
        result = ExportResult.ok(Path("/output/file.txt"))
        assert result.success is True
        assert result.output_path == Path("/output/file.txt")
        assert result.error is None

    def test_failure_result(self):
        """Test failure result creation."""
        result = ExportResult.failure("Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"


class TestNovelData:
    """Test novel data model."""

    def test_total_chapters(self, sample_novel):
        """Test total chapter count."""
        assert sample_novel.total_chapters == 3

    def test_total_words(self, sample_novel):
        """Test total word count estimation."""
        assert sample_novel.total_words > 0


class TestTxtExporter:
    """Test TXT exporter."""

    def test_name(self):
        """Test exporter name."""
        assert TxtExporter.name() == "Plain Text"

    def test_extensions(self):
        """Test supported extensions."""
        assert "txt" in TxtExporter.extensions()

    def test_capabilities(self):
        """Test exporter capabilities."""
        caps = TxtExporter.capabilities()
        assert ExportCapability.METADATA in caps
        assert ExportCapability.VOLUMES in caps

    def test_export(self, sample_novel, temp_output_dir):
        """Test TXT export."""
        exporter = TxtExporter()
        config = ExportConfig(output_path=temp_output_dir)

        result = exporter.export(sample_novel, config)

        assert result.success is True
        assert result.output_path.exists()
        assert result.output_path.suffix == ".txt"

        content = result.output_path.read_text(encoding="utf-8")
        assert sample_novel.title in content
        assert sample_novel.author in content
        assert "Chapter 1" in content


class TestHtmlExporter:
    """Test HTML exporter."""

    def test_name(self):
        """Test exporter name."""
        assert HtmlExporter.name() == "HTML"

    def test_export(self, sample_novel, temp_output_dir):
        """Test HTML export."""
        exporter = HtmlExporter()
        config = ExportConfig(output_path=temp_output_dir)

        result = exporter.export(sample_novel, config)

        assert result.success is True
        assert result.output_path.exists()

        content = result.output_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert sample_novel.title in content
        assert "chapter-1" in content


class TestMarkdownExporter:
    """Test Markdown exporter."""

    def test_name(self):
        """Test exporter name."""
        assert MarkdownExporter.name() == "Markdown"

    def test_export(self, sample_novel, temp_output_dir):
        """Test Markdown export."""
        exporter = MarkdownExporter()
        config = ExportConfig(output_path=temp_output_dir)

        result = exporter.export(sample_novel, config)

        assert result.success is True
        assert result.output_path.exists()
        assert result.output_path.suffix == ".md"

        content = result.output_path.read_text(encoding="utf-8")
        assert f"# {sample_novel.title}" in content
        assert "## Table of Contents" in content


class TestJsonExporter:
    """Test JSON exporter."""

    def test_name(self):
        """Test exporter name."""
        assert JsonExporter.name() == "JSON"

    def test_export(self, sample_novel, temp_output_dir):
        """Test JSON export."""
        exporter = JsonExporter()
        config = ExportConfig(output_path=temp_output_dir)

        result = exporter.export(sample_novel, config)

        assert result.success is True
        assert result.output_path.exists()

        # Verify JSON structure
        with open(result.output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["metadata"]["title"] == sample_novel.title
        assert data["metadata"]["author"] == sample_novel.author
        assert len(data["chapters"]) == 3
        assert len(data["volumes"]) == 2

    def test_export_compressed(self, sample_novel, temp_output_dir):
        """Test compressed JSON export."""
        exporter = JsonExporter()
        config = ExportConfig(output_path=temp_output_dir, compress=True)

        result = exporter.export(sample_novel, config)

        assert result.success is True
        content = result.output_path.read_text(encoding="utf-8")
        # Compressed JSON should not have newlines (except within strings)
        assert "\n\n" not in content


class TestRtfExporter:
    """Test RTF exporter."""

    def test_name(self):
        """Test exporter name."""
        assert RtfExporter.name() == "Rich Text Format"

    def test_export(self, sample_novel, temp_output_dir):
        """Test RTF export."""
        exporter = RtfExporter()
        config = ExportConfig(output_path=temp_output_dir)

        result = exporter.export(sample_novel, config)

        assert result.success is True
        assert result.output_path.exists()
        assert result.output_path.suffix == ".rtf"

        content = result.output_path.read_text(encoding="utf-8")
        assert content.startswith("{\\rtf1")
        assert "Test Novel" in content


class TestExportNovelFunction:
    """Test the convenience export_novel function."""

    def test_export_txt(self, sample_novel, temp_output_dir):
        """Test exporting to TXT."""
        config = ExportConfig(output_path=temp_output_dir)
        result = export_novel(sample_novel, "txt", config)

        assert result.success is True
        assert result.output_path.exists()

    def test_export_invalid_format(self, sample_novel, temp_output_dir):
        """Test exporting to invalid format."""
        config = ExportConfig(output_path=temp_output_dir)
        result = export_novel(sample_novel, "invalid_format", config)

        assert result.success is False
        assert "not available" in result.error


class TestFilenameGeneration:
    """Test filename generation."""

    def test_default_filename(self, sample_novel, temp_output_dir):
        """Test default filename template."""
        exporter = TxtExporter()
        config = ExportConfig(output_path=temp_output_dir)

        result = exporter.export(sample_novel, config)

        assert "Test Novel" in result.output_path.name

    def test_custom_filename(self, sample_novel, temp_output_dir):
        """Test custom filename template."""
        exporter = TxtExporter()
        config = ExportConfig(
            output_path=temp_output_dir,
            filename_template="{author} - {title}",
        )

        result = exporter.export(sample_novel, config)

        assert "Test Author" in result.output_path.name
        assert "Test Novel" in result.output_path.name


class TestMetadataOverrides:
    """Test metadata override functionality."""

    def test_override_title(self, sample_novel, temp_output_dir):
        """Test overriding title."""
        exporter = JsonExporter()
        config = ExportConfig(
            output_path=temp_output_dir,
            title="Custom Title",
        )

        result = exporter.export(sample_novel, config)

        with open(result.output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["metadata"]["title"] == "Custom Title"

    def test_override_author(self, sample_novel, temp_output_dir):
        """Test overriding author."""
        exporter = JsonExporter()
        config = ExportConfig(
            output_path=temp_output_dir,
            author="Custom Author",
        )

        result = exporter.export(sample_novel, config)

        with open(result.output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["metadata"]["author"] == "Custom Author"
