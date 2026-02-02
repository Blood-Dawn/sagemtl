"""
Multi-format Novel Exporter - Exports novels to various formats.

Supports: EPUB, JSON, Text, HTML/Web, Archives (zip)
Similar to lightnovel-crawler's output structure.
"""

import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from .novel_library import SavedNovel, SavedChapter


class NovelExporter:
    """
    Export novels to multiple formats.
    
    Creates output structure similar to lncrawl:
    - archives/     - Compressed archives
    - epub/         - EPUB files
    - json/         - JSON data files
    - text/         - Plain text files
    - web/          - HTML files
    - cover.jpg     - Cover image
    - meta.json     - Metadata
    """
    
    def __init__(self, output_base_dir: str):
        """
        Initialize exporter.
        
        Args:
            output_base_dir: Base directory for exports (e.g., Documents/Webnovels)
        """
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
    
    def export_novel(self, novel: SavedNovel, 
                     formats: List[str] = None,
                     use_translated: bool = True) -> Dict[str, str]:
        """
        Export a novel to multiple formats.
        
        Args:
            novel: The SavedNovel to export
            formats: List of formats to export ['epub', 'json', 'text', 'web', 'archive']
                     If None, exports all formats
            use_translated: If True, prefer translated content over original
            
        Returns:
            Dict mapping format name to output path
        """
        if formats is None:
            formats = ['epub', 'json', 'text', 'web', 'archive', 'meta']
        
        # Create novel directory
        safe_title = self._safe_filename(novel.title)
        novel_dir = self.output_base_dir / safe_title
        novel_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        # Get chapter content
        chapters = self._get_chapters_content(novel, use_translated)
        
        # Export each format
        if 'meta' in formats:
            results['meta'] = self._export_meta(novel, novel_dir)
        
        if 'json' in formats:
            results['json'] = self._export_json(novel, chapters, novel_dir)
        
        if 'text' in formats:
            results['text'] = self._export_text(novel, chapters, novel_dir)
        
        if 'web' in formats:
            results['web'] = self._export_web(novel, chapters, novel_dir)
        
        if 'epub' in formats:
            results['epub'] = self._export_epub(novel, chapters, novel_dir)
        
        if 'archive' in formats:
            results['archive'] = self._export_archive(novel, novel_dir)
        
        return results
    
    def _safe_filename(self, name: str) -> str:
        """Create a safe filename from a string"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        safe = name
        for char in invalid_chars:
            safe = safe.replace(char, '_')
        # Limit length
        return safe[:100].strip()
    
    def _get_chapters_content(self, novel: SavedNovel, 
                              use_translated: bool) -> List[Dict[str, Any]]:
        """Get chapter content, preferring translated if available"""
        chapters = []
        for ch in novel.chapters:
            content = ""
            if use_translated and ch.translated_content:
                content = ch.translated_content
            elif ch.cleaned_content:
                content = ch.cleaned_content
            else:
                content = ch.content
            
            chapters.append({
                'number': ch.chapter_number,
                'title': ch.title,
                'content': content,
                'url': ch.url
            })
        return chapters
    
    def _export_meta(self, novel: SavedNovel, novel_dir: Path) -> str:
        """Export metadata JSON file"""
        meta = {
            'title': novel.title,
            'author': novel.author,
            'source_url': novel.source_url,
            'chapter_count': len(novel.chapters),
            'created_at': novel.created_at,
            'updated_at': novel.updated_at,
            'cover_url': novel.cover_url,
            'description': novel.description,
            'exported_at': datetime.now().isoformat(),
            'exported_by': 'SageMTL Desktop'
        }
        
        meta_path = novel_dir / 'meta.json'
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        
        return str(meta_path)
    
    def _export_json(self, novel: SavedNovel, chapters: List[Dict], 
                     novel_dir: Path) -> str:
        """Export to JSON format"""
        json_dir = novel_dir / 'json'
        json_dir.mkdir(exist_ok=True)
        
        # Export full novel
        full_data = {
            'title': novel.title,
            'author': novel.author,
            'source_url': novel.source_url,
            'chapters': chapters
        }
        
        full_path = json_dir / 'novel.json'
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, indent=2, ensure_ascii=False)
        
        # Export individual chapters
        for ch in chapters:
            ch_path = json_dir / f"chapter_{ch['number']:04d}.json"
            with open(ch_path, 'w', encoding='utf-8') as f:
                json.dump(ch, f, indent=2, ensure_ascii=False)
        
        return str(json_dir)
    
    def _export_text(self, novel: SavedNovel, chapters: List[Dict],
                     novel_dir: Path) -> str:
        """Export to plain text format"""
        text_dir = novel_dir / 'text'
        text_dir.mkdir(exist_ok=True)
        
        # Export full novel as single file
        full_path = text_dir / f"{self._safe_filename(novel.title)}.txt"
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(f"{novel.title}\n")
            f.write(f"by {novel.author}\n")
            f.write(f"Source: {novel.source_url}\n")
            f.write("=" * 50 + "\n\n")
            
            for ch in chapters:
                f.write(f"\n{'=' * 40}\n")
                f.write(f"Chapter {ch['number']}: {ch['title']}\n")
                f.write(f"{'=' * 40}\n\n")
                f.write(ch['content'])
                f.write("\n\n")
        
        # Export individual chapters
        for ch in chapters:
            ch_path = text_dir / f"chapter_{ch['number']:04d}.txt"
            with open(ch_path, 'w', encoding='utf-8') as f:
                f.write(f"Chapter {ch['number']}: {ch['title']}\n\n")
                f.write(ch['content'])
        
        return str(text_dir)
    
    def _export_web(self, novel: SavedNovel, chapters: List[Dict],
                    novel_dir: Path) -> str:
        """Export to HTML/Web format"""
        web_dir = novel_dir / 'web'
        web_dir.mkdir(exist_ok=True)
        
        # CSS style
        css = """
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.8;
            background: #fafafa;
            color: #333;
        }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 40px; }
        .chapter-content { text-align: justify; }
        .meta { color: #666; font-style: italic; margin-bottom: 30px; }
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .toc { background: #fff; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .toc ul { list-style: none; padding-left: 0; }
        .toc li { padding: 5px 0; border-bottom: 1px solid #eee; }
        .nav { background: #3498db; color: white; padding: 10px 15px; 
               border-radius: 4px; display: inline-block; margin: 5px; }
        """
        
        # Write CSS
        css_path = web_dir / 'style.css'
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css)
        
        # Create index page with TOC
        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{novel.title}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>{novel.title}</h1>
    <p class="meta">by {novel.author}</p>
    <p class="meta">Source: <a href="{novel.source_url}">{novel.source_url}</a></p>
    
    <div class="toc">
        <h2>Table of Contents</h2>
        <ul>
"""
        for ch in chapters:
            index_html += f'            <li><a href="chapter_{ch["number"]:04d}.html">Chapter {ch["number"]}: {ch["title"]}</a></li>\n'
        
        index_html += """        </ul>
    </div>
</body>
</html>
"""
        
        index_path = web_dir / 'index.html'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        # Export individual chapters
        for i, ch in enumerate(chapters):
            prev_link = f'chapter_{chapters[i-1]["number"]:04d}.html' if i > 0 else 'index.html'
            next_link = f'chapter_{chapters[i+1]["number"]:04d}.html' if i < len(chapters)-1 else 'index.html'
            
            content_html = ch['content'].replace('\n', '<br>\n')
            
            chapter_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chapter {ch['number']}: {ch['title']} - {novel.title}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <nav>
        <a href="{prev_link}" class="nav">← Previous</a>
        <a href="index.html" class="nav">Contents</a>
        <a href="{next_link}" class="nav">Next →</a>
    </nav>
    
    <h1>Chapter {ch['number']}: {ch['title']}</h1>
    
    <div class="chapter-content">
        {content_html}
    </div>
    
    <nav style="margin-top: 40px;">
        <a href="{prev_link}" class="nav">← Previous</a>
        <a href="index.html" class="nav">Contents</a>
        <a href="{next_link}" class="nav">Next →</a>
    </nav>
</body>
</html>
"""
            ch_path = web_dir / f"chapter_{ch['number']:04d}.html"
            with open(ch_path, 'w', encoding='utf-8') as f:
                f.write(chapter_html)
        
        return str(web_dir)
    
    def _export_epub(self, novel: SavedNovel, chapters: List[Dict],
                     novel_dir: Path) -> str:
        """Export to EPUB format"""
        epub_dir = novel_dir / 'epub'
        epub_dir.mkdir(exist_ok=True)
        
        try:
            from .epub_writer import EPUBWriter
            writer = EPUBWriter()
            
            if not writer.is_available():
                return ""
            
            chapters_data = [(ch['title'], ch['content']) for ch in chapters]
            epub_path = writer.create_epub(
                title=novel.title,
                chapters=chapters_data,
                output_path=str(epub_dir),
                author=novel.author
            )
            return epub_path
        except Exception as e:
            print(f"EPUB export failed: {e}")
            return ""
    
    def _export_archive(self, novel: SavedNovel, novel_dir: Path) -> str:
        """Create zip archives of the exports"""
        archives_dir = novel_dir / 'archives'
        archives_dir.mkdir(exist_ok=True)
        
        safe_title = self._safe_filename(novel.title)
        
        # Create zip of everything
        zip_path = archives_dir / f"{safe_title}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for folder in ['json', 'text', 'web', 'epub']:
                folder_path = novel_dir / folder
                if folder_path.exists():
                    for file_path in folder_path.rglob('*'):
                        if file_path.is_file():
                            arcname = f"{safe_title}/{folder}/{file_path.relative_to(folder_path)}"
                            zf.write(file_path, arcname)
            
            # Add meta.json
            meta_path = novel_dir / 'meta.json'
            if meta_path.exists():
                zf.write(meta_path, f"{safe_title}/meta.json")
        
        return str(zip_path)
    
    def get_export_summary(self, results: Dict[str, str]) -> str:
        """Generate a summary of export results"""
        summary_parts = ["Export completed:\n"]
        
        for format_name, path in results.items():
            if path:
                summary_parts.append(f"  • {format_name}: {path}")
        
        return "\n".join(summary_parts)
