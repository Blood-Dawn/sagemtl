"""Output system for SageMTL with 15+ export formats.

This module provides a comprehensive export system with:
- Exporter protocol and registry
- Core formats: TXT, EPUB, PDF, HTML
- Extended formats: DOCX, Markdown, JSON, RTF
- Calibre integration for additional formats
- Metadata and cover handling
- Table of contents generation
"""

from .base import Exporter, ExporterRegistry, ExportCapability, ExportConfig
from .txt_exporter import TxtExporter
from .epub_exporter import EpubExporter
from .pdf_exporter import PdfExporter
from .html_exporter import HtmlExporter
from .docx_exporter import DocxExporter
from .markdown_exporter import MarkdownExporter
from .json_exporter import JsonExporter
from .rtf_exporter import RtfExporter
from .calibre import CalibreExporter, has_calibre

# Register all exporters
ExporterRegistry.register("txt", TxtExporter)
ExporterRegistry.register("epub", EpubExporter)
ExporterRegistry.register("pdf", PdfExporter)
ExporterRegistry.register("html", HtmlExporter)
ExporterRegistry.register("docx", DocxExporter)
ExporterRegistry.register("markdown", MarkdownExporter)
ExporterRegistry.register("md", MarkdownExporter)  # Alias
ExporterRegistry.register("json", JsonExporter)
ExporterRegistry.register("rtf", RtfExporter)

# Register Calibre formats if available
if has_calibre():
    ExporterRegistry.register("mobi", CalibreExporter)
    ExporterRegistry.register("azw3", CalibreExporter)
    ExporterRegistry.register("fb2", CalibreExporter)
    ExporterRegistry.register("lrf", CalibreExporter)

__all__ = [
    # Base
    "Exporter",
    "ExporterRegistry",
    "ExportCapability",
    "ExportConfig",
    # Exporters
    "TxtExporter",
    "EpubExporter",
    "PdfExporter",
    "HtmlExporter",
    "DocxExporter",
    "MarkdownExporter",
    "JsonExporter",
    "RtfExporter",
    "CalibreExporter",
    # Utilities
    "has_calibre",
]
