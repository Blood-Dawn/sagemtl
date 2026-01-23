"""
Royal Road adapter for SageCrawler

Handles URLs from royalroad.com - platform for original English web fiction
"""

import re
from typing import List, Optional
from urllib.parse import urlparse, urljoin, quote_plus
from datetime import datetime

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
class RoyalRoadAdapter:
    """Adapter for Royal Road site - royalroad.com

    Royal Road hosts primarily original English web fiction, including LitRPG,
    progression fantasy, and other web novel genres.
    """

    @classmethod
    def get_info(cls) -> AdapterInfo:
        return AdapterInfo(
            name="royalroad",
            display_name="Royal Road",
            base_url="https://www.royalroad.com",
            supported_domains=["royalroad.com", "www.royalroad.com"],
            capabilities=SiteCapability.SEARCH | SiteCapability.DIRECT_URL | SiteCapability.VOLUMES,
            description="Platform for original English web fiction - LitRPG, progression fantasy, etc.",
            rate_limit=0.5
        )

    def __init__(self, fetcher: Optional[PoliteFetcher] = None):
        self.fetcher = fetcher
        self.base_url = "https://www.royalroad.com"

    @property
    def name(self) -> str:
        return "royalroad"

    def can_handle(self, url: str) -> bool:
        """Check if URL is from Royal Road"""
        parsed = urlparse(url)
        return 'royalroad.com' in parsed.netloc.lower()

    async def search(self, query: str, limit: int = 20) -> List[SearchHit]:
        """
        Search Royal Road for fictions.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of search hits
        """
        if not self.fetcher:
            return []

        # Royal Road search URL
        search_url = f"{self.base_url}/fictions/search?title={quote_plus(query)}"

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

        # Find fiction list items - Royal Road specific selectors
        novel_items = soup.select('.fiction-list-item, .search-item, [data-fiction-id]')

        for item in novel_items[:limit]:
            try:
                # Extract link
                link = item.select_one('a[href*="/fiction/"]')
                if not link:
                    continue

                href = link.get('href', '')
                url = urljoin(self.base_url, href)

                # Extract title
                title_elem = item.select_one('.fiction-title a, h2 a, .title a')
                title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)

                # Extract author
                author_elem = item.select_one('.author, a[href*="/user/profile/"]')
                author = author_elem.get_text(strip=True) if author_elem else "Unknown"

                # Extract cover
                cover_elem = item.select_one('img.cover, img[src*="cover"]')
                cover_url = None
                if cover_elem:
                    cover_url = cover_elem.get('src') or cover_elem.get('data-src')
                    if cover_url:
                        cover_url = urljoin(self.base_url, cover_url)

                # Extract stats
                stats_elem = item.select_one('.stats, .fiction-stats')
                chapter_count = None
                page_count = None
                if stats_elem:
                    text = stats_elem.get_text()
                    ch_match = re.search(r'(\d+)\s*(?:chapters?|ch)', text, re.IGNORECASE)
                    if ch_match:
                        chapter_count = int(ch_match.group(1))
                    page_match = re.search(r'([\d,]+)\s*pages?', text, re.IGNORECASE)
                    if page_match:
                        page_count = int(page_match.group(1).replace(',', ''))

                # Extract rating
                rating_elem = item.select_one('.star, .rating, [data-score]')
                rating = None
                if rating_elem:
                    rating_attr = rating_elem.get('data-score') or rating_elem.get('title')
                    if rating_attr:
                        match = re.search(r'([\d.]+)', str(rating_attr))
                        if match:
                            rating = float(match.group(1))

                # Extract tags
                tags = []
                tag_elems = item.select('.tags a, .tag, .fiction-tags span')
                for tag in tag_elems[:5]:
                    tags.append(tag.get_text(strip=True))

                # Extract status
                status = None
                status_elem = item.select_one('.status, .completion-status')
                if status_elem:
                    status_text = status_elem.get_text(strip=True).lower()
                    if 'complete' in status_text:
                        status = "Completed"
                    elif 'ongoing' in status_text or 'hiatus' not in status_text:
                        status = "Ongoing"
                    elif 'hiatus' in status_text:
                        status = "Hiatus"
                    elif 'dropped' in status_text:
                        status = "Dropped"

                results.append(SearchHit(
                    title=title,
                    author=author,
                    url=url,
                    source="royalroad",
                    cover_url=cover_url,
                    chapter_count=chapter_count,
                    rating=rating,
                    status=status,
                    genres=tags if tags else None
                ))

            except Exception:
                continue

        return results

    def _parse_search_regex(self, html: str, limit: int) -> List[SearchHit]:
        """Fallback search parsing with regex"""
        results = []

        # Find fiction links
        pattern = r'<a[^>]+href="(/fiction/\d+/[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        seen_urls = set()
        for href, title in matches:
            if len(results) >= limit:
                break

            url = urljoin(self.base_url, href)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Clean title
            title = title.strip()
            if len(title) < 3 or title.lower() in ['read', 'more', 'next', 'prev']:
                continue

            results.append(SearchHit(
                title=title,
                author="Unknown",
                url=url,
                source="royalroad"
            ))

        return results

    async def get_toc(self, url: str) -> NovelTOC:
        """
        Get table of contents from a Royal Road fiction page.

        Args:
            url: Fiction page URL

        Returns:
            Novel TOC with chapters
        """
        if not self.fetcher:
            raise ValueError("Fetcher not provided")

        # Fetch fiction page
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
        title_elem = soup.select_one('h1.font-white, h1[property="name"], .fic-title h1')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Novel"

        # Extract author
        author = "Unknown Author"
        author_elem = soup.select_one('a[href*="/user/profile/"], .author-name, h4 a')
        if author_elem:
            author = author_elem.get_text(strip=True)

        # Extract description
        description = None
        desc_elem = soup.select_one('.description, .fiction-info .margin-bottom-10, [property="description"]')
        if desc_elem:
            description = desc_elem.get_text(strip=True)

        # Extract cover URL
        cover_url = None
        cover_elem = soup.select_one('img.fic-cover, img.thumbnail, .cover-art-container img')
        if cover_elem:
            cover_url = cover_elem.get('src') or cover_elem.get('data-src')
            if cover_url:
                cover_url = urljoin(url, cover_url)

        # Extract stats
        total_pages = None
        total_words = None
        stats_elems = soup.select('.fiction-stats li, .stats li')
        for stat in stats_elems:
            text = stat.get_text().lower()
            if 'page' in text:
                match = re.search(r'([\d,]+)', text)
                if match:
                    total_pages = int(match.group(1).replace(',', ''))
            elif 'word' in text:
                match = re.search(r'([\d,]+)', text)
                if match:
                    total_words = int(match.group(1).replace(',', ''))

        # Extract chapter list
        chapters = []
        volumes = []
        current_volume = None
        volume_index = 0

        # Royal Road chapter table
        chapter_table = soup.select_one('#chapters, .chapter-list, table.table')

        if chapter_table:
            rows = chapter_table.select('tr[data-chapter-id], tbody tr, .chapter-row')

            for row in rows:
                try:
                    # Check for volume header
                    volume_header = row.select_one('.volume-header, th[colspan]')
                    if volume_header:
                        volume_index += 1
                        vol_title = volume_header.get_text(strip=True)
                        volumes.append({
                            'index': volume_index,
                            'title': vol_title,
                            'start_chapter': len(chapters) + 1
                        })
                        continue

                    # Get chapter link
                    link = row.select_one('a[href*="/chapter/"]')
                    if not link:
                        continue

                    href = link.get('href', '')
                    chapter_url = urljoin(url, href)
                    chapter_title = link.get_text(strip=True)

                    # Get release date
                    date_elem = row.select_one('time, .date, td:last-child')
                    release_date = None
                    if date_elem:
                        date_str = date_elem.get('datetime') or date_elem.get('title')
                        if date_str:
                            try:
                                release_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            except ValueError:
                                pass

                    chapters.append(ChapterRef(
                        index=len(chapters) + 1,
                        title=chapter_title or f"Chapter {len(chapters) + 1}",
                        url=chapter_url,
                        volume_index=volume_index if volume_index > 0 else None,
                        release_date=release_date
                    ))

                except Exception:
                    continue

        # Also check for chapters outside table
        if not chapters:
            chapter_links = soup.select('a[href*="/chapter/"]')
            seen_urls = set()

            for link in chapter_links:
                href = link.get('href', '')
                if not href or '/chapter/' not in href:
                    continue

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
        status_elem = soup.select_one('.fiction-status, .label-default, [class*="status"]')
        if status_elem:
            status_text = status_elem.get_text(strip=True).lower()
            if 'complete' in status_text:
                status = "Completed"
            elif 'ongoing' in status_text:
                status = "Ongoing"
            elif 'hiatus' in status_text:
                status = "Hiatus"
            elif 'dropped' in status_text:
                status = "Dropped"
            elif 'stub' in status_text:
                status = "Stub"

        # Extract genres/tags
        genres = []
        genre_elems = soup.select('.tags a, .fiction-tags a, .tag')
        for g in genre_elems[:15]:
            tag_text = g.get_text(strip=True)
            if tag_text and len(tag_text) > 1:
                genres.append(tag_text)

        # Extract rating
        rating = None
        rating_elem = soup.select_one('[data-rating], .star-rating, .score')
        if rating_elem:
            rating_val = rating_elem.get('data-rating') or rating_elem.get('title')
            if rating_val:
                match = re.search(r'([\d.]+)', str(rating_val))
                if match:
                    rating = float(match.group(1))

        return NovelTOC(
            title=title,
            author=author,
            url=url,
            cover_url=cover_url,
            description=description,
            chapters=chapters,
            volumes=volumes if volumes else None,
            status=status,
            genres=genres if genres else None,
            rating=rating,
            total_pages=total_pages,
            total_words=total_words
        )

    def _parse_toc_regex(self, html: str, url: str) -> NovelTOC:
        """Fallback TOC parsing with regex"""
        # Extract title
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        title = title_match.group(1).strip() if title_match else "Unknown Novel"

        # Extract author
        author_match = re.search(r'<a[^>]+href="/user/profile/\d+"[^>]*>([^<]+)</a>', html)
        author = author_match.group(1).strip() if author_match else "Unknown Author"

        # Extract description
        desc_match = re.search(r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.+?)</div>', html, re.DOTALL)
        description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip() if desc_match else None

        # Extract chapter list
        chapter_pattern = r'<a[^>]+href="(/fiction/\d+/[^/]+/chapter/\d+[^"]*)"[^>]*>([^<]+)</a>'
        chapter_matches = re.findall(chapter_pattern, html)

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
            description=description,
            chapters=chapters,
            status="Unknown"
        )

    async def get_chapter(self, chapter: ChapterRef) -> ChapterContent:
        """
        Download a chapter from Royal Road.

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
                        'footer', '.comments', '.sidebar', '.author-note-portlet',
                        '.donate-button', '.pagination', '.nav-buttons']:
            for elem in soup.select(selector):
                elem.decompose()

        # Try different content selectors - Royal Road specific
        content_selectors = [
            '.chapter-content',
            '.chapter-inner',
            '.chapter-text',
            '#chapter-content',
            '.fiction-body',
            '.portlet-body'
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
        note_elems = content_elem.select('.author-note, .authors-note, .note')
        for note in note_elems:
            note_text = note.get_text(strip=True)
            if note_text:
                author_notes.append(note_text)
            note.decompose()  # Remove from content

        raw_html = str(content_elem)

        # Clean and extract content
        cleaned_html, plain_text, images = extract_chapter_content(raw_html, chapter.url)

        # Extract chapter title from page (might be more accurate)
        title_elem = soup.select_one('h1, .chapter-title')
        actual_title = title_elem.get_text(strip=True) if title_elem else chapter.title

        # Extract next/prev chapter links
        next_chapter = None
        prev_chapter = None

        nav_links = soup.select('.nav-buttons a, .chapter-nav a, .pagination a')
        for link in nav_links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            if 'next' in text or '→' in link.get_text():
                next_chapter = urljoin(chapter.url, href)
            elif 'prev' in text or '←' in link.get_text():
                prev_chapter = urljoin(chapter.url, href)

        return ChapterContent(
            ref=ChapterRef(
                index=chapter.index,
                title=actual_title,
                url=chapter.url,
                volume_index=chapter.volume_index if hasattr(chapter, 'volume_index') else None
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
            r'<div[^>]*class="[^"]*chapter-content[^"]*"[^>]*>(.+?)</div>',
            r'<div[^>]*class="[^"]*chapter-inner[^"]*"[^>]*>(.+?)</div>',
            r'<div[^>]*class="[^"]*portlet-body[^"]*"[^>]*>(.+?)</div>',
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
