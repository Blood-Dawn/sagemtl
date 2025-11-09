"""TXT exporter for novel data"""

from pathlib import Path
from typing import List
from ..core.models import NovelTOC, ChapterContent


class TXTExporter:
    """Export novel to plain text format"""

    @staticmethod
    def export(
        toc: NovelTOC,
        chapters: List[ChapterContent],
        output_path: Path
    ):
        """
        Export novel to TXT file.

        Args:
            toc: Novel table of contents
            chapters: List of downloaded chapters
            output_path: Path to output TXT file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            # Header
            f.write(f"{toc.title}\n")
            f.write(f"by {toc.author}\n")
            f.write("=" * 60 + "\n\n")

            if toc.description:
                f.write(f"{toc.description}\n\n")
                f.write("=" * 60 + "\n\n")

            # Chapters
            for chapter in chapters:
                f.write(f"\n{'=' * 60}\n")
                f.write(f"Chapter {chapter.ref.index}: {chapter.ref.title}\n")
                f.write(f"{'=' * 60}\n\n")
                f.write(chapter.text)
                f.write("\n\n")
