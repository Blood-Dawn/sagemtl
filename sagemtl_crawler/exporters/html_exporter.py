"""HTML exporter for novel data"""

import html
from pathlib import Path
from typing import List
from ..core.models import NovelTOC, ChapterContent


class HTMLExporter:
    """Export novel to single HTML file"""

    @staticmethod
    def export(
        toc: NovelTOC,
        chapters: List[ChapterContent],
        output_path: Path
    ):
        """
        Export novel to HTML file.

        Args:
            toc: Novel table of contents
            chapters: List of downloaded chapters
            output_path: Path to output HTML file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            # HTML header
            f.write(f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(toc.title)}</title>
    <style>
        body {{
            font-family: Georgia, serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        .author {{
            text-align: center;
            font-style: italic;
            color: #666;
        }}
        .description {{
            background: #f4f4f4;
            padding: 15px;
            margin: 20px 0;
            border-left: 4px solid #333;
        }}
        .chapter {{
            margin: 40px 0;
            page-break-before: always;
        }}
        .chapter-title {{
            font-size: 1.5em;
            font-weight: bold;
            margin: 20px 0;
            border-bottom: 1px solid #ccc;
        }}
    </style>
</head>
<body>
    <h1>{html.escape(toc.title)}</h1>
    <p class="author">by {html.escape(toc.author)}</p>
''')

            # Description
            if toc.description:
                f.write(f'''
    <div class="description">
        <p>{html.escape(toc.description)}</p>
    </div>
''')

            # Table of Contents
            f.write('\n    <div class="toc">\n        <h2>Table of Contents</h2>\n        <ul>\n')
            for chapter in chapters:
                f.write(f'            <li><a href="#chapter-{chapter.ref.index}">'
                        f'{html.escape(chapter.ref.title)}</a></li>\n')
            f.write('        </ul>\n    </div>\n')

            # Chapters
            for chapter in chapters:
                f.write(f'''
    <div class="chapter" id="chapter-{chapter.ref.index}">
        <h2 class="chapter-title">{html.escape(chapter.ref.title)}</h2>
        {chapter.html}
    </div>
''')

            # HTML footer
            f.write('''
</body>
</html>
''')
