"""
FanMTL adapter for SageCrawler

Handles URLs from fanmtl.com - a machine translation aggregator for web novels
"""

import re
from typing import List, Optional
from urllib.parse import urlparse, urljoin, quote_plus

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from ..core.models import SearchHit, NovelTOC, ChapterRef, ChapterContent
from ..core.fetch_httpx import PoliteFetcher
from ..core.cleaners import extract_chapter_content
from ..core.adapter_base import AdapterInfo, SiteCapability, register_adapter


@register_adapter
class FanMTLAdapter:
    """Adapter for FanMTL site - fanmtl.com"""

    @classmethod
    def get_info(cls) -> AdapterInfo:
        return AdapterInfo(
            name="fanmtl",
            display_name="FanMTL",
            base_url="https://www.fanmtl.com",
            supported_domains=["fanmtl.com", "www.fanmtl.com"],
            capabilities=SiteCapability.SEARCH | SiteCapability.DIRECT_URL | SiteCapability.VOLUMES,
            description="Machine translation aggregator for Chinese web novels",
            rate_limit=0.5
        )

    def __init__(self, fetcher: Optional[PoliteFetcher] = None):
        self.fetcher = fetcher
        self.base_url = "https://www.fanmtl.com"

    @property
    def name(self) -> str:
        return "fanmtl"

    def can_handle(self, url: str) -> bool:
        """Check if URL is from FanMTL"""
        parsed = urlparse(url)
        return 'fanmtl.com' in parsed.netloc.lower()

    async def search(self, query: str, limit: int = 20) -> List[SearchHit]:
        """
        Search FanMTL for novels.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of search hits
        """
        if not self.fetcher:
            return []

        search_url = f"{self.base_url}/search?keyword={quote_plus(query)}"

        try:
            response = await self.fetcher.fetch(search_url)
            html = response.text

            if HAS_BS4:
                return self._parse_search_bs4(html, limit)
            else:
                return self._parse_search_regex(html, limit)

        except Exception as e:
            print(f"Search failed: {e}")
            return []

    def _parse_search_bs4(self, html: str, limit: int) -> List[SearchHit]:
        """Parse search results using BeautifulSoup"""
        soup = BeautifulSoup(html, 'lxml')
        results = []

        # Find novel cards in search results
        novel_items = soup.select('.novel-item, .search-result-item, .book-item, .novel-card')

        for item in novel_items[:limit]:
            try:
                # Extract link
                link = item.select_one('a[href*="/novel/"]')
                if not link:
                    continue

                href = link.get('href', '')
                url = urljoin(self.base_url, href)

                # Extract title
                title_elem = item.select_one('.novel-title, .title, h3, h4')
                title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)

                # Extract author
                author_elem = item.select_one('.author, .novel-author')
                author = author_elem.get_text(strip=True) if author_elem else "Unknown"

                # Extract cover
                cover_elem = item.select_one('img')
                cover_url = None
                if cover_elem:
                    cover_url = cover_elem.get('src') or cover_elem.get('data-src')
                    if cover_url:
                        cover_url = urljoin(self.base_url, cover_url)

                # Extract chapter count if available
                chapter_elem = item.select_one('.chapter-count, .chapters')
                chapter_count = None
                if chapter_elem:
                    text = chapter_elem.get_text()
                    match = re.search(r'(\d+)', text)
                    if match:
                        chapter_count = int(match.group(1))

                results.append(SearchHit(
                    title=title,
                    author=author,
                    url=url,
                    source="fanmtl",
                    cover_url=cover_url,
                    chapter_count=chapter_count
                ))

            except Exception:
                continue

        return results

    def _parse_search_regex(self, html: str, limit: int) -> List[SearchHit]:
        """Fallback search parsing with regex"""
        results = []
        pattern = r'<a[^>]+href="(/novel/[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        for href, title in matches[:limit]:
            url = urljoin(self.base_url, href)
            results.append(SearchHit(
                title=title.strip(),
                author="Unknown",
                url=url,
                source="fanmtl"
            ))

        return results

    async def get_toc(self, url: str) -> NovelTOC:
        """
        Get table of contents from a FanMTL novel page.

        Args:
            url: Novel page URL (e.g., https://www.fanmtl.com/novel/ke408329.html)

        Returns:
            Novel TOC with chapters
        """
        if not self.fetcher:
            raise ValueError("Fetcher not provided")

        # Fetch novel page
        response = await self.fetcher.fetch(url)
        html = response.text

        if HAS_BS4:
            return self._parse_toc_bs4(html, url)
        else:
            return self._parse_toc_regex(html, url)

    def _parse_toc_bs4(self, html: str, url: str) -> NovelTOC:
        """Parse TOC using BeautifulSoup"""
        soup = BeautifulSoup(html, 'lxml')

        # Extract title
        title_elem = soup.select_one('h1, .novel-title, .book-title')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Novel"

        # Extract author
        author = "Unknown Author"
        author_patterns = ['.author a', '.author', '.novel-author', '[itemprop="author"]']
        for pattern in author_patterns:
            try:
                author_elem = soup.select_one(pattern)
                if author_elem:
                    text = author_elem.get_text(strip=True)
                    text = re.sub(r'^(Author|作者)[:\s]*', '', text, flags=re.IGNORECASE)
                    if text:
                        author = text
                        break
            except Exception:
                continue

        # Extract description
        description = None
        desc_patterns = ['.description', '.summary', '.synopsis', '[itemprop="description"]']
        for pattern in desc_patterns:
            desc_elem = soup.select_one(pattern)
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                break

        # Extract cover URL
        cover_url = None
        cover_patterns = ['img.cover', '.novel-cover img', '.book-cover img', '[itemprop="image"]']
        for pattern in cover_patterns:
            cover_elem = soup.select_one(pattern)
            if cover_elem:
                cover_url = cover_elem.get('src') or cover_elem.get('data-src')
                if cover_url:
                    cover_url = urljoin(url, cover_url)
                    break

        # Extract chapter list
        chapters = []
        volumes = []

        # Try different chapter list patterns
        chapter_list = soup.select('.chapter-list a, .chapters-list a, #chapter-list a, .list-chapter a')

        if not chapter_list:
            chapter_list = soup.select('a[href*="chapter"], a[href*="/novel/"][href*=".html"]')

        chapter_index = 0
        for elem in chapter_list:
            href = elem.get('href', '')
            if not href or href == '#':
                continue

            if any(skip in href.lower() for skip in ['login', 'register', 'search', 'category']):
                continue

            chapter_index += 1
            chapter_url = urljoin(url, href)
            chapter_title = elem.get_text(strip=True)

            if not chapter_title:
                chapter_title = f"Chapter {chapter_index}"

            chapters.append(ChapterRef(
                index=chapter_index,
                title=chapter_title,
                url=chapter_url
            ))

        # Extract status
        status = "Unknown"
        status_elem = soup.select_one('.status, .novel-status')
        if status_elem:
            status_text = status_elem.get_text(strip=True).lower()
            if 'complete' in status_text:
                status = "Completed"
            elif 'ongoing' in status_text:
                status = "Ongoing"
            elif 'hiatus' in status_text:
                status = "Hiatus"

        return NovelTOC(
            title=title,
            author=author,
            url=url,
            cover_url=cover_url,
            description=description,
            chapters=chapters,
            volumes=volumes,
            status=status
        )

    def _parse_toc_regex(self, html: str, url: str) -> NovelTOC:
        """Fallback TOC parsing with regex"""
        # Extract title
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        title = title_match.group(1).strip() if title_match else "Unknown Novel"

        # Extract author
        author_match = re.search(r'Author[^<]*</span>\s*<a[^>]*>([^<]+)</a>', html, re.IGNORECASE)
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
        chapter_pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
        chapter_matches = re.findall(chapter_pattern, html)

        chapters = []
        chapter_index = 0
        for href, chapter_title in chapter_matches:
            if 'chapter' in href.lower() or (href.startswith('/') and 'novel' in href):
                chapter_index += 1
                chapter_url = urljoin(url, href)
                chapters.append(ChapterRef(
                    index=chapter_index,
                    title=chapter_title.strip(),
                    url=chapter_url
                ))

        return NovelTOC(
            title=title,
            author=author,
            url=url,
            cover_url=cover_url,
            description=description,
            chapters=chapters,
            status="Unknown"
        )

    async def get_chapter(self, chapter: ChapterRef) -> ChapterContent:
        """
        Download a chapter from FanMTL.

        Args:
            chapter: Chapter reference

        Returns:
            Chapter content
        """
        if not self.fetcher:
            raise ValueError("Fetcher not provided")

        # Fetch chapter page
        response = await self.fetcher.fetch(chapter.url)
        html = response.text

        if HAS_BS4:
            return self._parse_chapter_bs4(html, chapter)
        else:
            return self._parse_chapter_regex(html, chapter)

    def _parse_chapter_bs4(self, html: str, chapter: ChapterRef) -> ChapterContent:
        """Parse chapter using BeautifulSoup"""
        soup = BeautifulSoup(html, 'lxml')

        # Remove unwanted elements
        for selector in ['script', 'style', '.ads', '.advertisement', 'nav', 'header', 'footer', '.comments']:
            for elem in soup.select(selector):
                elem.decompose()

        # Try different content selectors
        content_selectors = [
            '.chapter-content',
            '.content',
            '#chapter-content',
            '#content',
            '.reading-content',
            'article',
            '.entry-content'
        ]

        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break

        if not content_elem:
            raise ValueError(f"Could not find chapter content in {chapter.url}")

        raw_html = str(content_elem)

        # Clean and extract content
        cleaned_html, plain_text, images = extract_chapter_content(raw_html, chapter.url)

        return ChapterContent(
            ref=chapter,
            html=cleaned_html,
            text=plain_text,
            images=images
        )

    def _parse_chapter_regex(self, html: str, chapter: ChapterRef) -> ChapterContent:
        """Fallback chapter parsing with regex"""
        content_match = re.search(
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.+?)</div>',
            html,
            re.DOTALL | re.IGNORECASE
        )

        if not content_match:
            content_match = re.search(
                r'<div[^>]*id="[^"]*content[^"]*"[^>]*>(.+?)</div>',
                html,
                re.DOTALL | re.IGNORECASE
            )

        if not content_match:
            raise ValueError(f"Could not find chapter content in {chapter.url}")

        raw_html = content_match.group(1)
        cleaned_html, plain_text, images = extract_chapter_content(raw_html, chapter.url)

        return ChapterContent(
            ref=chapter,
            html=cleaned_html,
            text=plain_text,
            images=images
        )
