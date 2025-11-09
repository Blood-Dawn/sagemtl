"""
FanMTL adapter for SageCrawler

Handles URLs from fanmtl.com
"""

import re
from typing import List
from urllib.parse import urlparse, urljoin

from ..core.models import SearchHit, NovelTOC, ChapterRef, ChapterContent
from ..core.fetch_httpx import PoliteFetcher
from ..core.cleaners import extract_chapter_content


class FanMTLAdapter:
    """Adapter for FanMTL site"""

    def __init__(self, fetcher: PoliteFetcher):
        self.fetcher = fetcher
        self.base_url = "https://www.fanmtl.com"

    @property
    def name(self) -> str:
        return "fanmtl"

    def can_handle(self, url: str) -> bool:
        """Check if URL is from FanMTL"""
        parsed = urlparse(url)
        return 'fanmtl.com' in parsed.netloc

    async def search(self, query: str, limit: int = 20) -> List[SearchHit]:
        """
        Search FanMTL for novels.

        Note: This is a placeholder. Full implementation would require
        inspecting FanMTL's search page structure.
        """
        # TODO: Implement actual search by fetching search results page
        # For now, return empty list
        return []

    async def get_toc(self, url: str) -> NovelTOC:
        """
        Get table of contents from a FanMTL novel page.

        Args:
            url: Novel page URL (e.g., https://www.fanmtl.com/novel/ke408329.html)

        Returns:
            Novel TOC with chapters
        """
        # Fetch novel page
        response = await self.fetcher.fetch(url)
        html = response.text

        # Extract title
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        title = title_match.group(1).strip() if title_match else "Unknown Novel"

        # Extract author
        author_match = re.search(r'<span[^>]*>Author[^<]*</span>\s*<a[^>]*>([^<]+)</a>', html, re.IGNORECASE)
        author = author_match.group(1).strip() if author_match else "Unknown Author"

        # Extract description
        desc_match = re.search(r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.+?)</div>', html, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else None

        # Extract cover URL
        cover_match = re.search(r'<img[^>]+src="([^"]+)"[^>]*class="[^"]*cover[^"]*"', html)
        if not cover_match:
            cover_match = re.search(r'<img[^>]+class="[^"]*cover[^"]*"[^>]*src="([^"]+)"', html)
        cover_url = urljoin(url, cover_match.group(1)) if cover_match else None

        # Extract chapter list
        # FanMTL typically has chapter links in a list or div
        chapter_pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
        chapter_matches = re.findall(chapter_pattern, html)

        chapters = []
        for i, (href, chapter_title) in enumerate(chapter_matches, 1):
            # Filter out non-chapter links (navigation, etc.)
            if 'chapter' in href.lower() or href.startswith('/'):
                chapter_url = urljoin(url, href)
                chapters.append(ChapterRef(
                    index=i,
                    title=chapter_title.strip(),
                    url=chapter_url
                ))

        # Build TOC
        toc = NovelTOC(
            title=title,
            author=author,
            url=url,
            cover_url=cover_url,
            description=description,
            chapters=chapters,
            status="Unknown"
        )

        return toc

    async def get_chapter(self, chapter: ChapterRef) -> ChapterContent:
        """
        Download a chapter from FanMTL.

        Args:
            chapter: Chapter reference

        Returns:
            Chapter content
        """
        # Fetch chapter page
        response = await self.fetcher.fetch(chapter.url)
        html = response.text

        # Extract chapter content
        # FanMTL typically has content in a div with class like "content" or "chapter-content"
        content_match = re.search(
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.+?)</div>',
            html,
            re.DOTALL | re.IGNORECASE
        )

        if not content_match:
            # Try alternative patterns
            content_match = re.search(
                r'<div[^>]*id="[^"]*content[^"]*"[^>]*>(.+?)</div>',
                html,
                re.DOTALL | re.IGNORECASE
            )

        if not content_match:
            raise ValueError(f"Could not find chapter content in {chapter.url}")

        raw_html = content_match.group(1)

        # Clean and extract content
        cleaned_html, plain_text, images = extract_chapter_content(raw_html, chapter.url)

        return ChapterContent(
            ref=chapter,
            html=cleaned_html,
            text=plain_text,
            images=images
        )
