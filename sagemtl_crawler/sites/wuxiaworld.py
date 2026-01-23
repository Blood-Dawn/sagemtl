"""
Wuxiaworld adapter for SageCrawler

Handles URLs from wuxiaworld.com - major translation site for Chinese web novels
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
class WuxiaworldAdapter:
    """Adapter for Wuxiaworld site - wuxiaworld.com"""

    @classmethod
    def get_info(cls) -> AdapterInfo:
        return AdapterInfo(
            name="wuxiaworld",
            display_name="Wuxiaworld",
            base_url="https://www.wuxiaworld.com",
            supported_domains=["wuxiaworld.com", "www.wuxiaworld.com"],
            capabilities=SiteCapability.SEARCH | SiteCapability.DIRECT_URL | SiteCapability.VOLUMES | SiteCapability.LOGIN,
            description="Major translation site for Chinese web novels with premium content",
            requires_login=False,  # Some content is free
            rate_limit=1.0  # Be more conservative with rate limiting
        )

    def __init__(self, fetcher: Optional[PoliteFetcher] = None):
        self.fetcher = fetcher
        self.base_url = "https://www.wuxiaworld.com"

    @property
    def name(self) -> str:
        return "wuxiaworld"

    def can_handle(self, url: str) -> bool:
        """Check if URL is from Wuxiaworld"""
        parsed = urlparse(url)
        return 'wuxiaworld.com' in parsed.netloc.lower()

    async def search(self, query: str, limit: int = 20) -> List[SearchHit]:
        """
        Search Wuxiaworld for novels.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of search hits
        """
        if not self.fetcher:
            return []

        # Wuxiaworld uses a different search endpoint
        search_url = f"{self.base_url}/search?query={quote_plus(query)}"

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

        # Find novel cards in search results - Wuxiaworld specific selectors
        novel_items = soup.select('.search-result-item, .novel-item, .book-card, [data-novel-id]')

        for item in novel_items[:limit]:
            try:
                # Extract link
                link = item.select_one('a[href*="/novel/"]')
                if not link:
                    link = item.select_one('a')
                if not link:
                    continue

                href = link.get('href', '')
                url = urljoin(self.base_url, href)

                # Extract title
                title_elem = item.select_one('.novel-title, .title, h3, h4, .name')
                title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)

                # Extract author
                author_elem = item.select_one('.author, .novel-author, .writer')
                author = author_elem.get_text(strip=True) if author_elem else "Unknown"
                # Clean up author text
                author = re.sub(r'^(Author|By)[:\s]*', '', author, flags=re.IGNORECASE)

                # Extract cover
                cover_elem = item.select_one('img')
                cover_url = None
                if cover_elem:
                    cover_url = cover_elem.get('src') or cover_elem.get('data-src') or cover_elem.get('data-original')
                    if cover_url:
                        cover_url = urljoin(self.base_url, cover_url)

                # Extract chapter count if available
                chapter_elem = item.select_one('.chapter-count, .chapters, .stats')
                chapter_count = None
                if chapter_elem:
                    text = chapter_elem.get_text()
                    match = re.search(r'(\d+)\s*(?:chapters?|ch)', text, re.IGNORECASE)
                    if match:
                        chapter_count = int(match.group(1))

                # Extract status
                status_elem = item.select_one('.status, .novel-status')
                status = None
                if status_elem:
                    status = status_elem.get_text(strip=True)

                results.append(SearchHit(
                    title=title,
                    author=author,
                    url=url,
                    source="wuxiaworld",
                    cover_url=cover_url,
                    chapter_count=chapter_count,
                    status=status
                ))

            except Exception:
                continue

        return results

    def _parse_search_regex(self, html: str, limit: int) -> List[SearchHit]:
        """Fallback search parsing with regex"""
        results = []
        pattern = r'<a[^>]+href="(/novel/[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        seen_urls = set()
        for href, title in matches[:limit * 2]:  # Get more to filter duplicates
            url = urljoin(self.base_url, href)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            results.append(SearchHit(
                title=title.strip(),
                author="Unknown",
                url=url,
                source="wuxiaworld"
            ))

            if len(results) >= limit:
                break

        return results

    async def get_toc(self, url: str) -> NovelTOC:
        """
        Get table of contents from a Wuxiaworld novel page.

        Args:
            url: Novel page URL

        Returns:
            Novel TOC with chapters organized by volumes
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
        title_elem = soup.select_one('h1, .novel-title, .book-title, [itemprop="name"]')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Novel"

        # Extract author
        author = "Unknown Author"
        author_patterns = ['.author a', '.author', '.novel-author', '[itemprop="author"]', '.writer']
        for pattern in author_patterns:
            try:
                author_elem = soup.select_one(pattern)
                if author_elem:
                    text = author_elem.get_text(strip=True)
                    text = re.sub(r'^(Author|By|作者)[:\s]*', '', text, flags=re.IGNORECASE)
                    if text:
                        author = text
                        break
            except Exception:
                continue

        # Extract description
        description = None
        desc_patterns = ['.description', '.summary', '.synopsis', '[itemprop="description"]', '.novel-summary']
        for pattern in desc_patterns:
            desc_elem = soup.select_one(pattern)
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                break

        # Extract cover URL
        cover_url = None
        cover_patterns = ['img.cover', '.novel-cover img', '.book-cover img', '[itemprop="image"]', '.cover-image img']
        for pattern in cover_patterns:
            cover_elem = soup.select_one(pattern)
            if cover_elem:
                cover_url = cover_elem.get('src') or cover_elem.get('data-src') or cover_elem.get('data-original')
                if cover_url:
                    cover_url = urljoin(url, cover_url)
                    break

        # Extract chapter list with volume support
        chapters = []
        volumes = []
        current_volume = None
        volume_index = 0

        # Look for volume headers and chapter lists
        volume_containers = soup.select('.volume, .book, [data-volume-id], .chapter-group')

        if volume_containers:
            # Site has volume structure
            for vol_container in volume_containers:
                volume_index += 1
                vol_title_elem = vol_container.select_one('.volume-title, .book-title, h3, h4')
                vol_title = vol_title_elem.get_text(strip=True) if vol_title_elem else f"Volume {volume_index}"

                volumes.append({
                    'index': volume_index,
                    'title': vol_title,
                    'start_chapter': len(chapters) + 1
                })

                chapter_links = vol_container.select('a[href*="chapter"], a[href*="/c"]')
                for elem in chapter_links:
                    href = elem.get('href', '')
                    if not href or href == '#':
                        continue

                    chapter_url = urljoin(url, href)
                    chapter_title = elem.get_text(strip=True)

                    if not chapter_title:
                        chapter_title = f"Chapter {len(chapters) + 1}"

                    chapters.append(ChapterRef(
                        index=len(chapters) + 1,
                        title=chapter_title,
                        url=chapter_url,
                        volume_index=volume_index
                    ))
        else:
            # Flat chapter list
            chapter_list = soup.select('.chapter-list a, .chapters-list a, #chapter-list a, .toc a, [data-chapter-id] a')

            if not chapter_list:
                chapter_list = soup.select('a[href*="chapter"], a[href*="/c"]')

            for elem in chapter_list:
                href = elem.get('href', '')
                if not href or href == '#':
                    continue

                # Skip navigation links
                if any(skip in href.lower() for skip in ['login', 'register', 'search', 'category', 'genre']):
                    continue

                chapter_url = urljoin(url, href)
                chapter_title = elem.get_text(strip=True)

                if not chapter_title:
                    chapter_title = f"Chapter {len(chapters) + 1}"

                chapters.append(ChapterRef(
                    index=len(chapters) + 1,
                    title=chapter_title,
                    url=chapter_url
                ))

        # Extract status
        status = "Unknown"
        status_elem = soup.select_one('.status, .novel-status, [data-status]')
        if status_elem:
            status_text = status_elem.get_text(strip=True).lower()
            if 'complete' in status_text or 'finished' in status_text:
                status = "Completed"
            elif 'ongoing' in status_text or 'active' in status_text:
                status = "Ongoing"
            elif 'hiatus' in status_text:
                status = "Hiatus"
            elif 'dropped' in status_text:
                status = "Dropped"

        # Extract genres/tags
        genres = []
        genre_elems = soup.select('.genre a, .tag a, .tags a, [data-genre]')
        for g in genre_elems[:10]:  # Limit to 10 genres
            genres.append(g.get_text(strip=True))

        return NovelTOC(
            title=title,
            author=author,
            url=url,
            cover_url=cover_url,
            description=description,
            chapters=chapters,
            volumes=volumes if volumes else None,
            status=status,
            genres=genres if genres else None
        )

    def _parse_toc_regex(self, html: str, url: str) -> NovelTOC:
        """Fallback TOC parsing with regex"""
        # Extract title
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        title = title_match.group(1).strip() if title_match else "Unknown Novel"

        # Extract author
        author_match = re.search(r'(?:Author|By)[:\s]*</span>\s*<a[^>]*>([^<]+)</a>', html, re.IGNORECASE)
        if not author_match:
            author_match = re.search(r'(?:Author|By)[:\s]*([^<]+)</span>', html, re.IGNORECASE)
        author = author_match.group(1).strip() if author_match else "Unknown Author"

        # Extract description
        desc_match = re.search(r'<div[^>]*class="[^"]*(?:description|synopsis)[^"]*"[^>]*>(.+?)</div>', html, re.DOTALL)
        description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip() if desc_match else None

        # Extract cover URL
        cover_match = re.search(r'<img[^>]+(?:class="[^"]*cover[^"]*"|src="([^"]+)"[^>]*class="[^"]*cover)', html)
        cover_url = urljoin(url, cover_match.group(1)) if cover_match else None

        # Extract chapter list
        chapter_pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]*(?:chapter|ch)[^<]*)</a>'
        chapter_matches = re.findall(chapter_pattern, html, re.IGNORECASE)

        chapters = []
        seen_urls = set()
        for href, chapter_title in chapter_matches:
            chapter_url = urljoin(url, href)
            if chapter_url in seen_urls:
                continue
            seen_urls.add(chapter_url)

            chapters.append(ChapterRef(
                index=len(chapters) + 1,
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
        Download a chapter from Wuxiaworld.

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
        for selector in ['script', 'style', '.ads', '.advertisement', 'nav', 'header',
                        'footer', '.comments', '.sidebar', '.related', '.social-share']:
            for elem in soup.select(selector):
                elem.decompose()

        # Try different content selectors - Wuxiaworld specific
        content_selectors = [
            '.chapter-content',
            '.chapter-body',
            '#chapter-content',
            '.reading-content',
            '.content-text',
            '[data-chapter-content]',
            'article .content',
            '.entry-content'
        ]

        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break

        if not content_elem:
            # Try to find by looking for the largest text block
            all_divs = soup.find_all('div')
            max_text_len = 0
            for div in all_divs:
                text_len = len(div.get_text())
                if text_len > max_text_len and text_len > 500:  # Minimum content length
                    max_text_len = text_len
                    content_elem = div

        if not content_elem:
            raise ValueError(f"Could not find chapter content in {chapter.url}")

        raw_html = str(content_elem)

        # Clean and extract content
        cleaned_html, plain_text, images = extract_chapter_content(raw_html, chapter.url)

        # Extract next/prev chapter links
        next_chapter = None
        prev_chapter = None

        next_link = soup.select_one('a.next-chapter, a[rel="next"], .next a')
        if next_link:
            next_chapter = urljoin(chapter.url, next_link.get('href', ''))

        prev_link = soup.select_one('a.prev-chapter, a[rel="prev"], .prev a')
        if prev_link:
            prev_chapter = urljoin(chapter.url, prev_link.get('href', ''))

        return ChapterContent(
            ref=chapter,
            html=cleaned_html,
            text=plain_text,
            images=images,
            next_url=next_chapter,
            prev_url=prev_chapter
        )

    def _parse_chapter_regex(self, html: str, chapter: ChapterRef) -> ChapterContent:
        """Fallback chapter parsing with regex"""
        # Try multiple content patterns
        content_patterns = [
            r'<div[^>]*class="[^"]*chapter-content[^"]*"[^>]*>(.+?)</div>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.+?)</div>',
            r'<article[^>]*>(.+?)</article>',
        ]

        content_match = None
        for pattern in content_patterns:
            content_match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if content_match:
                break

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
