"""RTF exporter for SageMTL."""

from __future__ import annotations

from typing import List

from .base import (
    BaseExporter,
    ExportCapability,
    ExportConfig,
    ExportResult,
    NovelData,
)


class RtfExporter(BaseExporter):
    """Export novel to RTF (Rich Text Format).

    Features:
    - Legacy word processor compatibility
    - Basic formatting (bold, italic)
    - Chapter structure
    - No external dependencies
    """

    @classmethod
    def name(cls) -> str:
        return "Rich Text Format"

    @classmethod
    def extensions(cls) -> List[str]:
        return ["rtf"]

    @classmethod
    def capabilities(cls) -> ExportCapability:
        return ExportCapability.METADATA | ExportCapability.STYLES | ExportCapability.VOLUMES

    def export(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> ExportResult:
        """Export novel to RTF file."""
        output_path = self._get_output_path(novel, config)

        try:
            # Generate RTF content
            rtf_content = self._generate_rtf(novel, config)

            # Write file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rtf_content)

            return ExportResult.ok(output_path)

        except Exception as e:
            return ExportResult.failure(str(e))

    def _generate_rtf(self, novel: NovelData, config: ExportConfig) -> str:
        """Generate RTF document content."""
        title = config.title or novel.title
        author = config.author or novel.author

        # RTF header
        lines = [
            r"{\rtf1\ansi\deff0",
            # Font table
            r"{\fonttbl",
            r"{\f0\froman Times New Roman;}",
            r"{\f1\fswiss Arial;}",
            r"}",
            # Color table
            r"{\colortbl;\red0\green0\blue0;\red128\green128\blue128;}",
            # Document info
            r"{\info",
            r"{\title " + self._escape_rtf(title) + r"}",
        ]

        if author:
            lines.append(r"{\author " + self._escape_rtf(author) + r"}")

        lines.append(r"}")

        # Document settings
        lines.extend([
            r"\paperw12240\paperh15840",  # Letter size
            r"\margl1440\margr1440\margt1440\margb1440",  # 1 inch margins
            r"\f0\fs" + str(config.font_size * 2),  # Font size (half-points)
        ])

        # Cover page
        if config.include_cover:
            lines.extend(self._generate_cover(novel, config))

        # Table of contents
        if config.include_toc:
            lines.extend(self._generate_toc(novel))

        # Chapters
        lines.extend(self._generate_chapters(novel, config))

        # RTF footer
        lines.append(r"}")

        return "\n".join(lines)

    def _generate_cover(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> List[str]:
        """Generate cover page RTF."""
        title = config.title or novel.title
        author = config.author or novel.author

        lines = [
            # Center alignment
            r"\pard\qc",
            # Vertical space
            r"\par\par\par\par\par\par\par\par",
            # Title (large, bold)
            r"\f1\fs56\b " + self._escape_rtf(title) + r"\b0\par",
            r"\par",
        ]

        if author:
            lines.extend([
                # Author (italic)
                r"\f0\fs28\i by " + self._escape_rtf(author) + r"\i0\par",
                r"\par",
            ])

        if novel.description:
            lines.extend([
                r"\par\par",
                r"\f0\fs24 " + self._escape_rtf(novel.description) + r"\par",
            ])

        # Page break
        lines.append(r"\page")

        return lines

    def _generate_toc(self, novel: NovelData) -> List[str]:
        """Generate table of contents RTF."""
        lines = [
            r"\pard\qc",
            r"\f1\fs32\b Table of Contents\b0\par",
            r"\par",
            r"\pard\ql\fi0\li720",  # Left align, no indent, margin
        ]

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
                    lines.append(
                        r"\par\f1\fs24\b " +
                        self._escape_rtf(volume.title) +
                        r"\b0\par"
                    )

            # Chapter entry
            lines.append(
                r"\f0\fs22     " +
                self._escape_rtf(chapter.title) +
                r"\par"
            )

        lines.append(r"\page")

        return lines

    def _generate_chapters(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> List[str]:
        """Generate chapters RTF."""
        lines = []
        current_volume = None

        for chapter in novel.chapters:
            # Volume header
            if chapter.volume_index is not None and chapter.volume_index != current_volume:
                current_volume = chapter.volume_index
                volume = next(
                    (v for v in novel.volumes if v.index == current_volume),
                    None
                )
                if volume and config.volume_page_break:
                    lines.extend([
                        r"\page",
                        r"\pard\qc",
                        r"\par\par\par\par\par",
                        r"\f1\fs40\b " + self._escape_rtf(volume.title) + r"\b0\par",
                        r"\page",
                    ])

            # Chapter title
            lines.extend([
                r"\pard\qc",
                r"\f1\fs28\b " + self._escape_rtf(chapter.title) + r"\b0\par",
                r"\par",
                r"\pard\ql\fi720",  # Paragraph indent
            ])

            # Chapter content
            paragraphs = chapter.content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    lines.append(
                        r"\f0\fs" + str(config.font_size * 2) + " " +
                        self._escape_rtf(para.strip()) +
                        r"\par\par"
                    )

            # Page break after chapter
            if config.volume_page_break:
                lines.append(r"\page")

        return lines

    @staticmethod
    def _escape_rtf(text: str) -> str:
        """Escape special characters for RTF."""
        # Escape backslashes first
        text = text.replace("\\", "\\\\")
        # Escape curly braces
        text = text.replace("{", "\\{")
        text = text.replace("}", "\\}")
        # Handle newlines
        text = text.replace("\n", "\\par ")
        # Handle Unicode characters
        result = []
        for char in text:
            if ord(char) > 127:
                result.append(f"\\u{ord(char)}?")
            else:
                result.append(char)
        return "".join(result)
