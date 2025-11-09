"""
EPUB file extraction and parsing.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML"""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.ignore_tags = {'script', 'style'}  # Don't extract text from these
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag

    def handle_endtag(self, tag):
        self.current_tag = None

    def handle_data(self, data):
        # Skip script and style content
        if self.current_tag not in self.ignore_tags:
            self.text_parts.append(data)

    def get_text(self):
        """Get extracted text"""
        # Join and clean up whitespace
        text = ''.join(self.text_parts)
        # Normalize whitespace but preserve paragraphs
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        return '\n\n'.join(lines)


class EPUBExtractor:
    """Extract text from EPUB files"""

    # XML namespaces used in EPUB files
    NAMESPACES = {
        'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }

    def extract(self, epub_path: str) -> Tuple[str, List[str]]:
        """
        Extract chapters from EPUB.

        Args:
            epub_path: Path to EPUB file

        Returns:
            Tuple of (full_text, list_of_chapter_texts)

        Raises:
            FileNotFoundError: If EPUB file doesn't exist
            zipfile.BadZipFile: If file is not a valid EPUB/ZIP
            ValueError: If EPUB structure is invalid
        """
        epub_file = Path(epub_path)
        if not epub_file.exists():
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")

        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            # Step 1: Find content.opf location from META-INF/container.xml
            try:
                container_xml = zip_ref.read('META-INF/container.xml')
            except KeyError:
                raise ValueError("Not a valid EPUB: META-INF/container.xml not found")

            container_tree = ET.fromstring(container_xml)

            # Get path to content.opf
            rootfile = container_tree.find('.//container:rootfile', self.NAMESPACES)
            if rootfile is None:
                raise ValueError("Invalid EPUB container.xml")

            opf_path = rootfile.get('full-path')
            if not opf_path:
                raise ValueError("No content.opf path found in container.xml")

            # Step 2: Parse content.opf
            try:
                opf_xml = zip_ref.read(opf_path)
            except KeyError:
                raise ValueError(f"content.opf not found at {opf_path}")

            opf_tree = ET.fromstring(opf_xml)

            # Step 3: Get reading order from spine
            spine_items = []
            spine = opf_tree.find('.//opf:spine', self.NAMESPACES)
            if spine is not None:
                for itemref in spine.findall('opf:itemref', self.NAMESPACES):
                    idref = itemref.get('idref')
                    if idref:
                        spine_items.append(idref)

            if not spine_items:
                print("Warning: No spine items found, will try to extract from manifest")

            # Step 4: Get manifest (maps id to href)
            manifest = {}
            manifest_elem = opf_tree.find('.//opf:manifest', self.NAMESPACES)
            if manifest_elem is not None:
                for item in manifest_elem.findall('opf:item', self.NAMESPACES):
                    item_id = item.get('id')
                    href = item.get('href')
                    media_type = item.get('media-type', '')

                    if item_id and href:
                        manifest[item_id] = (href, media_type)

            # If no spine, try to use all HTML files from manifest
            if not spine_items:
                spine_items = [
                    item_id for item_id, (href, media_type) in manifest.items()
                    if 'html' in media_type or 'xhtml' in media_type
                ]

            # Step 5: Extract chapters in order
            opf_dir = Path(opf_path).parent
            chapters = []
            failed_count = 0
            total_count = 0

            for item_id in spine_items:
                if item_id not in manifest:
                    print(f"Warning: Spine item '{item_id}' not in manifest, skipping")
                    continue

                href, media_type = manifest[item_id]

                # Only process HTML/XHTML files
                if 'html' not in media_type and 'xhtml' not in media_type:
                    continue

                total_count += 1

                # Fix: Convert Windows backslashes to forward slashes for ZIP compatibility
                # ZIP files always use forward slashes internally, regardless of OS
                if opf_dir == Path('.'):
                    chapter_path = href
                else:
                    chapter_path = str(opf_dir / href).replace('\\', '/')

                try:
                    chapter_html = zip_ref.read(chapter_path).decode('utf-8', errors='ignore')
                    chapter_text = self._extract_text_from_html(chapter_html)

                    if chapter_text.strip():  # Only add non-empty chapters
                        chapters.append(chapter_text)
                except KeyError:
                    failed_count += 1
                    print(f"Warning: File not found: {chapter_path}")
                except Exception as e:
                    failed_count += 1
                    print(f"Warning: Failed to extract {chapter_path}: {e}")

            if not chapters:
                raise ValueError(
                    f"No chapters extracted from EPUB. Failed to read {failed_count} file(s). "
                    f"The EPUB may be corrupted or use an unsupported structure."
                )

            print(f"Successfully extracted {len(chapters)} chapters from EPUB (failed: {failed_count})")

            # Step 6: Concatenate with chapter markers
            full_text = ""
            for i, chapter in enumerate(chapters, 1):
                full_text += f"\n\n{'='*60}\n"
                full_text += f"Chapter {i}\n"
                full_text += f"{'='*60}\n\n"
                full_text += chapter

            return full_text, chapters

    def _extract_text_from_html(self, html: str) -> str:
        """
        Extract plain text from HTML.

        Args:
            html: HTML content

        Returns:
            Plain text
        """
        parser = HTMLTextExtractor()
        try:
            parser.feed(html)
            return parser.get_text().strip()
        except Exception as e:
            print(f"Warning: HTML parsing error: {e}")
            # Fallback: simple tag stripping
            import re
            text = re.sub(r'<[^>]+>', '', html)
            return text.strip()
