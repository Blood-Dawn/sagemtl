"""
Generic web novel crawler for sites not supported by lightnovel-crawler.

This module provides a fallback crawler that attempts to extract novel content
from any website using common HTML patterns and heuristics.
"""

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import httpx
from bs4 import BeautifulSoup

from sagemtl_desktop.core.crawler_interface import CrawledNovel, CrawledChapter
from sagemtl_desktop.core.crawl_settings import CrawlSettings, DEFAULT_CRAWL_USER_AGENT


class GenericNovelCrawler:
    """
    A generic crawler that attempts to scrape novels from any website.
    
    This uses heuristics to find chapter links and extract content,
    making it work with sites not officially supported by lightnovel-crawler.
    """
    
    def __init__(self, base_url: str, crawl_settings: Optional[CrawlSettings] = None):
        """
        Initialize the generic crawler.
        
        Args:
            base_url: The URL of the novel's main page
            crawl_settings: Runtime crawl settings for requests/policies
        """
        self.base_url = base_url
        parsed_base = urlparse(base_url)
        self.domain = parsed_base.netloc
        self.base_scheme = parsed_base.scheme or "https"
        self.settings = (crawl_settings or CrawlSettings()).normalize()
        self._request_lock = threading.Lock()
        self._last_request_at = 0.0
        self._robots_checked = False
        self._robots_parser: Optional[RobotFileParser] = None
        self.session = httpx.Client(
            follow_redirects=True,
            timeout=30.0,
            headers={
                'User-Agent': self.settings.user_agent or DEFAULT_CRAWL_USER_AGENT
            }
        )

    def _enforce_request_delay(self):
        """Apply request throttling across all worker threads."""
        delay = self.settings.request_delay_seconds
        if delay <= 0:
            return

        with self._request_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_at
            if elapsed < delay:
                time.sleep(delay - elapsed)
                now = time.monotonic()
            self._last_request_at = now

    def _ensure_robots_parser(self):
        """Load robots.txt once unless policy explicitly ignores it."""
        if self.settings.ignore_robots_txt or self._robots_checked:
            return

        self._robots_checked = True
        robots_url = f"{self.base_scheme}://{self.domain}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
        except Exception:
            self._robots_parser = None
            return
        self._robots_parser = parser

    def _assert_robots_allowed(self, url: str):
        """Reject disallowed URLs when robots override is disabled."""
        if self.settings.ignore_robots_txt:
            return
        self._ensure_robots_parser()
        if self._robots_parser and not self._robots_parser.can_fetch(self.settings.user_agent, url):
            raise PermissionError(
                f"Blocked by robots.txt policy for {url}. "
                "Enable override in crawl settings to bypass."
            )

    def _request(self, method: str, url: str, allow_http_errors: bool = False, **kwargs) -> httpx.Response:
        """
        Send an HTTP request with delay/retries and optional robots policy.

        Args:
            method: HTTP method
            url: Target URL
            allow_http_errors: If True, do not raise on HTTP status codes
            **kwargs: Passed to httpx.Client.request
        """
        self._assert_robots_allowed(url)

        retries = self.settings.max_retries
        last_exc = None
        for attempt in range(retries + 1):
            self._enforce_request_delay()
            try:
                response = self.session.request(method, url, **kwargs)
                if allow_http_errors:
                    return response
                if response.status_code >= 500 and attempt < retries:
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response is not None and exc.response.status_code < 500:
                    raise
                if attempt >= retries:
                    raise
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_exc = exc
                if attempt >= retries:
                    raise

        # Defensive fallback; loop should return or raise.
        if last_exc:
            raise last_exc
        raise RuntimeError(f"Request failed without exception: {method} {url}")
    
    def discover_chapters(self, progress_callback=None) -> tuple:
        """
        Discover all available chapters without downloading content.
        
        This is the first phase - find all chapter links and return them
        so the user can choose which ones to download.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (title, author, chapter_links) where chapter_links is 
            a list of (url, title) tuples
        """
        if progress_callback:
            progress_callback(0, 100, "Stage 1/3: Fetching novel page...")
        
        # Get the main novel page
        response = self._request("GET", self.base_url)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if progress_callback:
            progress_callback(20, 100, "Stage 2/3: Extracting novel metadata...")
        
        # Extract novel title and author
        title = self._extract_title(soup)
        author = self._extract_author(soup)
        
        if progress_callback:
            progress_callback(
                40,
                100,
                "Stage 3/3: Finding chapter links (this may take a while for large novels)..."
            )
        
        # Find all chapter links
        chapter_links = self._find_chapter_links(soup, self.base_url)
        
        # If no chapter links found from page, try pattern-based discovery
        if not chapter_links:
            if progress_callback:
                progress_callback(60, 100, "No chapter list found. Trying pattern-based discovery...")
            chapter_links = self._discover_chapters_by_pattern(self.base_url)
        
        if progress_callback:
            progress_callback(100, 100, f"Discovery complete: Found {len(chapter_links)} chapters")
        
        return title, author, chapter_links
    
    def fetch_chapters(self, chapter_links: List[tuple], title: str, author: str,
                       progress_callback=None, max_workers: int = 4) -> CrawledNovel:
        """
        Fetch content for specified chapters.
        
        This is the second phase - download content for the selected chapters.
        
        Args:
            chapter_links: List of (url, title) tuples to download
            title: Novel title
            author: Novel author
            progress_callback: Optional callback for progress updates
            
        Returns:
            CrawledNovel with extracted content
        """
        if not chapter_links:
            raise ValueError("No chapters to download")
        
        if progress_callback:
            progress_callback(0, 100, f"Downloading {len(chapter_links)} chapters...")
        
        worker_count = max(1, min(max_workers, len(chapter_links)))
        if progress_callback:
            progress_callback(
                0,
                100,
                f"Downloading chapters with {worker_count} worker(s)..."
            )

        chapters: List[Optional[CrawledChapter]] = [None] * len(chapter_links)
        completed_count = 0
        completed_lock = threading.Lock()

        def download_one(index: int, chapter_url: str, chapter_title: str):
            content = self._fetch_chapter_content(chapter_url)
            return index, CrawledChapter(
                title=chapter_title or f"Chapter {index + 1}",
                content=content,
                chapter_number=index + 1,
                url=chapter_url
            )

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(download_one, idx, chapter_url, chapter_title): (idx, chapter_url)
                for idx, (chapter_url, chapter_title) in enumerate(chapter_links)
            }

            for future in as_completed(future_map):
                idx, chapter_url = future_map[future]
                try:
                    chapter_idx, chapter = future.result()
                    chapters[chapter_idx] = chapter
                except Exception as e:
                    # Log but continue with other chapters
                    print(
                        f"Warning: Failed to download chapter {idx + 1} ({chapter_url}): {e}"
                    )
                finally:
                    with completed_lock:
                        completed_count += 1
                        if progress_callback:
                            percent = int((completed_count / len(chapter_links)) * 95)
                            progress_callback(
                                percent,
                                100,
                                f"Downloaded {completed_count}/{len(chapter_links)} chapters..."
                            )

        ordered_chapters = [chapter for chapter in chapters if chapter is not None]
        for idx, chapter in enumerate(ordered_chapters, 1):
            chapter.chapter_number = idx

        if progress_callback:
            progress_callback(100, 100, "Download complete!")

        return CrawledNovel(
            title=title,
            author=author,
            chapters=ordered_chapters
        )
    
    def fetch_novel(self, progress_callback=None, max_chapters: Optional[int] = None) -> CrawledNovel:
        """
        Fetch the novel using generic scraping techniques.
        
        Args:
            progress_callback: Optional callback for progress updates
            max_chapters: Optional limit on number of chapters
            
        Returns:
            CrawledNovel with extracted content
        """
        if progress_callback:
            progress_callback(0, 100, "Stage 1/4: Fetching novel page...")
        
        # Get the main novel page
        response = self._request("GET", self.base_url)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if progress_callback:
            progress_callback(10, 100, "Stage 2/4: Extracting novel metadata...")
        
        # Extract novel title and author
        title = self._extract_title(soup)
        author = self._extract_author(soup)
        
        if progress_callback:
            progress_callback(20, 100, "Stage 3/4: Discovering chapter links...")
        
        # Find all chapter links
        chapter_links = self._find_chapter_links(soup, self.base_url)
        
        # If no chapter links found from page, try pattern-based discovery
        if not chapter_links:
            if progress_callback:
                progress_callback(
                    25,
                    100,
                    "No chapter list found. Trying pattern-based discovery..."
                )
            chapter_links = self._discover_chapters_by_pattern(self.base_url)
        
        # Only limit if explicitly requested (for testing)
        if max_chapters and max_chapters > 0:
            chapter_links = chapter_links[:max_chapters]
        
        if not chapter_links:
            raise ValueError(
                f"No chapter links found on {self.base_url}\n\n"
                "The site may have unusual structure or may be blocking automated access."
            )
        
        if progress_callback:
            progress_callback(
                30,
                100,
                f"Stage 4/4: Found {len(chapter_links)} chapters. Starting download..."
            )

        def mapped_progress(current: int, total: int, message: str):
            if not progress_callback:
                return
            # Map fetch_chapters progress (0-100) into the final stage range (30-100).
            mapped = 30 + int((current / max(total, 1)) * 70)
            progress_callback(mapped, 100, message)

        novel = self.fetch_chapters(
            chapter_links=chapter_links,
            title=title,
            author=author or "Unknown",
            progress_callback=mapped_progress,
            max_workers=self.settings.chapter_download_workers
        )

        if progress_callback:
            progress_callback(100, 100, "Generic crawl complete!")

        return novel
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract novel title from the page."""
        # Try common title locations
        candidates = [
            soup.find('h1', class_=re.compile(r'title|novel|book', re.I)),
            soup.find('h1'),
            soup.find('meta', property='og:title'),
            soup.find('title')
        ]
        
        for candidate in candidates:
            if candidate:
                if candidate.name == 'meta':
                    title = candidate.get('content', '')
                else:
                    title = candidate.get_text(strip=True)
                
                if title:
                    # Clean up common suffixes
                    title = re.sub(r'\s*[-|]\s*(Read|Novel|Chapter|Latest).*$', '', title, flags=re.I)
                    return title.strip()
        
        # Fallback to domain name
        return self.domain
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author name from the page."""
        # Try common author locations
        candidates = [
            soup.find(class_=re.compile(r'author', re.I)),
            soup.find('span', class_=re.compile(r'author', re.I)),
            soup.find('div', class_=re.compile(r'author', re.I)),
            soup.find('meta', {'name': 'author'}),
            soup.find('a', href=re.compile(r'/author/', re.I))
        ]
        
        for candidate in candidates:
            if candidate:
                if candidate.name == 'meta':
                    author = candidate.get('content', '')
                else:
                    author = candidate.get_text(strip=True)
                
                # Clean up common prefixes
                if author := re.sub(r'^(By|Author|Writer):\s*', '', author, flags=re.I).strip():
                    return author
        
        return None
    
    def _find_chapter_links(self, soup: BeautifulSoup, base_url: str) -> List[Tuple[str, str]]:
        """
        Find all chapter links on the page, following pagination if present.
        
        Returns:
            List of (url, title) tuples
        """
        all_chapter_links = []
        visited_pages = set()
        pages_to_visit = [base_url]
        max_pages = 100  # Safety limit
        pages_visited = 0
        
        while pages_to_visit and pages_visited < max_pages:
            current_page = pages_to_visit.pop(0)
            
            if current_page in visited_pages:
                continue
            visited_pages.add(current_page)
            pages_visited += 1
            
            # Fetch page if not the first (soup already loaded for first page)
            if current_page != base_url:
                try:
                    response = self._request("GET", current_page)
                    page_soup = BeautifulSoup(response.text, 'html.parser')
                except Exception as e:
                    print(f"Failed to fetch pagination page {current_page}: {e}")
                    continue
            else:
                page_soup = soup
            
            # Find chapters on this page
            chapter_links = self._find_chapter_links_on_page(page_soup, base_url)
            
            for link in chapter_links:
                if link not in all_chapter_links:
                    all_chapter_links.append(link)
            
            # Look for pagination links on EVERY page (not just first)
            # This ensures we discover all pages even if they're not all linked from page 1
            pagination_links = self._find_pagination_links(page_soup, current_page)
            for plink in pagination_links:
                if plink not in visited_pages and plink not in pages_to_visit:
                    pages_to_visit.append(plink)
        
        print(f"Visited {pages_visited} pages, found {len(all_chapter_links)} chapters")
        
        # Sort by chapter number if possible
        return self._sort_chapters(all_chapter_links)
    
    def _find_chapter_links_on_page(self, soup: BeautifulSoup, base_url: str) -> List[Tuple[str, str]]:
        """
        Find chapter links on a single page (no pagination following).
        
        Returns:
            List of (url, title) tuples
        """
        chapter_links = []
        
        # Look for common chapter list containers - ordered by specificity
        # More specific patterns first to avoid matching sidebars
        containers = [
            # Look for section/div with "chapter list" header text
            soup.find('section', class_=re.compile(r'chapter', re.I)),
            soup.find('div', class_=re.compile(r'^chapter[-_]?list$', re.I)),
            soup.find('ul', class_=re.compile(r'^chapter[-_]?list$', re.I)),
            soup.find('div', id=re.compile(r'^chapter[-_]?list$', re.I)),
            # More general patterns
            soup.find('div', class_=re.compile(r'chapter.*list|list.*chapter', re.I)),
            soup.find('div', class_=re.compile(r'table.*content', re.I)),
            soup.find('ul', class_=re.compile(r'chapter', re.I)),
            soup.find('div', id=re.compile(r'chapter', re.I)),
            # Novgo.net specific - look for chapter list section by header
            self._find_container_by_header(soup, ['chapter list', 'chapters', 'table of contents']),
            soup  # Fallback to entire page
        ]
        
        for container in containers:
            if not container:
                continue
            
            # Find all links that look like chapters
            links = container.find_all('a', href=True)
            
            found_chapters = []
            for link in links:
                href = link.get('href', '')
                
                # Get just the direct text, not text from child elements
                # This avoids picking up "346 days ago" from date spans
                text = self._get_direct_link_text(link)
                
                # Skip if empty or looks like navigation
                if not text or len(text) < 3:
                    continue
                
                # Clean the title - remove common garbage
                text = self._clean_chapter_title(text)
                
                # Check if it looks like a chapter link
                if self._is_chapter_link(href, text):
                    full_url = urljoin(base_url, href)
                    
                    # Avoid duplicates
                    if all(url != full_url for url, _ in found_chapters):
                        found_chapters.append((full_url, text))
            
            # If we found a reasonable number of chapters in this container, use it
            # Skip containers with very few chapters (likely sidebar/latest chapters)
            if len(found_chapters) > 10:
                return found_chapters
            elif found_chapters and not chapter_links:
                chapter_links = found_chapters
        
        return chapter_links
    
    def _find_container_by_header(self, soup: BeautifulSoup, header_texts: List[str]) -> Optional[BeautifulSoup]:
        """
        Find a container section by looking for headers with specific text.
        Useful for sites like novgo.net that have 'CHAPTER LIST' as a header.
        """
        for header_text in header_texts:
            # Look for headers containing the text
            for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div'], class_=re.compile(r'title|header', re.I)):
                if header_text.lower() in header.get_text(strip=True).lower():
                    # Return the parent container
                    if parent := header.find_parent(['section', 'div', 'article']):
                        return parent
            
            # Also look for elements with the text directly
            for elem in soup.find_all(string=re.compile(header_text, re.I)):
                if parent := elem.find_parent(['section', 'div', 'article']):
                    return parent
        
        return None
    
    def _find_pagination_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Find pagination links for chapter lists.
        
        Returns:
            List of pagination page URLs
        """
        pagination_links = []
        
        # First, look for pagination containers
        pagination_containers = [
            soup.find('div', class_=re.compile(r'pagination|pager|pages', re.I)),
            soup.find('nav', class_=re.compile(r'pagination|pager', re.I)),
            soup.find('ul', class_=re.compile(r'pagination|pager', re.I)),
            soup  # Fallback to entire page
        ]
        
        for container in pagination_containers:
            if not container:
                continue
                
            for link in container.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Skip empty or javascript links
                if not href or href.startswith('javascript:') or href == '#':
                    continue
                
                # Check for page parameter in URL
                if re.search(r'page[=\-/]?\d+|wjm=|/p/\d+', href, re.I):
                    full_url = urljoin(base_url, href)
                    if full_url not in pagination_links and full_url != base_url:
                        pagination_links.append(full_url)
                
                # Numbered page link (like "2", "3", etc.)
                elif text.isdigit() and 1 < int(text) <= 100:
                    full_url = urljoin(base_url, href)
                    if full_url not in pagination_links and full_url != base_url:
                        pagination_links.append(full_url)
                
                # "Next" or ">" links
                elif text in ['next', '>', '>>', '»', 'next page', 'last', 'last »']:
                    full_url = urljoin(base_url, href)
                    if full_url not in pagination_links and full_url != base_url:
                        pagination_links.append(full_url)
                
                # "First" link to page 1 (useful to ensure we have all pages)
                elif text in ['first', '<<', '«', '1']:
                    full_url = urljoin(base_url, href)
                    if full_url not in pagination_links and full_url != base_url:
                        pagination_links.append(full_url)
            
            # If we found pagination links in this container, stop looking
            if pagination_links:
                break
        
        return pagination_links

    def _get_direct_link_text(self, link) -> str:
        """
        Get only the direct text content of a link, excluding child element text.
        Falls back to full text if no direct text found.
        """
        # Try to get just the direct text (not from children like date spans)
        direct_text_parts = []
        for child in link.children:
            if isinstance(child, str) and (text := child.strip()):
                direct_text_parts.append(text)
        
        if direct_text_parts:
            return ' '.join(direct_text_parts)
        
        # Fallback to full text
        return link.get_text(strip=True)
    
    def _clean_chapter_title(self, title: str) -> str:
        """
        Clean garbage from chapter titles.
        Removes common patterns like dates, times, etc.
        """
        # Remove common date/time patterns
        patterns_to_remove = [
            r'\d+\s*(days?|hours?|mins?|minutes?|weeks?|months?|years?)\s*ago',
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # Dates like 01/01/2024
            r'\d{4}[/-]\d{2}[/-]\d{2}',  # Dates like 2024-01-01
            r'^\d+\s*',  # Leading chapter number (will be added back)
        ]
        
        cleaned = title
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.I)
        
        # Clean up extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    def _is_chapter_link(self, href: str, text: str) -> bool:
        """Check if a link looks like a chapter link."""
        # Common chapter patterns in URLs
        chapter_patterns = [
            r'chapter[-_\s]*\d+',
            r'ch[-_\s]*\d+',
            r'volume[-_\s]*\d+',
            r'episode[-_\s]*\d+',
            r'part[-_\s]*\d+',
            r'_\d+\.html$',  # Pattern like ke412542_1.html
            r'/\d+\.html$',  # Pattern like /123.html
            r'-\d+\.html$',  # Pattern like novel-123.html
        ]
        
        href_lower = href.lower()
        text_lower = text.lower()
        
        # Check URL patterns
        for pattern in chapter_patterns:
            if re.search(pattern, href_lower, re.I):
                return True
        
        # Check text patterns (chapter in title)
        text_patterns = [
            r'chapter\s*\d+',
            r'ch\s*\d+',
            r'^\d+[\.\:\s]',  # Starts with number like "1." or "1:"
        ]
        for pattern in text_patterns:
            if re.search(pattern, text_lower, re.I):
                return True
        
        # Avoid navigation links
        nav_keywords = ['home', 'index', 'contact', 'about', 'login', 'register', 'profile', 
                        'search', 'browse', 'list', 'tags', 'updates', 'login', 'member']
        if any(kw in text_lower for kw in nav_keywords) or any(kw in href_lower for kw in nav_keywords):
            return False
        
        # If URL contains chapter/post/read, likely a chapter
        return any(word in href_lower for word in ['chapter', 'post', 'read'])
    
    def _sort_chapters(self, chapters: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Sort chapters by number if possible."""
        def extract_number(text):
            """Extract first number from text."""
            match = re.search(r'\d+', text)
            return int(match.group()) if match else float('inf')
        
        # Try to sort by chapter number
        try:
            return sorted(chapters, key=lambda x: extract_number(x[1]))
        except Exception:
            # If sorting fails, return as is
            return chapters
    
    def _discover_chapters_by_pattern(self, url: str) -> List[Tuple[str, str]]:
        """
        Discover chapters by detecting URL patterns and incrementing chapter numbers.
        
        This is used as a fallback when the main page doesn't have a chapter list.
        Works by:
        1. Detecting if the URL contains a chapter number
        2. Testing incrementing URLs to find valid chapters
        
        Args:
            url: The base URL (may be a chapter URL)
            
        Returns:
            List of (url, title) tuples
        """
        # Common patterns for chapter URLs
        # Pattern: match chapter number in URL
        patterns = [
            # /chapter-1, /chapter-123
            (r'(chapter[-_]?)(\d+)', r'\g<1>{}'),
            # /ch-1, /ch-123  
            (r'(ch[-_]?)(\d+)', r'\g<1>{}'),
            # /1, /123 at end of URL path
            (r'/(\d+)(?:/|$)', '/{}'),
            # ?chapter=1, ?ch=123
            (r'([?&](?:chapter|ch)=)(\d+)', r'\g<1>{}'),
            # chapter/1, episode/123
            (r'(chapter|episode|part)[-/](\d+)', r'\g<1>/{}'),
        ]
        
        chapter_links = []
        base_chapter_num = None
        pattern_used = None
        replacement_template = None
        
        # Try to detect which pattern the URL uses
        for pattern, replacement in patterns:
            if match := re.search(pattern, url, re.I):
                base_chapter_num = int(match[2] if len(match.groups()) > 1 else match[1])
                pattern_used = pattern
                replacement_template = replacement
                break
        
        if base_chapter_num is None:
            # No chapter pattern detected
            return []
        
        # Start from chapter 1 and probe upwards
        max_failures = 5  # Stop after N consecutive 404s
        consecutive_failures = 0
        chapter_num = 1
        max_chapters_to_probe = 1000  # Safety limit
        
        while consecutive_failures < max_failures and chapter_num <= max_chapters_to_probe:
            # Generate the URL for this chapter
            test_url = re.sub(
                pattern_used,
                replacement_template.format(chapter_num),
                url,
                flags=re.I
            )
            
            try:
                # Quick HEAD request to check if URL exists
                response = self._request("HEAD", test_url, allow_http_errors=True, timeout=10)
                
                if response.status_code == 200:
                    chapter_links.append((test_url, f"Chapter {chapter_num}"))
                    consecutive_failures = 0
                elif response.status_code == 404:
                    consecutive_failures += 1
                else:
                    # Some sites don't support HEAD, try GET
                    response = self._request("GET", test_url, allow_http_errors=True, timeout=10)
                    if response.status_code == 200:
                        chapter_links.append((test_url, f"Chapter {chapter_num}"))
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
            except Exception:
                consecutive_failures += 1
            
            chapter_num += 1
        
        return chapter_links
    
    # Patterns to filter out from chapter content
    JUNK_PATTERNS = [
        r'^Prev\s*Chapter\s*Next\s*Chapter$',
        r'^Next\s*Chapter\s*Prev\s*Chapter$',
        r'^Prev\s*Chapter$',
        r'^Next\s*Chapter$',
        r'^Report\s*chapter$',
        r'^Tip:\s*You can use.*between chapters\.*$',
        r'^Tip:.*keyboard keys.*$',
        r'^Previous\s*Chapter$',
        r'^Next$',
        r'^Previous$',
        r'^Table of Contents$',
        r'^Home$',
        r'^Index$',
        r'^Share\s*this:?$',
        r'^Like\s*this:?$',
        r'^Loading\.+$',
        r'^Comments?\s*\(\d*\)$',
        r'^\d+\s*Comments?$',
        r'^Leave\s*a\s*comment',
        r'^Advertisement$',
        r'^Ads$',
        r'^Sponsored$',
    ]
    
    def _clean_chapter_text(self, text: str) -> str:
        """
        Clean chapter text by removing junk patterns.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        # Check against junk patterns
        if next((True for pattern in self.JUNK_PATTERNS if re.match(pattern, text.strip(), re.I)), False):
            return ""
        return text
    
    def _deduplicate_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """
        Remove duplicate paragraphs that often appear from bad scraping.
        
        Args:
            paragraphs: List of paragraph texts
            
        Returns:
            Deduplicated list
        """
        seen = set()
        result = []
        for p in paragraphs:
            # Normalize for comparison (remove extra whitespace)
            normalized = ' '.join(p.split())
            if normalized not in seen and len(normalized) > 10:
                seen.add(normalized)
                result.append(p)
        return result
    
    def _fetch_chapter_content(self, chapter_url: str) -> str:
        """
        Fetch and extract content from a chapter page.
        
        Args:
            chapter_url: URL of the chapter
            
        Returns:
            Cleaned chapter text
        """
        response = self._request("GET", chapter_url)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
            element.decompose()
        
        # Also remove navigation-related elements (use word boundaries to avoid false positives)
        nav_patterns = [
            r'\bnav\b', r'\bmenu\b', r'\bsidebar\b', r'\bcomment', r'\bshare\b', 
            r'\bsocial\b', r'\bads?\b', r'\bbanner\b', r'\bpopup\b'
        ]
        for pattern in nav_patterns:
            for element in soup.find_all(class_=re.compile(pattern, re.I)):
                # Don't remove if it's a content area
                classes = element.get('class') or []
                if all('content' not in c.lower() for c in classes):
                    element.decompose()
        
        # Remove elements by common nav IDs
        for element in soup.find_all(id=re.compile(r'nav|menu|sidebar|comment|share|social|ad[sv]?|banner', re.I)):
            element.decompose()
        
        # Try to find the main content area
        content_candidates = [
            soup.find('div', class_=re.compile(r'chapter[-_]?content|post[-_]?content|entry[-_]?content|article[-_]?content|reading[-_]?content', re.I)),
            soup.find('div', class_=re.compile(r'^content$', re.I)),
            soup.find('article'),
            soup.find('div', id=re.compile(r'chapter[-_]?content|content', re.I)),
            soup.find('main'),
        ]
        
        content = next((c for c in content_candidates if c), None) or soup.find('body')
        
        if not content:
            return ""
        
        # Strategy 1: Try to get text from paragraph elements
        paragraphs = []
        for p in content.find_all(['p']):
            text = p.get_text(strip=True)
            if text and len(text) > 20 and (cleaned := self._clean_chapter_text(text)):
                paragraphs.append(cleaned)
        
        # If we got reasonable content from <p> tags, use it
        if len(paragraphs) >= 3:
            paragraphs = self._deduplicate_paragraphs(paragraphs)
            return '\n\n'.join(paragraphs)
        
        # Strategy 2: Get all text from content div, split by double newlines
        # This handles sites that use <br><br> or other separators
        full_text = content.get_text(separator='\n')
        
        # Split into paragraphs and clean
        raw_paragraphs = re.split(r'\n{2,}', full_text)
        paragraphs = []
        for p in raw_paragraphs:
            text = ' '.join(p.split())  # Normalize whitespace
            if text and len(text) > 20 and (cleaned := self._clean_chapter_text(text)):
                paragraphs.append(cleaned)
        
        # Deduplicate paragraphs
        paragraphs = self._deduplicate_paragraphs(paragraphs)
        
        return '\n\n'.join(paragraphs)
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
