"""JSON exporter for SageMTL."""

from __future__ import annotations

import json
from datetime import datetime
from typing import List

from .base import (
    BaseExporter,
    ExportCapability,
    ExportConfig,
    ExportResult,
    NovelData,
)


class JsonExporter(BaseExporter):
    """Export novel to JSON format.

    Features:
    - Structured data export
    - Full metadata preservation
    - Machine-readable format
    - Optional minification
    """

    @classmethod
    def name(cls) -> str:
        return "JSON"

    @classmethod
    def extensions(cls) -> List[str]:
        return ["json"]

    @classmethod
    def capabilities(cls) -> ExportCapability:
        return ExportCapability.METADATA | ExportCapability.VOLUMES

    def export(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> ExportResult:
        """Export novel to JSON file."""
        output_path = self._get_output_path(novel, config)

        try:
            # Build JSON structure
            data = self._build_json(novel, config)

            # Determine indentation
            indent = None if config.compress else 2

            # Write file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)

            return ExportResult.ok(output_path)

        except Exception as e:
            return ExportResult.failure(str(e))

    def _build_json(self, novel: NovelData, config: ExportConfig) -> dict:
        """Build JSON data structure."""
        data = {
            "metadata": {
                "title": config.title or novel.title,
                "author": config.author or novel.author,
                "description": novel.description,
                "language": config.language or novel.language,
                "genres": novel.genres,
                "tags": novel.tags,
                "source_url": novel.source_url,
                "total_chapters": novel.total_chapters,
                "total_words": novel.total_words,
                "exported_at": datetime.now().isoformat(),
                "generator": "SageMTL",
            },
            "volumes": [],
            "chapters": [],
        }

        # Add cover path if available
        if novel.cover_path:
            data["metadata"]["cover_path"] = str(novel.cover_path)

        # Add volumes
        for volume in novel.volumes:
            data["volumes"].append({
                "index": volume.index,
                "title": volume.title,
                "chapter_start": volume.chapter_start,
                "chapter_end": volume.chapter_end,
            })

        # Add chapters
        for chapter in novel.chapters:
            chapter_data = {
                "index": chapter.index,
                "title": chapter.title,
                "content": chapter.content,
                "word_count": chapter.word_count,
            }

            if chapter.volume_index is not None:
                chapter_data["volume_index"] = chapter.volume_index

            if chapter.html_content:
                chapter_data["html_content"] = chapter.html_content

            data["chapters"].append(chapter_data)

        return data
