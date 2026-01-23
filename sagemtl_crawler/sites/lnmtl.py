"""
LNMTL adapter for SageCrawler

Handles URLs from lnmtl.com - Light Novel Machine Translation site
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
class LNMTLAdapter:
    """Adapter for LNMTL site - lnmtl.com

    LNMTL provides machine translations of Chinese light novels with
    original Chinese text alongside translations.
    """

    @classmethod
    def get_info(cls) -> AdapterInfo:
        return AdapterInfo(
            name="lnmtl",
            display_name="LNMTL",
            base_url="https://lnmtl.com",
            supported_domains=["lnmtl.com", "www.lnmtl.com"],
            capabilities=SiteCapability.SEARCH | SiteCapability.DIRECT_URL | SiteCapability.VOLUMES | SiteCapability.AJAX,
            description="Light Novel Machine Translation - Chinese to English MTL",
            rate_limit=1.0
        )

    def __init__(self, fetcher: Optional[PoliteFetcher] = None):
        self.fetcher = fetcher
        self.base_url = "https://lnmtl.com"

    @property
    def name(self) -> str:
        return "lnmtl"

    def can_handle(self, url: str) -> bool:
        """Check if URL is from LNMTL"""
        parsed = urlparse(url)
        return 'lnmtl.com' in parsed.netloc.lower()

    async def search(self, query: str, limit: int = 20) -> List[SearchHit]:
        """
        Search LNMTL for novels.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of search hits
        """
        if not self.fetcher:
            return []

        # LNMTL search URL
        search_url = f"{self.base_url}/search?q={quote_plus(query)}"

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
        novel_items = soup.select('.novel, .search-result, .media')

        for item in novel_items[:limit]:
            try:
                # Extract link
                link = item.select_one('a[href*="/novel/"]')
                if not link:
                    continue

                href = link.get('href', '')
                url = urljoin(self.base_url, href)

                # Extract title
                title_elem = item.select_one('.novel-title, .media-heading, h4')
                title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)

                # Extract original title (Chinese)
                original_title = None
                orig_elem = item.select_one('.original-title, .chinese-title')
                if orig_elem:
                    original_title = orig_elem.get_text(strip=True)

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

                # Extract chapter count
                stats_elem = item.select_one('.chapters, .stats')
                chapter_count = None
                if stats_elem:
                    text = stats_elem.get_text()
                    match = re.search(r'(\d+)\s*(?:chapters?|ch)', text, re.IGNORECASE)
                    if match:
                        chapter_count = int(match.group(1))

                # Extract status
                status_elem = item.select_one('.status, .novel-status')
                status = None
                if status_elem:
                    status_text = status_elem.get_text(strip=True).lower()
                    if 'complete' in status_text:
                        status = "Completed"
                    elif 'ongoing' in status_text or 'translating' in status_text:
                        status = "Ongoing"

                results.append(SearchHit(
                    title=title,
                    author=author,
                    url=url,
                    source="lnmtl",
                    cover_url=cover_url,
                    chapter_count=chapter_count,
                    status=status,
                    original_title=original_title
                ))

            except Exception:
                continue

        return results

    def _parse_search_regex(self, html: str, limit: int) -> List[SearchHit]:
        """Fallback search parsing with regex"""
        results = []

        # Find novel links
        pattern = r'<a[^>]+href="(/novel/[^"]+)"[^>]*>([^<]+)</a>'
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
                source="lnmtl"
            ))

        return results

    async def get_toc(self, url: str) -> NovelTOC:
        """
        Get table of contents from an LNMTL novel page.

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

        # Try to extract from JSON data first (LNMTL often embeds data in scripts)
        for script in soup.find_all('script'):
            if script.string and 'window.lnmtl' in script.string:
                try:
                    json_match = re.search(r'window\.lnmtl\s*=\s*({.+?});', script.string, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        toc = self._parse_toc_from_json(data, url)
                        if toc and toc.chapters:
                            return toc
                except (json.JSONDecodeError, TypeError):
                    continue

        # Fallback to HTML parsing
        # Extract title
        title_elem = soup.select_one('.novel-name, h1, .page-title')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Novel"

        # Extract original title
        original_title = None
        orig_elem = soup.select_one('.novel-name-original, .chinese-name')
        if orig_elem:
            original_title = orig_elem.get_text(strip=True)

        # Extract author
        author = "Unknown Author"
        author_elem = soup.select_one('.novel-author a, .author')
        if author_elem:
            author = author_elem.get_text(strip=True)

        # Extract description
        description = None
        desc_elem = soup.select_one('.novel-synopsis, .description, .synopsis')
        if desc_elem:
            description = desc_elem.get_text(strip=True)

        # Extract cover URL
        cover_url = None
        cover_elem = soup.select_one('.novel-cover img, .cover img')
        if cover_elem:
            cover_url = cover_elem.get('src') or cover_elem.get('data-src')
            if cover_url:
                cover_url = urljoin(url, cover_url)

        # Extract chapter list with volume support
        chapters = []
        volumes = []

        # LNMTL organizes by volumes
        volume_containers = soup.select('.volume, .volume-container, [data-volume-id]')

        if volume_containers:
            for vol_idx, vol_container in enumerate(volume_containers, 1):
                vol_title_elem = vol_container.select_one('.volume-title, .volume-name, h4')
                vol_title = vol_title_elem.get_text(strip=True) if vol_title_elem else f"Volume {vol_idx}"

                volumes.append({
                    'index': vol_idx,
                    'title': vol_title,
                    'start_chapter': len(chapters) + 1
                })

                chapter_links = vol_container.select('a[href*="/chapter/"]')
                for elem in chapter_links:
                    href = elem.get('href', '')
                    if not href:
                        continue

                    chapter_url = urljoin(url, href)
                    chapter_title = elem.get_text(strip=True)

                    chapters.append(ChapterRef(
                        index=len(chapters) + 1,
                        title=chapter_title or f"Chapter {len(chapters) + 1}",
                        url=chapter_url,
                        volume_index=vol_idx
                    ))
        else:
            # Flat chapter list
            chapter_links = soup.select('a[href*="/chapter/"]')
            seen_urls = set()

            for elem in chapter_links:
                href = elem.get('href', '')
                if not href:
                    continue

                chapter_url = urljoin(url, href)
                if chapter_url in seen_urls:
                    continue
                seen_urls.add(chapter_url)

                chapter_title = elem.get_text(strip=True)

                # Skip navigation links
                if not chapter_title or chapter_title.lower() in ['next', 'prev', 'previous']:
                    continue

                chapters.append(ChapterRef(
                    index=len(chapters) + 1,
                    title=chapter_title,
                    url=chapter_url
                ))

        # Extract status
        status = "Unknown"
        status_elem = soup.select_one('.novel-status, .status')
        if status_elem:
            status_text = status_elem.get_text(strip=True).lower()
            if 'complete' in status_text:
                status = "Completed"
            elif 'ongoing' in status_text or 'translating' in status_text:
                status = "Ongoing"

        # Extract genres
        genres = []
        genre_elems = soup.select('.novel-genre a, .genres a, .tag')
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
            genres=genres if genres else None,
            original_title=original_title
        )

    def _parse_toc_from_json(self, data: dict, url: str) -> Optional[NovelTOC]:
        """Parse TOC from JSON data structure"""
        try:
            novel = data.get('novel', {})
            if not novel:
                return None

            title = novel.get('name', 'Unknown Novel')
            original_title = novel.get('nameOrigin')
            author = novel.get('author', {}).get('name', 'Unknown Author')
            cover_url = novel.get('image')
            description = novel.get('description')

            chapters = []
            volumes = []

            volume_list = data.get('volumes', [])
            for vol_idx, volume in enumerate(volume_list, 1):
                vol_title = volume.get('title') or f"Volume {vol_idx}"
                volumes.append({
                    'index': vol_idx,
                    'title': vol_title,
                    'start_chapter': len(chapters) + 1
                })

                chapter_list = volume.get('chapters', [])
                for ch in chapter_list:
                    ch_slug = ch.get('slug')
                    ch_title = ch.get('title') or f"Chapter {len(chapters) + 1}"

                    ch_url = f"{self.base_url}/chapter/{ch_slug}" if ch_slug else url

                    chapters.append(ChapterRef(
                        index=len(chapters) + 1,
                        title=ch_title,
                        url=ch_url,
                        volume_index=vol_idx
                    ))

            status_val = novel.get('status', 'ongoing')
            status = "Completed" if status_val == 'complete' else "Ongoing"

            return NovelTOC(
                title=title,
                author=author,
                url=url,
                cover_url=cover_url,
                description=description,
                chapters=chapters,
                volumes=volumes if volumes else None,
                status=status,
                original_title=original_title
            )

        except Exception:
            return None

    def _parse_toc_regex(self, html: str, url: str) -> NovelTOC:
        """Fallback TOC parsing with regex"""
        # Extract title
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        title = title_match.group(1).strip() if title_match else "Unknown Novel"

        # Extract author
        author_match = re.search(r'"author"[:\s]*"([^"]+)"', html)
        author = author_match.group(1) if author_match else "Unknown Author"

        # Extract chapters
        chapter_pattern = r'<a[^>]+href="(/chapter/[^"]+)"[^>]*>([^<]+)</a>'
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
            chapters=chapters,
            status="Unknown"
        )

    async def get_chapter(self, chapter: ChapterRef) -> ChapterContent:
        """
        Download a chapter from LNMTL.

        Args:
            chapter: Chapter reference

        Returns:
            Chapter content (with both translated and original text if available)
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

        # Try to extract from JSON first
        for script in soup.find_all('script'):
            if script.string and 'window.lnmtl' in script.string:
                try:
                    json_match = re.search(r'window\.lnmtl\s*=\s*({.+?});', script.string, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        content = self._parse_chapter_from_json(data, chapter)
                        if content:
                            return content
                except (json.JSONDecodeError, TypeError):
                    continue

        # Remove unwanted elements
        for selector in ['script', 'style', '.ads', '.advertisement', 'nav', 'header',
                        'footer', '.comments', '.sidebar']:
            for elem in soup.select(selector):
                elem.decompose()

        # Try different content selectors - LNMTL specific
        content_selectors = [
            '.chapter-body',
            '.chapter-content',
            '.translated-content',
            '#chapter-content',
            '.content'
        ]

        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break

        if not content_elem:
            raise ValueError(f"Could not find chapter content in {chapter.url}")

        # LNMTL has sentences with both translated and original text
        sentences = content_elem.select('.translated, sentence')
        if sentences:
            # Build content from sentences
            translated_parts = []
            original_parts = []

            for sent in sentences:
                trans_elem = sent.select_one('.translated') or sent
                orig_elem = sent.select_one('.original')

                trans_text = trans_elem.get_text(strip=True)
                if trans_text:
                    translated_parts.append(trans_text)

                if orig_elem:
                    orig_text = orig_elem.get_text(strip=True)
                    if orig_text:
                        original_parts.append(orig_text)

            plain_text = '\n\n'.join(translated_parts)
            cleaned_html = '<p>' + '</p><p>'.join(translated_parts) + '</p>'

            return ChapterContent(
                ref=chapter,
                html=cleaned_html,
                text=plain_text,
                original_text='\n\n'.join(original_parts) if original_parts else None
            )

        raw_html = str(content_elem)

        # Clean and extract content
        cleaned_html, plain_text, images = extract_chapter_content(raw_html, chapter.url)

        # Extract next/prev chapter links
        next_chapter = None
        prev_chapter = None

        nav_links = soup.select('.chapter-nav a, .nav-chapter a')
        for link in nav_links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            if 'next' in text:
                next_chapter = urljoin(chapter.url, href)
            elif 'prev' in text:
                prev_chapter = urljoin(chapter.url, href)

        return ChapterContent(
            ref=chapter,
            html=cleaned_html,
            text=plain_text,
            images=images,
            next_url=next_chapter,
            prev_url=prev_chapter
        )

    def _parse_chapter_from_json(self, data: dict, chapter: ChapterRef) -> Optional[ChapterContent]:
        """Parse chapter content from JSON data"""
        try:
            chapter_data = data.get('chapter', {})
            if not chapter_data:
                return None

            # Get sentences
            sentences = chapter_data.get('body', [])
            if not sentences:
                return None

            translated_parts = []
            original_parts = []

            for sent in sentences:
                if isinstance(sent, dict):
                    trans = sent.get('t') or sent.get('translated', '')
                    orig = sent.get('o') or sent.get('original', '')
                else:
                    trans = str(sent)
                    orig = ''

                if trans:
                    translated_parts.append(trans)
                if orig:
                    original_parts.append(orig)

            plain_text = '\n\n'.join(translated_parts)
            cleaned_html = '<p>' + '</p><p>'.join(translated_parts) + '</p>'

            # Get navigation
            next_ch = chapter_data.get('next', {})
            prev_ch = chapter_data.get('prev', {})

            next_url = None
            prev_url = None

            if next_ch and next_ch.get('slug'):
                next_url = f"{self.base_url}/chapter/{next_ch['slug']}"
            if prev_ch and prev_ch.get('slug'):
                prev_url = f"{self.base_url}/chapter/{prev_ch['slug']}"

            return ChapterContent(
                ref=chapter,
                html=cleaned_html,
                text=plain_text,
                original_text='\n\n'.join(original_parts) if original_parts else None,
                next_url=next_url,
                prev_url=prev_url
            )

        except Exception:
            return None

    def _parse_chapter_regex(self, html: str, chapter: ChapterRef) -> ChapterContent:
        """Fallback chapter parsing with regex"""
        # Try to extract sentences
        sentence_pattern = r'<sentence[^>]*>.*?<span[^>]*class="[^"]*translated[^"]*"[^>]*>([^<]+)</span>'
        sentences = re.findall(sentence_pattern, html, re.DOTALL)

        if sentences:
            plain_text = '\n\n'.join(sentences)
            cleaned_html = '<p>' + '</p><p>'.join(sentences) + '</p>'
            return ChapterContent(
                ref=chapter,
                html=cleaned_html,
                text=plain_text
            )

        # Try generic content extraction
        content_match = re.search(
            r'<div[^>]*class="[^"]*(?:chapter-body|chapter-content|content)[^"]*"[^>]*>(.+?)</div>',
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
