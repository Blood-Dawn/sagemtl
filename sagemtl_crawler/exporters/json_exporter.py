"""JSON exporter for novel data"""

import json
from pathlib import Path
from typing import List
from ..core.models import NovelTOC, ChapterContent


class JSONExporter:
    """Export novel to JSON format"""

    @staticmethod
    def export(
        toc: NovelTOC,
        chapters: List[ChapterContent],
        output_path: Path
    ):
        """
        Export novel to JSON file.

        Args:
            toc: Novel table of contents
            chapters: List of downloaded chapters
            output_path: Path to output JSON file
        """
        data = {
            "title": toc.title,
            "author": toc.author,
            "url": toc.url,
            "cover_url": toc.cover_url,
            "description": toc.description,
            "status": toc.status,
            "total_chapters": toc.total_chapters,
            "chapters": [
                {
                    "index": ch.ref.index,
                    "title": ch.ref.title,
                    "url": ch.ref.url,
                    "html": ch.html,
                    "text": ch.text,
                    "images": ch.images
                }
                for ch in chapters
            ]
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
