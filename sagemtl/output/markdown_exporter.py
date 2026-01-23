"""Markdown exporter for SageMTL."""

from __future__ import annotations

from typing import List

from .base import (
    BaseExporter,
    ExportCapability,
    ExportConfig,
    ExportResult,
    NovelData,
)


class MarkdownExporter(BaseExporter):
    """Export novel to Markdown format.

    Features:
    - GitHub Flavored Markdown compatible
    - Table of contents
    - Volume and chapter structure
    - Metadata as YAML frontmatter
    """

    @classmethod
    def name(cls) -> str:
        return "Markdown"

    @classmethod
    def extensions(cls) -> List[str]:
        return ["md", "markdown"]

    @classmethod
    def capabilities(cls) -> ExportCapability:
        return (
            ExportCapability.TOC |
            ExportCapability.METADATA |
            ExportCapability.VOLUMES |
            ExportCapability.HYPERLINKS
        )

    def export(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> ExportResult:
        """Export novel to Markdown file."""
        output_path = self._get_output_path(novel, config, extension="md")

        try:
            lines = []

            # YAML frontmatter
            if config.include_metadata:
                lines.extend(self._generate_frontmatter(novel, config))

            # Title
            title = config.title or novel.title
            lines.append(f"# {title}")
            lines.append("")

            # Author
            author = config.author or novel.author
            if author:
                lines.append(f"*by {author}*")
                lines.append("")

            # Description
            if novel.description:
                lines.append("> " + novel.description.replace("\n", "\n> "))
                lines.append("")

            # Table of contents
            if config.include_toc:
                lines.extend(self._generate_toc(novel))

            # Chapters
            lines.extend(self._generate_chapters(novel, config))

            # Write file
            content = "\n".join(lines)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            return ExportResult.ok(output_path)

        except Exception as e:
            return ExportResult.failure(str(e))

    def _generate_frontmatter(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> List[str]:
        """Generate YAML frontmatter."""
        lines = ["---"]

        title = config.title or novel.title
        author = config.author or novel.author

        lines.append(f"title: \"{title}\"")
        if author:
            lines.append(f"author: \"{author}\"")
        lines.append(f"language: {config.language}")

        if novel.genres:
            lines.append("genres:")
            for genre in novel.genres:
                lines.append(f"  - {genre}")

        if novel.tags:
            lines.append("tags:")
            for tag in novel.tags:
                lines.append(f"  - {tag}")

        if novel.source_url:
            lines.append(f"source: \"{novel.source_url}\"")

        lines.append(f"chapters: {novel.total_chapters}")
        lines.append(f"words: {novel.total_words}")
        lines.append("generator: SageMTL")
        lines.append("---")
        lines.append("")

        return lines

    def _generate_toc(self, novel: NovelData) -> List[str]:
        """Generate table of contents."""
        lines = []
        lines.append("## Table of Contents")
        lines.append("")

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
                    lines.append(f"- **{volume.title}**")

            # Chapter link
            anchor = self._make_anchor(chapter.title)
            indent = "  " if chapter.volume_index is not None else ""
            lines.append(f"{indent}- [{chapter.title}](#{anchor})")

        lines.append("")
        lines.append("---")
        lines.append("")

        return lines

    def _generate_chapters(
        self,
        novel: NovelData,
        config: ExportConfig,
    ) -> List[str]:
        """Generate chapter content."""
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
                if volume:
                    lines.append(f"## {volume.title}")
                    lines.append("")

            # Chapter header
            lines.append(f"### {chapter.title}")
            lines.append("")

            # Chapter content
            lines.append(chapter.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return lines

    @staticmethod
    def _make_anchor(text: str) -> str:
        """Convert text to a valid Markdown anchor."""
        # Convert to lowercase
        anchor = text.lower()
        # Replace spaces with hyphens
        anchor = anchor.replace(" ", "-")
        # Remove invalid characters
        anchor = "".join(c for c in anchor if c.isalnum() or c == "-")
        # Remove multiple hyphens
        while "--" in anchor:
            anchor = anchor.replace("--", "-")
        return anchor
