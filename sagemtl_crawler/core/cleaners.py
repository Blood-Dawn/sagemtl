"""
HTML extraction and cleaning utilities
"""

import re
from html.parser import HTMLParser
from typing import List, Tuple
from urllib.parse import urljoin


class HTMLTextExtractor(HTMLParser):
    """Extract clean text from HTML while preserving structure"""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_script = False
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.in_script = tag == 'script'
            self.in_style = tag == 'style'
        elif tag == 'br':
            self.text_parts.append('\n')
        elif tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text_parts.append('\n\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.in_script = False
            self.in_style = False
        elif tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text_parts.append('\n\n')

    def handle_data(self, data):
        if not (self.in_script or self.in_style):
            # Clean up whitespace but preserve intentional line breaks
            cleaned = ' '.join(data.split())
            if cleaned:
                self.text_parts.append(cleaned)

    def get_text(self) -> str:
        """Get the extracted text"""
        text = ''.join(self.text_parts)
        # Normalize multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


class HTMLCleaner:
    """Clean and normalize HTML content"""

    # Tags to preserve (article content)
    ALLOWED_TAGS = {
        'p', 'div', 'span', 'br', 'hr',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'strong', 'b', 'em', 'i', 'u', 's', 'mark',
        'ul', 'ol', 'li',
        'blockquote', 'code', 'pre',
        'img', 'a'
    }

    # Tags to remove entirely (including content)
    STRIP_TAGS = {
        'script', 'style', 'noscript', 'iframe', 'object', 'embed',
        'nav', 'header', 'footer', 'aside', 'form', 'button'
    }

    def __init__(self, base_url: str = ""):
        self.base_url = base_url

    def clean_html(self, html: str) -> str:
        """
        Clean HTML by removing unwanted tags and normalizing content.

        Args:
            html: Raw HTML string

        Returns:
            Cleaned HTML
        """
        # Remove comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

        # Remove script and style tags with content
        for tag in self.STRIP_TAGS:
            html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Normalize whitespace
        html = re.sub(r'\s+', ' ', html)

        # Fix relative URLs in images and links
        if self.base_url:
            html = self._fix_relative_urls(html)

        return html.strip()

    def _fix_relative_urls(self, html: str) -> str:
        """Convert relative URLs to absolute URLs"""

        def replace_url(match):
            tag = match.group(1)
            attr = match.group(2)
            url = match.group(3)

            # Convert relative to absolute
            absolute_url = urljoin(self.base_url, url)

            return f'<{tag} {attr}="{absolute_url}"'

        # Fix img src
        html = re.sub(
            r'<(img)\s+[^>]*?(src)=["\']([^"\']+)["\']',
            replace_url,
            html,
            flags=re.IGNORECASE
        )

        # Fix a href
        html = re.sub(
            r'<(a)\s+[^>]*?(href)=["\']([^"\']+)["\']',
            replace_url,
            html,
            flags=re.IGNORECASE
        )

        return html

    def extract_images(self, html: str) -> List[str]:
        """Extract all image URLs from HTML"""
        pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        matches = re.findall(pattern, html, flags=re.IGNORECASE)

        # Convert relative to absolute if base_url is set
        if self.base_url:
            return [urljoin(self.base_url, url) for url in matches]

        return matches

    def strip_html_tags(self, html: str) -> str:
        """Remove all HTML tags, keeping only text"""
        extractor = HTMLTextExtractor()
        try:
            extractor.feed(html)
            return extractor.get_text()
        except Exception as e:
            # Fallback: simple regex stripping
            text = re.sub(r'<[^>]+>', '', html)
            return ' '.join(text.split())


def extract_chapter_content(html: str, base_url: str = "") -> Tuple[str, str, List[str]]:
    """
    Extract chapter content from HTML.

    Args:
        html: Raw chapter HTML
        base_url: Base URL for fixing relative links

    Returns:
        Tuple of (cleaned_html, plain_text, image_urls)
    """
    cleaner = HTMLCleaner(base_url)

    # Clean HTML
    cleaned_html = cleaner.clean_html(html)

    # Extract text
    plain_text = cleaner.strip_html_tags(cleaned_html)

    # Extract images
    images = cleaner.extract_images(cleaned_html)

    return cleaned_html, plain_text, images
