"""
NovelUpdates adapter for SageCrawler

Handles URLs from novelupdates.com - aggregator/tracker for translated web novels
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
class NovelUpdatesAdapter:
    """Adapter for NovelUpdates site - novelupdates.com

    NovelUpdates is primarily an aggregator/tracker that links to external translation sites.
    This adapter handles searching and TOC extraction, but chapter content comes from external links.
    """

    @classmethod
    def get_info(cls) -> AdapterInfo:
        return AdapterInfo(
            name="novelupdates",
            display_name="Novel Updates",
            base_url="https://www.novelupdates.com",
            supported_domains=["novelupdates.com", "www.novelupdates.com"],
            capabilities=SiteCapability.SEARCH | SiteCapability.DIRECT_URL,
            description="Aggregator/tracker for translated web novels - links to external translation sites",
            rate_limit=1.0
        )

    def __init__(self, fetcher: Optional[PoliteFetcher] = None):
        self.fetcher = fetcher
        self.base_url = "https://www.novelupdates.com"

    @property
    def name(self) -> str:
        return "novelupdates"

    def can_handle(self, url: str) -> bool:
        """Check if URL is from NovelUpdates"""
        parsed = urlparse(url)
        return 'novelupdates.com' in parsed.netloc.lower()

    async def search(self, query: str, limit: int = 20) -> List[SearchHit]:
        """
        Search NovelUpdates for novels.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of search hits
        """
        if not self.fetcher:
            return []

        # NovelUpdates search URL
        search_url = f"{self.base_url}/?s={quote_plus(query)}&post_type=seriesplans"

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
        novel_items = soup.select('.search_main_box_nu, .search_body_nu, .searchp')

        for item in novel_items[:limit]:
            try:
                # Extract link
                link = item.select_one('a[href*="/series/"]')
                if not link:
                    continue

                href = link.get('href', '')
                url = urljoin(self.base_url, href)

                # Extract title
                title_elem = item.select_one('.search_title a, .search_title, h4 a')
                title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)

                # Extract cover
                cover_elem = item.select_one('img')
                cover_url = None
                if cover_elem:
                    cover_url = cover_elem.get('src') or cover_elem.get('data-src')
                    if cover_url:
                        cover_url = urljoin(self.base_url, cover_url)

                # Extract rating
                rating_elem = item.select_one('.search_ratings, .nurating')
                rating = None
                if rating_elem:
                    rating_text = rating_elem.get_text()
                    match = re.search(r'([\d.]+)', rating_text)
                    if match:
                        rating = float(match.group(1))

                # Extract genre/type
                genre_elem = item.select_one('.search_genre, .gennew')
                genres = []
                if genre_elem:
                    genre_links = genre_elem.select('a')
                    for g in genre_links[:5]:
                        genres.append(g.get_text(strip=True))

                # Extract release info
                release_elem = item.select_one('.search_stats')
                chapter_count = None
                status = None
                if release_elem:
                    text = release_elem.get_text()
                    ch_match = re.search(r'(\d+)\s*(?:chapters?|ch)', text, re.IGNORECASE)
                    if ch_match:
                        chapter_count = int(ch_match.group(1))

                    if 'complete' in text.lower():
                        status = "Completed"
                    elif 'ongoing' in text.lower():
                        status = "Ongoing"

                results.append(SearchHit(
                    title=title,
                    author="Unknown",  # NovelUpdates often doesn't show author in search
                    url=url,
                    source="novelupdates",
                    cover_url=cover_url,
                    chapter_count=chapter_count,
                    rating=rating,
                    status=status,
                    genres=genres if genres else None
                ))

            except Exception:
                continue

        return results

    def _parse_search_regex(self, html: str, limit: int) -> List[SearchHit]:
        """Fallback search parsing with regex"""
        results = []

        # Find series links
        pattern = r'<a[^>]+href="(https?://[^"]*novelupdates\.com/series/[^"]+)"[^>]*>([^<]+)</a>'
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
                source="novelupdates"
            ))

        return results

    async def get_toc(self, url: str) -> NovelTOC:
        """
        Get table of contents from a NovelUpdates series page.

        Note: NovelUpdates is an aggregator - chapter links point to external translation sites.

        Args:
            url: Series page URL

        Returns:
            Novel TOC with chapters (links to external sites)
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
        title_elem = soup.select_one('.seriestitlenu, h1.entry-title, .title')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Novel"

        # Extract author
        author = "Unknown Author"
        author_elem = soup.select_one('#authtag a, #showauthors a, a[href*="/group/"]')
        if author_elem:
            author = author_elem.get_text(strip=True)

        # Extract description
        description = None
        desc_elem = soup.select_one('#editdescription, .seriesdes, .description')
        if desc_elem:
            description = desc_elem.get_text(strip=True)

        # Extract cover URL
        cover_url = None
        cover_elem = soup.select_one('.seriesimg img, .wpb_wrapper img')
        if cover_elem:
            cover_url = cover_elem.get('src') or cover_elem.get('data-src')
            if cover_url:
                cover_url = urljoin(url, cover_url)

        # Extract original title
        original_title = None
        orig_elem = soup.select_one('#editassociated')
        if orig_elem:
            original_title = orig_elem.get_text(strip=True)

        # Extract status
        status = "Unknown"
        status_elem = soup.select_one('#editstatus')
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
        genre_elems = soup.select('#seriesgenre a, .genre a, #showtags a')
        for g in genre_elems[:15]:
            genres.append(g.get_text(strip=True))

        # Extract chapter list
        # NovelUpdates has chapters in a table or list, often paginated
        chapters = []

        # Try the release table first
        chapter_rows = soup.select('#myTable tr, .chp-release, table.tablesorter tbody tr')

        for row in chapter_rows:
            try:
                # Get chapter link
                link = row.select_one('a[href*="extnu"]')  # NovelUpdates uses extnu for external links
                if not link:
                    link = row.select_one('a.chp-release')
                if not link:
                    continue

                href = link.get('href', '')

                # NovelUpdates wraps external URLs - need to extract the actual URL
                # URLs are like: https://www.novelupdates.com/extnu/1234567/
                chapter_url = href

                chapter_title = link.get_text(strip=True)

                # Get group/translator info
                group_elem = row.select_one('a[href*="/group/"]')
                translator = group_elem.get_text(strip=True) if group_elem else None

                chapters.append(ChapterRef(
                    index=len(chapters) + 1,
                    title=chapter_title or f"Chapter {len(chapters) + 1}",
                    url=chapter_url,
                    translator=translator
                ))

            except Exception:
                continue

        # Reverse chapters if they're in reverse order (newest first)
        if chapters and len(chapters) > 1:
            # Check if first chapter number > last chapter number
            first_num = self._extract_chapter_number(chapters[0].title)
            last_num = self._extract_chapter_number(chapters[-1].title)
            if first_num and last_num and first_num > last_num:
                chapters = list(reversed(chapters))
                # Re-index
                for i, ch in enumerate(chapters, 1):
                    ch.index = i

        # Extract rating
        rating = None
        rating_elem = soup.select_one('.uvotes, .seriesrating')
        if rating_elem:
            rating_text = rating_elem.get_text()
            match = re.search(r'([\d.]+)', rating_text)
            if match:
                rating = float(match.group(1))

        # Extract type (CN, KR, JP, etc.)
        novel_type = None
        type_elem = soup.select_one('#showtype a, .genre a[href*="type"]')
        if type_elem:
            novel_type = type_elem.get_text(strip=True)

        return NovelTOC(
            title=title,
            author=author,
            url=url,
            cover_url=cover_url,
            description=description,
            chapters=chapters,
            status=status,
            genres=genres if genres else None,
            original_title=original_title,
            novel_type=novel_type,
            rating=rating
        )

    def _extract_chapter_number(self, title: str) -> Optional[int]:
        """Extract chapter number from title"""
        match = re.search(r'(?:chapter|ch\.?|c)\s*(\d+)', title, re.IGNORECASE)
        if match:
            return int(match.group(1))
        # Try just finding a number
        match = re.search(r'^(\d+)', title)
        if match:
            return int(match.group(1))
        return None

    def _parse_toc_regex(self, html: str, url: str) -> NovelTOC:
        """Fallback TOC parsing with regex"""
        # Extract title
        title_match = re.search(r'<div[^>]*class="[^"]*seriestitlenu[^"]*"[^>]*>([^<]+)</div>', html)
        if not title_match:
            title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        title = title_match.group(1).strip() if title_match else "Unknown Novel"

        # Extract author
        author_match = re.search(r'<a[^>]+href="[^"]*novelupdates\.com/group/[^"]*"[^>]*>([^<]+)</a>', html)
        author = author_match.group(1).strip() if author_match else "Unknown Author"

        # Extract description
        desc_match = re.search(r'<div[^>]*id="editdescription"[^>]*>(.+?)</div>', html, re.DOTALL)
        description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip() if desc_match else None

        # Extract chapter list
        chapter_pattern = r'<a[^>]+href="([^"]*extnu[^"]*)"[^>]*>([^<]+)</a>'
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
        Get chapter content from external link.

        Note: NovelUpdates chapters link to external sites. This method follows the redirect
        and attempts to extract content from the target site.

        Args:
            chapter: Chapter reference with NovelUpdates extnu URL

        Returns:
            Chapter content from the external site
        """
        if not self.fetcher:
            raise ValueError("Fetcher not provided")

        # First, resolve the NovelUpdates redirect
        actual_url = chapter.url

        if 'extnu' in chapter.url:
            try:
                # Follow the redirect to get actual URL
                response = await self.fetcher.fetch(chapter.url, follow_redirects=True)
                actual_url = str(response.url) if hasattr(response, 'url') else chapter.url
            except Exception:
                pass

        # Fetch the actual chapter page
        response = await self.fetcher.fetch(actual_url)
        html = response.text

        if HAS_BS4:
            return self._parse_chapter_bs4(html, chapter, actual_url)
        else:
            return self._parse_chapter_regex(html, chapter)

    def _parse_chapter_bs4(self, html: str, chapter: ChapterRef, actual_url: str) -> ChapterContent:
        """Parse chapter using BeautifulSoup - generic extraction for external sites"""
        soup = BeautifulSoup(html, 'lxml')

        # Remove unwanted elements
        for selector in ['script', 'style', '.ads', '.advertisement', 'nav', 'header',
                        'footer', '.comments', '.sidebar', '.related', '.share']:
            for elem in soup.select(selector):
                elem.decompose()

        # Generic content selectors that work across many translation sites
        content_selectors = [
            '.chapter-content',
            '.entry-content',
            '.post-content',
            '.content',
            '#chapter-content',
            '#content',
            'article',
            '.reading-content',
            '.text-content',
            '.chp-body',
            '.chapter-body'
        ]

        content_elem = None
        max_text_len = 0

        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                text_len = len(elem.get_text())
                if text_len > max_text_len and text_len > 500:
                    max_text_len = text_len
                    content_elem = elem

        # If no content found with selectors, find largest text block
        if not content_elem:
            all_divs = soup.find_all('div')
            for div in all_divs:
                text_len = len(div.get_text())
                if text_len > max_text_len and text_len > 500:
                    max_text_len = text_len
                    content_elem = div

        if not content_elem:
            raise ValueError(f"Could not find chapter content at {actual_url}")

        raw_html = str(content_elem)

        # Clean and extract content
        cleaned_html, plain_text, images = extract_chapter_content(raw_html, actual_url)

        return ChapterContent(
            ref=chapter,
            html=cleaned_html,
            text=plain_text,
            images=images,
            source_url=actual_url  # Include the actual source URL
        )

    def _parse_chapter_regex(self, html: str, chapter: ChapterRef) -> ChapterContent:
        """Fallback chapter parsing with regex"""
        # Try generic content patterns
        content_patterns = [
            r'<div[^>]*class="[^"]*(?:chapter-content|entry-content|content)[^"]*"[^>]*>(.+?)</div>',
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


# Helper function to resolve NovelUpdates external links
async def resolve_extnu_link(fetcher: PoliteFetcher, extnu_url: str) -> str:
    """
    Resolve a NovelUpdates external link (extnu) to the actual URL.

    Args:
        fetcher: HTTP fetcher
        extnu_url: NovelUpdates external link URL

    Returns:
        The actual destination URL
    """
    try:
        response = await fetcher.fetch(extnu_url, follow_redirects=True)
        return str(response.url) if hasattr(response, 'url') else extnu_url
    except Exception:
        return extnu_url
