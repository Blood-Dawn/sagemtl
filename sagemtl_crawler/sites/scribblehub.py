"""
ScribbleHub adapter for SageCrawler

Handles URLs from scribblehub.com - platform for original web fiction
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
class ScribbleHubAdapter:
    """Adapter for ScribbleHub site - scribblehub.com

    ScribbleHub is a platform for original web fiction similar to Royal Road,
    with a focus on various genres including isekai, fantasy, and slice of life.
    """

    @classmethod
    def get_info(cls) -> AdapterInfo:
        return AdapterInfo(
            name="scribblehub",
            display_name="ScribbleHub",
            base_url="https://www.scribblehub.com",
            supported_domains=["scribblehub.com", "www.scribblehub.com"],
            capabilities=SiteCapability.SEARCH | SiteCapability.DIRECT_URL,
            description="Platform for original web fiction - isekai, fantasy, slice of life",
            rate_limit=0.5
        )

    def __init__(self, fetcher: Optional[PoliteFetcher] = None):
        self.fetcher = fetcher
        self.base_url = "https://www.scribblehub.com"

    @property
    def name(self) -> str:
        return "scribblehub"

    def can_handle(self, url: str) -> bool:
        """Check if URL is from ScribbleHub"""
        parsed = urlparse(url)
        return 'scribblehub.com' in parsed.netloc.lower()

    async def search(self, query: str, limit: int = 20) -> List[SearchHit]:
        """
        Search ScribbleHub for series.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of search hits
        """
        if not self.fetcher:
            return []

        # ScribbleHub search URL
        search_url = f"{self.base_url}/?s={quote_plus(query)}&post_type=fictionposts"

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

        # Find search result items
        novel_items = soup.select('.search_main_box, .fic_row, .search-item')

        for item in novel_items[:limit]:
            try:
                # Extract link
                link = item.select_one('a[href*="/series/"], a.search_title')
                if not link:
                    continue

                href = link.get('href', '')
                url = urljoin(self.base_url, href)

                # Extract title
                title_elem = item.select_one('.search_title, .fic_title, h4 a')
                title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)

                # Extract author
                author_elem = item.select_one('.author, a[href*="/profile/"]')
                author = author_elem.get_text(strip=True) if author_elem else "Unknown"

                # Extract cover
                cover_elem = item.select_one('img')
                cover_url = None
                if cover_elem:
                    cover_url = cover_elem.get('src') or cover_elem.get('data-src')
                    if cover_url:
                        cover_url = urljoin(self.base_url, cover_url)

                # Extract rating
                rating_elem = item.select_one('.rating, .score')
                rating = None
                if rating_elem:
                    rating_text = rating_elem.get_text()
                    match = re.search(r'([\d.]+)', rating_text)
                    if match:
                        rating = float(match.group(1))

                # Extract genres
                genres = []
                genre_elems = item.select('.fic_genre a, .genre a, .tags a')
                for g in genre_elems[:5]:
                    genres.append(g.get_text(strip=True))

                # Extract chapter count
                stats_elem = item.select_one('.stats, .fic_stats')
                chapter_count = None
                if stats_elem:
                    text = stats_elem.get_text()
                    match = re.search(r'(\d+)\s*(?:chapters?|ch)', text, re.IGNORECASE)
                    if match:
                        chapter_count = int(match.group(1))

                results.append(SearchHit(
                    title=title,
                    author=author,
                    url=url,
                    source="scribblehub",
                    cover_url=cover_url,
                    chapter_count=chapter_count,
                    rating=rating,
                    genres=genres if genres else None
                ))

            except Exception:
                continue

        return results

    def _parse_search_regex(self, html: str, limit: int) -> List[SearchHit]:
        """Fallback search parsing with regex"""
        results = []

        # Find series links
        pattern = r'<a[^>]+href="(https?://[^"]*scribblehub\.com/series/[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        seen_urls = set()
        for url, title in matches:
            if len(results) >= limit:
                break
            if url in seen_urls:
                continue
            seen_urls.add(url)

            results.append(SearchHit(
                title=title.strip(),
                author="Unknown",
                url=url,
                source="scribblehub"
            ))

        return results

    async def get_toc(self, url: str) -> NovelTOC:
        """
        Get table of contents from a ScribbleHub series page.

        Args:
            url: Series page URL

        Returns:
            Novel TOC with chapters
        """
        if not self.fetcher:
            raise ValueError("Fetcher not provided")

        # Fetch series page
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
        title_elem = soup.select_one('.fic_title, h1.entry-title, .series-title')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Novel"

        # Extract author
        author = "Unknown Author"
        author_elem = soup.select_one('.auth_name_fic a, a[href*="/profile/"]')
        if author_elem:
            author = author_elem.get_text(strip=True)

        # Extract description
        description = None
        desc_elem = soup.select_one('.wi_fic_desc, .fic_row_desc, .description')
        if desc_elem:
            description = desc_elem.get_text(strip=True)

        # Extract cover URL
        cover_url = None
        cover_elem = soup.select_one('.fic_image img, .novel_cover img')
        if cover_elem:
            cover_url = cover_elem.get('src') or cover_elem.get('data-src')
            if cover_url:
                cover_url = urljoin(url, cover_url)

        # Extract chapter list
        chapters = []

        # ScribbleHub chapter list is often loaded via AJAX, but also has initial chapters
        chapter_list = soup.select('.toc_a, .chp-release a, a[href*="/read/"]')

        seen_urls = set()
        for elem in chapter_list:
            href = elem.get('href', '')
            if not href or href in seen_urls:
                continue

            chapter_url = urljoin(url, href)
            if chapter_url in seen_urls:
                continue
            seen_urls.add(chapter_url)

            chapter_title = elem.get_text(strip=True)

            # Skip if title is too short or looks like navigation
            if not chapter_title or len(chapter_title) < 2:
                continue
            if chapter_title.lower() in ['next', 'prev', 'previous', 'read']:
                continue

            chapters.append(ChapterRef(
                index=len(chapters) + 1,
                title=chapter_title,
                url=chapter_url
            ))

        # Also try to get chapters from the TOC table
        toc_rows = soup.select('.toc_ol li, .toc_w li, #toc li')
        for row in toc_rows:
            link = row.select_one('a')
            if not link:
                continue

            href = link.get('href', '')
            chapter_url = urljoin(url, href)

            if chapter_url in seen_urls:
                continue
            seen_urls.add(chapter_url)

            chapter_title = link.get_text(strip=True)
            if not chapter_title or len(chapter_title) < 2:
                continue

            chapters.append(ChapterRef(
                index=len(chapters) + 1,
                title=chapter_title,
                url=chapter_url
            ))

        # Extract status
        status = "Unknown"
        status_elem = soup.select_one('.widget_fic_similar span, .status')
        if status_elem:
            status_text = status_elem.get_text(strip=True).lower()
            if 'complete' in status_text:
                status = "Completed"
            elif 'ongoing' in status_text:
                status = "Ongoing"
            elif 'hiatus' in status_text:
                status = "Hiatus"

        # Extract genres
        genres = []
        genre_elems = soup.select('.fic_genre a, .wi_fic_genre a, .genre-tag')
        for g in genre_elems[:15]:
            genres.append(g.get_text(strip=True))

        # Extract rating
        rating = None
        rating_elem = soup.select_one('.fic_stats .rating, [property="ratingValue"]')
        if rating_elem:
            rating_text = rating_elem.get_text() if rating_elem.name != 'meta' else rating_elem.get('content', '')
            match = re.search(r'([\d.]+)', rating_text)
            if match:
                rating = float(match.group(1))

        return NovelTOC(
            title=title,
            author=author,
            url=url,
            cover_url=cover_url,
            description=description,
            chapters=chapters,
            status=status,
            genres=genres if genres else None,
            rating=rating
        )

    def _parse_toc_regex(self, html: str, url: str) -> NovelTOC:
        """Fallback TOC parsing with regex"""
        # Extract title
        title_match = re.search(r'<div[^>]*class="[^"]*fic_title[^"]*"[^>]*>([^<]+)</div>', html)
        if not title_match:
            title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        title = title_match.group(1).strip() if title_match else "Unknown Novel"

        # Extract author
        author_match = re.search(r'<a[^>]+href="[^"]*scribblehub\.com/profile/[^"]*"[^>]*>([^<]+)</a>', html)
        author = author_match.group(1).strip() if author_match else "Unknown Author"

        # Extract description
        desc_match = re.search(r'<div[^>]*class="[^"]*wi_fic_desc[^"]*"[^>]*>(.+?)</div>', html, re.DOTALL)
        description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip() if desc_match else None

        # Extract chapters
        chapter_pattern = r'<a[^>]+href="([^"]*scribblehub\.com/read/[^"]+)"[^>]*>([^<]+)</a>'
        chapter_matches = re.findall(chapter_pattern, html)

        chapters = []
        seen_urls = set()
        for href, chapter_title in chapter_matches:
            if href in seen_urls:
                continue
            seen_urls.add(href)

            chapters.append(ChapterRef(
                index=len(chapters) + 1,
                title=chapter_title.strip(),
                url=href
            ))

        return NovelTOC(
            title=title,
            author=author,
            url=url,
            description=description,
            chapters=chapters,
            status="Unknown"
        )

    async def get_chapter(self, chapter: ChapterRef) -> ChapterContent:
        """
        Download a chapter from ScribbleHub.

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
                        'footer', '.comments', '.sidebar', '.author-note', '.wi_authornotes']:
            for elem in soup.select(selector):
                elem.decompose()

        # Try different content selectors - ScribbleHub specific
        content_selectors = [
            '.chp_raw',
            '#chp_raw',
            '.chapter-content',
            '.entry-content',
            '#chapter-content'
        ]

        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break

        if not content_elem:
            raise ValueError(f"Could not find chapter content in {chapter.url}")

        # Handle author notes separately
        author_notes = []
        note_elems = soup.select('.wi_authornotes, .author-note')
        for note in note_elems:
            note_text = note.get_text(strip=True)
            if note_text:
                author_notes.append(note_text)

        raw_html = str(content_elem)

        # Clean and extract content
        cleaned_html, plain_text, images = extract_chapter_content(raw_html, chapter.url)

        # Extract chapter title from page
        title_elem = soup.select_one('.chapter-title, h1.entry-title')
        actual_title = title_elem.get_text(strip=True) if title_elem else chapter.title

        # Extract next/prev chapter links
        next_chapter = None
        prev_chapter = None

        nav_links = soup.select('.chapter-nav a, .wi_nav_pag a')
        for link in nav_links:
            href = link.get('href', '')
            classes = link.get('class', [])
            text = link.get_text(strip=True).lower()

            if 'btn_next' in classes or 'next' in text or '→' in link.get_text():
                next_chapter = urljoin(chapter.url, href)
            elif 'btn_prev' in classes or 'prev' in text or '←' in link.get_text():
                prev_chapter = urljoin(chapter.url, href)

        return ChapterContent(
            ref=ChapterRef(
                index=chapter.index,
                title=actual_title,
                url=chapter.url
            ),
            html=cleaned_html,
            text=plain_text,
            images=images,
            next_url=next_chapter,
            prev_url=prev_chapter,
            author_notes=author_notes if author_notes else None
        )

    def _parse_chapter_regex(self, html: str, chapter: ChapterRef) -> ChapterContent:
        """Fallback chapter parsing with regex"""
        # Try multiple content patterns
        content_patterns = [
            r'<div[^>]*id="chp_raw"[^>]*>(.+?)</div>',
            r'<div[^>]*class="[^"]*chp_raw[^"]*"[^>]*>(.+?)</div>',
            r'<div[^>]*class="[^"]*chapter-content[^"]*"[^>]*>(.+?)</div>',
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
