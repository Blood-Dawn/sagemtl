"""Plain text exporter for SageMTL."""

from __future__ import annotations

from typing import List

from .base import (
    BaseExporter,
    ExportCapability,
    ExportConfig,
    ExportResult,
    NovelData,
)


class TxtExporter(BaseExporter):
    """Export novel to plain text format.

    Features:
    - Chapter headers
    - Volume separators (optional)
    - Configurable formatting
    """

    @classmethod
    def name(cls) -> str:
        return "Plain Text"

    @classmethod
    def extensions(cls) -> List[str]:
        return ["txt"]

    @classmethod
    def capabilities(cls) -> ExportCapability:
        return ExportCapability.METADATA | ExportCapability.VOLUMES

    def export(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> ExportResult:
        """Export novel to TXT file."""
        output_path = self._get_output_path(novel, config)

        try:
            lines = []

            # Title and metadata
            lines.append("=" * 60)
            lines.append(novel.title.center(60))
            if novel.author:
                lines.append(f"by {novel.author}".center(60))
            lines.append("=" * 60)
            lines.append("")

            if config.include_metadata:
                if novel.description:
                    lines.append("DESCRIPTION:")
                    lines.append(novel.description)
                    lines.append("")

                if novel.genres:
                    lines.append(f"Genres: {', '.join(novel.genres)}")
                    lines.append("")

            # Table of contents (optional)
            if config.include_toc and novel.chapters:
                lines.append("-" * 40)
                lines.append("TABLE OF CONTENTS")
                lines.append("-" * 40)
                for chapter in novel.chapters:
                    lines.append(f"  {chapter.index}. {chapter.title}")
                lines.append("")

            # Chapters
            current_volume = None
            for chapter in novel.chapters:
                # Volume header
                if config.split_by_volume and chapter.volume_index is not None:
                    if chapter.volume_index != current_volume:
                        current_volume = chapter.volume_index
                        volume = next(
                            (v for v in novel.volumes if v.index == current_volume),
                            None
                        )
                        if volume:
                            if config.volume_page_break:
                                lines.append("\n" + "=" * 60 + "\n")
                            lines.append(f"VOLUME {volume.index}: {volume.title}")
                            lines.append("=" * 60)
                            lines.append("")

                # Chapter header
                lines.append("-" * 40)
                lines.append(f"Chapter {chapter.index}: {chapter.title}")
                lines.append("-" * 40)
                lines.append("")

                # Chapter content
                lines.append(chapter.content)
                lines.append("")
                lines.append("")

            # Write file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            return ExportResult.ok(output_path)

        except Exception as e:
            return ExportResult.failure(str(e))
