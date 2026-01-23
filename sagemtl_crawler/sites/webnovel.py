"""
Webnovel adapter for SageCrawler

Handles URLs from webnovel.com - QiDian English platform for web novels
"""

import re
import json
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
class WebnovelAdapter:
    """Adapter for Webnovel site - webnovel.com (QiDian English)"""

    @classmethod
    def get_info(cls) -> AdapterInfo:
        return AdapterInfo(
            name="webnovel",
            display_name="Webnovel",
            base_url="https://www.webnovel.com",
            supported_domains=["webnovel.com", "www.webnovel.com", "m.webnovel.com"],
            capabilities=SiteCapability.SEARCH | SiteCapability.DIRECT_URL | SiteCapability.VOLUMES | SiteCapability.LOGIN | SiteCapability.AJAX,
            description="QiDian English - Official platform for Chinese web novels",
            requires_login=False,  # Some chapters require login/payment
            rate_limit=1.0
        )

    def __init__(self, fetcher: Optional[PoliteFetcher] = None):
        self.fetcher = fetcher
        self.base_url = "https://www.webnovel.com"
        self.api_base = "https://www.webnovel.com/apiajax"

    @property
    def name(self) -> str:
        return "webnovel"

    def can_handle(self, url: str) -> bool:
        """Check if URL is from Webnovel"""
        parsed = urlparse(url)
        return 'webnovel.com' in parsed.netloc.lower()

    def _extract_book_id(self, url: str) -> Optional[str]:
        """Extract book ID from Webnovel URL"""
        # URLs can be like:
        # https://www.webnovel.com/book/12345678901234567
        # https://www.webnovel.com/book/novel-title_12345678901234567
        match = re.search(r'/book/(?:[^/]*_)?(\d+)', url)
        if match:
            return match.group(1)
        return None

    async def search(self, query: str, limit: int = 20) -> List[SearchHit]:
        """
        Search Webnovel for novels.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of search hits
        """
        if not self.fetcher:
            return []

        # Webnovel search page
        search_url = f"{self.base_url}/search?keywords={quote_plus(query)}"

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

        # Try to extract from embedded JSON first (Webnovel often uses this)
        script_tags = soup.find_all('script', type='application/json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if 'searchBooks' in str(data) or 'bookItems' in str(data):
                    # Navigate the JSON structure to find books
                    self._extract_from_json(data, results, limit)
                    if results:
                        return results[:limit]
            except (json.JSONDecodeError, TypeError):
                continue

        # Fallback to HTML parsing
        novel_items = soup.select('.search-result-item, .book-item, .novel-item, [data-book-id]')

        for item in novel_items[:limit]:
            try:
                # Extract link
                link = item.select_one('a[href*="/book/"]')
                if not link:
                    continue

                href = link.get('href', '')
                url = urljoin(self.base_url, href)

                # Extract title
                title_elem = item.select_one('.book-title, .title, h3, h4, .name')
                title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)

                # Extract author
                author_elem = item.select_one('.author, .author-name, [data-author]')
                author = author_elem.get_text(strip=True) if author_elem else "Unknown"

                # Extract cover
                cover_elem = item.select_one('img')
                cover_url = None
                if cover_elem:
                    cover_url = cover_elem.get('src') or cover_elem.get('data-src')
                    if cover_url:
                        cover_url = urljoin(self.base_url, cover_url)

                # Extract chapter count
                chapter_elem = item.select_one('.chapter-count, .chapters, [data-chapter-count]')
                chapter_count = None
                if chapter_elem:
                    text = chapter_elem.get_text()
                    match = re.search(r'(\d+)', text)
                    if match:
                        chapter_count = int(match.group(1))

                # Extract rating
                rating_elem = item.select_one('.rating, .score, [data-rating]')
                rating = None
                if rating_elem:
                    rating_text = rating_elem.get_text()
                    match = re.search(r'([\d.]+)', rating_text)
                    if match:
                        rating = float(match.group(1))

                results.append(SearchHit(
                    title=title,
                    author=author,
                    url=url,
                    source="webnovel",
                    cover_url=cover_url,
                    chapter_count=chapter_count,
                    rating=rating
                ))

            except Exception:
                continue

        return results

    def _extract_from_json(self, data: dict, results: List[SearchHit], limit: int):
        """Recursively extract book data from JSON structure"""
        if isinstance(data, dict):
            # Check if this is a book object
            if 'bookName' in data or 'name' in data:
                book_id = data.get('bookId') or data.get('id')
                title = data.get('bookName') or data.get('name', 'Unknown')
                author = data.get('authorName') or data.get('author', 'Unknown')
                cover = data.get('coverUrl') or data.get('cover')
                chapters = data.get('chapterCount') or data.get('totalChapter')

                if book_id:
                    url = f"{self.base_url}/book/{book_id}"
                    results.append(SearchHit(
                        title=title,
                        author=author,
                        url=url,
                        source="webnovel",
                        cover_url=cover,
                        chapter_count=int(chapters) if chapters else None
                    ))

            # Recursively search nested objects
            for value in data.values():
                if len(results) >= limit:
                    return
                self._extract_from_json(value, results, limit)

        elif isinstance(data, list):
            for item in data:
                if len(results) >= limit:
                    return
                self._extract_from_json(item, results, limit)

    def _parse_search_regex(self, html: str, limit: int) -> List[SearchHit]:
        """Fallback search parsing with regex"""
        results = []

        # Try to find book links
        pattern = r'<a[^>]+href="(/book/[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        seen_urls = set()
        for href, title in matches:
            if len(results) >= limit:
                break

            url = urljoin(self.base_url, href)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            results.append(SearchHit(
                title=title.strip(),
                author="Unknown",
                url=url,
                source="webnovel"
            ))

        return results

    async def get_toc(self, url: str) -> NovelTOC:
        """
        Get table of contents from a Webnovel novel page.

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

        # Try to extract from embedded JSON first
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and ('bookInfo' in script.string or '__NUXT__' in script.string):
                try:
                    # Extract JSON from script
                    json_match = re.search(r'(?:bookInfo|__NUXT__)\s*=\s*({.+?})\s*;?\s*(?:</script>|$)',
                                          script.string, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        toc = self._parse_toc_from_json(data, url)
                        if toc and toc.chapters:
                            return toc
                except (json.JSONDecodeError, TypeError):
                    continue

        # Fallback to HTML parsing
        # Extract title
        title_elem = soup.select_one('h1, .book-title, .novel-title, [data-book-name]')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Novel"

        # Extract author
        author = "Unknown Author"
        author_patterns = ['.author-name a', '.author a', '[data-author]', '.writer']
        for pattern in author_patterns:
            author_elem = soup.select_one(pattern)
            if author_elem:
                author = author_elem.get_text(strip=True)
                break

        # Extract description
        description = None
        desc_elem = soup.select_one('.description, .summary, .synopsis, [data-description]')
        if desc_elem:
            description = desc_elem.get_text(strip=True)

        # Extract cover URL
        cover_url = None
        cover_elem = soup.select_one('img.cover, .book-cover img, [data-cover]')
        if cover_elem:
            cover_url = cover_elem.get('src') or cover_elem.get('data-src')
            if cover_url:
                cover_url = urljoin(url, cover_url)

        # Extract chapter list
        chapters = []
        volumes = []

        # Look for volume structure
        volume_containers = soup.select('.volume, .book-volume, [data-volume-id]')

        if volume_containers:
            volume_index = 0
            for vol_container in volume_containers:
                volume_index += 1
                vol_title_elem = vol_container.select_one('.volume-title, .vol-title, h3')
                vol_title = vol_title_elem.get_text(strip=True) if vol_title_elem else f"Volume {volume_index}"

                volumes.append({
                    'index': volume_index,
                    'title': vol_title,
                    'start_chapter': len(chapters) + 1
                })

                chapter_links = vol_container.select('a[href*="/chapter/"], a[href*="/book/"]')
                for elem in chapter_links:
                    href = elem.get('href', '')
                    if not href or 'chapter' not in href.lower():
                        continue

                    chapter_url = urljoin(url, href)
                    chapter_title = elem.get_text(strip=True)

                    # Check if chapter is locked
                    is_locked = 'locked' in elem.get('class', []) or elem.select_one('.lock-icon')

                    chapters.append(ChapterRef(
                        index=len(chapters) + 1,
                        title=chapter_title or f"Chapter {len(chapters) + 1}",
                        url=chapter_url,
                        volume_index=volume_index,
                        is_locked=bool(is_locked)
                    ))
        else:
            # Flat chapter list
            chapter_list = soup.select('a[href*="/chapter/"], .chapter-item a, .toc a')

            for elem in chapter_list:
                href = elem.get('href', '')
                if not href:
                    continue

                chapter_url = urljoin(url, href)
                chapter_title = elem.get_text(strip=True)

                is_locked = 'locked' in elem.get('class', []) or elem.select_one('.lock-icon')

                chapters.append(ChapterRef(
                    index=len(chapters) + 1,
                    title=chapter_title or f"Chapter {len(chapters) + 1}",
                    url=chapter_url,
                    is_locked=bool(is_locked)
                ))

        # Extract status
        status = "Unknown"
        status_elem = soup.select_one('.status, [data-status], .book-status')
        if status_elem:
            status_text = status_elem.get_text(strip=True).lower()
            if 'complete' in status_text:
                status = "Completed"
            elif 'ongoing' in status_text:
                status = "Ongoing"

        # Extract genres
        genres = []
        genre_elems = soup.select('.genre a, .tag a, [data-genre]')
        for g in genre_elems[:10]:
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

    def _parse_toc_from_json(self, data: dict, url: str) -> Optional[NovelTOC]:
        """Parse TOC from JSON data structure"""
        try:
            # Navigate to book info
            book_info = None
            if 'bookInfo' in data:
                book_info = data['bookInfo']
            elif 'data' in data and 'bookInfo' in data['data']:
                book_info = data['data']['bookInfo']

            if not book_info:
                return None

            title = book_info.get('bookName', 'Unknown Novel')
            author = book_info.get('authorName', 'Unknown Author')
            cover_url = book_info.get('coverUrl')
            description = book_info.get('description')

            chapters = []
            volumes = []

            # Try to get volume/chapter info
            volume_list = book_info.get('volumeList') or book_info.get('volumes') or []

            for vol_idx, volume in enumerate(volume_list, 1):
                vol_title = volume.get('volumeName') or volume.get('name') or f"Volume {vol_idx}"
                volumes.append({
                    'index': vol_idx,
                    'title': vol_title,
                    'start_chapter': len(chapters) + 1
                })

                chapter_list = volume.get('chapterList') or volume.get('chapters') or []
                for ch in chapter_list:
                    ch_id = ch.get('chapterId') or ch.get('id')
                    ch_title = ch.get('chapterName') or ch.get('name') or f"Chapter {len(chapters) + 1}"
                    is_locked = ch.get('isVip') or ch.get('locked', False)

                    book_id = self._extract_book_id(url)
                    ch_url = f"{self.base_url}/book/{book_id}/{ch_id}" if book_id and ch_id else url

                    chapters.append(ChapterRef(
                        index=len(chapters) + 1,
                        title=ch_title,
                        url=ch_url,
                        volume_index=vol_idx,
                        is_locked=is_locked
                    ))

            status_val = book_info.get('status', 0)
            status = "Completed" if status_val == 1 else "Ongoing"

            return NovelTOC(
                title=title,
                author=author,
                url=url,
                cover_url=cover_url,
                description=description,
                chapters=chapters,
                volumes=volumes if volumes else None,
                status=status
            )

        except Exception:
            return None

    def _parse_toc_regex(self, html: str, url: str) -> NovelTOC:
        """Fallback TOC parsing with regex"""
        # Extract title
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        title = title_match.group(1).strip() if title_match else "Unknown Novel"

        # Extract author
        author_match = re.search(r'"authorName"\s*:\s*"([^"]+)"', html)
        if not author_match:
            author_match = re.search(r'Author[:\s]*([^<]+)</span>', html, re.IGNORECASE)
        author = author_match.group(1).strip() if author_match else "Unknown Author"

        # Extract chapters from HTML
        chapter_pattern = r'<a[^>]+href="([^"]*chapter[^"]*)"[^>]*>([^<]+)</a>'
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
            chapters=chapters,
            status="Unknown"
        )

    async def get_chapter(self, chapter: ChapterRef) -> ChapterContent:
        """
        Download a chapter from Webnovel.

        Args:
            chapter: Chapter reference

        Returns:
            Chapter content
        """
        if not self.fetcher:
            raise ValueError("Fetcher not provided")

        if hasattr(chapter, 'is_locked') and chapter.is_locked:
            raise ValueError(f"Chapter {chapter.title} is locked and requires premium access")

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

        # Try to extract from JSON first
        for script in soup.find_all('script'):
            if script.string and 'chapterContent' in script.string:
                try:
                    json_match = re.search(r'"content"\s*:\s*"([^"]+)"', script.string)
                    if json_match:
                        # Decode escaped content
                        content = json_match.group(1)
                        content = content.encode().decode('unicode_escape')
                        cleaned_html, plain_text, images = extract_chapter_content(content, chapter.url)
                        return ChapterContent(
                            ref=chapter,
                            html=cleaned_html,
                            text=plain_text,
                            images=images
                        )
                except Exception:
                    continue

        # Remove unwanted elements
        for selector in ['script', 'style', '.ads', '.advertisement', 'nav', 'header',
                        'footer', '.comments', '.sidebar', '.pirate', '.app-download']:
            for elem in soup.select(selector):
                elem.decompose()

        # Try different content selectors
        content_selectors = [
            '.chapter-content',
            '.cha-content',
            '#chapter-content',
            '.content-text',
            '[data-chapter-content]',
            '.reading-content',
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
        # Try to find content in JSON
        json_match = re.search(r'"content"\s*:\s*"([^"]+)"', html)
        if json_match:
            content = json_match.group(1)
            content = content.encode().decode('unicode_escape')
            cleaned_html, plain_text, images = extract_chapter_content(content, chapter.url)
            return ChapterContent(
                ref=chapter,
                html=cleaned_html,
                text=plain_text,
                images=images
            )

        # Try HTML content
        content_match = re.search(
            r'<div[^>]*class="[^"]*(?:chapter-content|cha-content|content)[^"]*"[^>]*>(.+?)</div>',
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
