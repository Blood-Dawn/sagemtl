"""
Wrapper for lightnovel-crawler to implement the CrawlerInterface.

This allows your app to use lightnovel-crawler's extensive site support
while maintaining GPL v3 compliance (it's a separate dependency, not
incorporated code).
"""
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from sagemtl_desktop.core.crawler_interface import (
    CrawlerInterface,
    CrawledNovel,
    CrawledChapter
)
from sagemtl_desktop.core.supported_sites import get_supported_sites_formatted
from sagemtl_desktop.core.generic_crawler import GenericNovelCrawler

# Try to import lightnovel-crawler, but don't fail if it's not installed
# This allows your app to work even if users haven't installed the optional dependency
LIGHTNOVEL_CRAWLER_AVAILABLE = False
try:
    from lncrawl.core.app import App as LNCrawlApp
    from lncrawl.core.exeptions import LNException
    LIGHTNOVEL_CRAWLER_AVAILABLE = True
except ImportError as e:
    # Store the error for debugging
    _import_error = str(e)
    LNException = None
except Exception as e:
    # Catch any other errors during import
    _import_error = f"Unexpected error: {str(e)}"
    LNException = None


class LightNovelCrawlerWrapper(CrawlerInterface):
    """
    Integrates lightnovel-crawler's extensive site support into sagemtl.

    This wrapper handles the complexity of interfacing with lightnovel-crawler,
    which was designed as a command-line tool but can also be used as a library.
    The key challenge is that it expects to write files to disk, but we want
    to capture the content in memory for processing.
    """

    def __init__(self, chapter_download_workers: int = 4):
        if not LIGHTNOVEL_CRAWLER_AVAILABLE:
            raise ImportError(
                "lightnovel-crawler is not installed. "
                "Install it with: pip install lightnovel-crawler"
            )

        # We'll use a temporary directory for lightnovel-crawler's output
        # then read it back into memory. This is necessary because lightnovel-crawler
        # was designed to save files rather than return data in memory.
        self.temp_dir = None
        self.chapter_download_workers = max(1, chapter_download_workers)

    @staticmethod
    def is_url(input_str: str) -> bool:
        """
        Detect if input is a URL or a novel name.
        
        Returns True if input looks like a URL (starts with http/https).
        Returns False if it looks like a novel name (plain text).
        """
        input_str = input_str.strip()
        return input_str.lower().startswith(('http://', 'https://'))

    async def fetch_novel(self, url: str, progress_callback=None, max_chapters: int = None) -> CrawledNovel:
        """
        Use lightnovel-crawler to fetch the novel, with generic crawler fallback.

        This method integrates with lncrawl's API to download novels.
        If the site is not supported by lncrawl, it falls back to the generic crawler.
        
        Args:
            url: Novel URL to download
            progress_callback: Optional callback for progress updates
            max_chapters: Optional limit on number of chapters to download (for testing)
        """
        # Try lightnovel-crawler first
        try:
            # Create a temporary directory for this crawl operation
            self.temp_dir = tempfile.mkdtemp(prefix='sagemtl_lncrawl_')

            # Run the crawler in a thread pool to avoid blocking your UI
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._run_crawler_sync,
                url,
                progress_callback,
                max_chapters
            )
        except RuntimeError as e:
            error_msg = str(e)
            
            # Check if it's not an unsupported site error - re-raise other errors
            if "not supported" not in error_msg.lower() and "no results" not in error_msg.lower():
                raise
            
            if progress_callback:
                progress_callback(0, 100, "Site not in lncrawl database. Trying generic crawler...")
            
            # Fall back to generic crawler
            return await self._fetch_with_generic_crawler(url, progress_callback, max_chapters)
        except Exception as e:
            # For unexpected errors, try generic crawler as last resort
            if progress_callback:
                progress_callback(0, 100, f"lncrawl failed ({str(e)}). Trying generic crawler...")
            
            return await self._fetch_with_generic_crawler(url, progress_callback, max_chapters)
        finally:
            # Clean up temporary files
            if self.temp_dir and Path(self.temp_dir).exists():
                shutil.rmtree(self.temp_dir)

    async def discover_chapters(
        self,
        url: str,
        progress_callback=None
    ) -> Tuple[str, Optional[str], List[Tuple[str, str]]]:
        """
        Discover chapter links for a novel URL.

        Uses the generic crawler path because lncrawl does not expose a stable
        chapter-discovery API suitable for interactive chapter selection.
        """
        def run_discovery():
            crawler = GenericNovelCrawler(url)
            try:
                return crawler.discover_chapters(progress_callback)
            finally:
                crawler.close()

        return await asyncio.get_event_loop().run_in_executor(None, run_discovery)

    async def fetch_selected_chapters(
        self,
        url: str,
        title: str,
        author: Optional[str],
        selected_chapters: List[Tuple[str, str]],
        progress_callback=None
    ) -> CrawledNovel:
        """
        Download a user-selected subset of chapters.

        This path uses the generic crawler so chapter selection/ranges work
        reliably even when lncrawl only supports full-novel downloads.
        """
        if not selected_chapters:
            raise ValueError("No chapters were selected for download")

        def run_fetch():
            crawler = GenericNovelCrawler(url)
            try:
                return crawler.fetch_chapters(
                    selected_chapters,
                    title=title,
                    author=author or "Unknown",
                    progress_callback=progress_callback,
                    max_workers=self.chapter_download_workers
                )
            finally:
                crawler.close()

        return await asyncio.get_event_loop().run_in_executor(None, run_fetch)
    
    async def _fetch_with_generic_crawler(self, url: str, progress_callback, max_chapters: int = None) -> CrawledNovel:
        """
        Fetch novel using the generic web crawler.
        
        Args:
            url: Novel URL to download
            progress_callback: Optional callback for progress updates
            max_chapters: Optional limit on number of chapters
            
        Returns:
            CrawledNovel from generic crawler
        """
        try:
            # Run generic crawler in executor to avoid blocking
            def run_generic():
                crawler = GenericNovelCrawler(url)
                try:
                    return crawler.fetch_novel(progress_callback, max_chapters)
                finally:
                    crawler.close()
            
            novel = await asyncio.get_event_loop().run_in_executor(None, run_generic)
            return novel
        except Exception as e:
            raise RuntimeError(
                f"Failed to crawl novel with generic crawler: {str(e)}\n\n"
                "The site may have unusual structure or may be blocking automated access."
            )

    async def search_novel_by_name(self, novel_name: str, progress_callback=None) -> List[Dict[str, Any]]:
        """
        Search for a novel by name and return available options.
        
        Returns a list of dicts with keys:
        - title: Novel title
        - url: URL to fetch
        - site: Source site name
        
        This uses lncrawl's interactive search functionality to find novels
        across multiple sites.
        """
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._search_novel_sync,
                novel_name,
                progress_callback
            )
        except Exception as e:
            if LNException and isinstance(e, LNException):
                raise RuntimeError(
                    f"Search failed: {str(e)}\n\n"
                    "Check supported sites via Help > View Supported Sites in the app."
                )
            raise RuntimeError(f"Failed to search for novel: {str(e)}")

    def _search_novel_sync(self, novel_name: str, progress_callback) -> List[Dict[str, Any]]:
        """
        Run novel search synchronously using lncrawl's API.
        """
        import sys
        
        if progress_callback:
            progress_callback(0, 100, "Loading sources...")

        try:
            # Temporarily override sys.argv to avoid argparse conflicts with pytest
            original_argv = sys.argv
            sys.argv = ['lncrawl']
            
            # Load sources first (required for search to work)
            from lncrawl.core.sources import load_sources
            load_sources()
            
            # Restore original argv
            sys.argv = original_argv
            
            if progress_callback:
                progress_callback(10, 100, f"Searching for '{novel_name}' across supported sites...")
            
            # Create the app instance
            app = LNCrawlApp()
            
            # Set search query
            app.user_input = novel_name
            
            if progress_callback:
                progress_callback(20, 100, "Preparing search...")

            # Prepare search (configures which crawlers to use)
            app.prepare_search()
            
            if progress_callback:
                progress_callback(30, 100, f"Searching across {len(app.crawler_links)} sites...")

            # Run the search
            app.search_novel()
            
            if progress_callback:
                progress_callback(90, 100, "Processing results...")

            # Debug: log what we got back
            if hasattr(app, 'search_results'):
                if progress_callback:
                    progress_callback(92, 100, f"Raw results count: {len(app.search_results) if app.search_results else 0}")
            
            # Extract search results
            # search_results should be a list of Result objects with .novel and .origin attributes
            results = []
            if hasattr(app, 'search_results') and app.search_results:
                for result in app.search_results:
                    try:
                        # Each result has .novel (with .url) and .origin (source)
                        novel = result.novel if hasattr(result, 'novel') else result
                        origin = result.origin if hasattr(result, 'origin') else 'Unknown'
                        
                        url = None
                        title = None
                        
                        if hasattr(novel, 'url'):
                            url = novel.url
                        if hasattr(novel, 'title'):
                            title = novel.title
                        
                        if url and title:
                            results.append({
                                'title': title,
                                'url': url,
                                'site': str(origin)
                            })
                    except Exception:
                        # Skip malformed results
                        continue
            
            if progress_callback:
                progress_callback(100, 100, f"Found {len(results)} results")

            return results
            
        except Exception as e:
            if LNException and isinstance(e, LNException):
                raise
            raise RuntimeError(f"Search error: {str(e)}")

    def _run_crawler_sync(self, url: str, progress_callback, max_chapters: int = None) -> CrawledNovel:
        """
        Run lightnovel-crawler synchronously using programmatic API.
        
        This integrates with lncrawl's crawler directly without using CLI.
        
        Args:
            url: Novel URL to download
            progress_callback: Callback for progress updates
            max_chapters: Optional limit on number of chapters to download (for testing)
        """
        import threading
        import time
        import sys
        
        if progress_callback:
            progress_callback(0, 100, "Initializing lightnovel-crawler...")

        try:
            # Temporarily override sys.argv to avoid argparse conflicts with pytest
            original_argv = sys.argv
            sys.argv = ['lncrawl']
            
            # Load sources first (required for download to work)
            from lncrawl.core.sources import load_sources
            load_sources()
            
            # Restore original argv
            sys.argv = original_argv
            
            # Create the app instance
            app = LNCrawlApp()
            
            # Set up novel URL
            app.user_input = url
            app.output_path = self.temp_dir
            
            # Configure output formats - we'll use JSON for easy parsing
            app.output_formats = {'json'}
            
            # Download all chapters
            app.pack_by_volume = False
            
            if progress_callback:
                progress_callback(10, 100, "Searching for crawler/support...")

            # Prepare and search for appropriate crawler/site adapter
            app.prepare_search()
            app.search_novel()
            
            # Check if search found any results
            if not hasattr(app, 'crawler') or not app.crawler:
                raise RuntimeError(
                    f"No results for: {url}\n\n"
                    "This could mean:\n"
                    "1. The site is not in lightnovel-crawler's database\n"
                    "2. The URL format is incorrect\n"
                    "3. The novel doesn't exist at this URL\n\n"
                    "Falling back to generic crawler..."
                )

            # Limit chapters if max_chapters is specified
            if max_chapters is not None and (crawler := getattr(app, 'crawler', None)):
                original_chapters = getattr(crawler, 'chapters', [])
                if len(original_chapters) > max_chapters:
                    crawler.chapters = original_chapters[:max_chapters]
                    if progress_callback:
                        progress_callback(20, 100, f"Limited to first {max_chapters} chapters for testing")

            if progress_callback:
                progress_callback(30, 100, "Downloading chapters...")

            # Create signal for graceful interruption
            signal = threading.Event()
            
            # Start download in a thread so we can monitor progress
            download_thread = threading.Thread(
                target=lambda: app.start_download(signal=signal)
            )
            download_thread.daemon = True
            download_thread.start()
            
            # Monitor progress while downloading
            last_reported_progress = 0
            while download_thread.is_alive():
                try:
                    # Get current progress
                    novel_progress = getattr(app, 'fetch_novel_progress', 0) or 0
                    chapter_progress = getattr(app, 'fetch_chapter_progress', 0) or 0
                    images_progress = getattr(app, 'fetch_images_progress', 0) or 0
                    
                    # Combine progress (novel 40%, chapters 40%, images 20%)
                    combined_progress = (novel_progress * 0.4) + (chapter_progress * 0.4) + (images_progress * 0.2)
                    combined_progress = min(combined_progress, 99)  # Never reach 100% until complete
                    
                    # Only report if significantly changed (avoid too many updates)
                    if combined_progress - last_reported_progress >= 1:
                        if progress_callback:
                            progress_callback(
                                30 + int(combined_progress * 0.5),  # Map to 30-80 range
                                100,
                                f"Downloading chapters... ({int(combined_progress)}%)"
                            )
                        last_reported_progress = combined_progress
                    
                    time.sleep(0.5)  # Check progress every 500ms
                except Exception:
                    # If we can't get progress, just wait
                    time.sleep(1)
            
            # Wait for thread to fully complete
            download_thread.join(timeout=5)
            
            if progress_callback:
                progress_callback(80, 100, "Processing downloaded content...")
            
            # Extract the novel from JSON output
            novel = self._extract_novel_from_json()
            
            if progress_callback:
                progress_callback(100, 100, "Complete!")
            
            return novel
            
        except Exception as e:
            # Check if it's an unsupported site error from lncrawl
            if LNException and isinstance(e, LNException):
                raise RuntimeError(
                    f"Site not supported by lightnovel-crawler. {str(e)}\n\n"
                    "Check supported sites via Help > View Supported Sites in the app."
                )
            raise RuntimeError(f"Failed to crawl novel: {str(e)}")

    def _extract_novel_from_json(self) -> CrawledNovel:
        """
        Parse lightnovel-crawler's JSON output into our standardized format.
        
        lncrawl creates a JSON file with structured chapter data which is
        much easier to parse than text files.
        """
        temp_path = Path(self.temp_dir)
        
        # Find the novel directory (usually there's only one)
        novel_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
        
        if not novel_dirs:
            raise ValueError("No novel data found in crawler output")
        
        novel_dir = novel_dirs[0]
        novel_title = novel_dir.name
        
        # Find the JSON file
        json_files = list(novel_dir.glob('*.json'))
        
        if not json_files:
            raise ValueError("No JSON file found in crawler output")
        
        # Read the JSON data
        with open(json_files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract chapters from JSON structure
        chapters = []
        
        # lncrawl JSON structure typically has a 'chapters' array
        chapters_data = data.get('chapters', [])
        
        for idx, chapter_data in enumerate(chapters_data, 1):
            # Extract chapter info from JSON
            title = chapter_data.get('title', f'Chapter {idx}')
            # Content might be in 'body' or 'content' field
            content = chapter_data.get('body') or chapter_data.get('content', '')
            url = chapter_data.get('url')
            
            chapter = CrawledChapter(
                title=title,
                content=content,
                chapter_number=idx,
                url=url
            )
            chapters.append(chapter)
        
        # Get author from metadata if available
        author = data.get('author') or data.get('novel_author')
        
        return CrawledNovel(
            title=novel_title,
            author=author,
            chapters=chapters
        )

    def supports_url(self, url: str) -> bool:
        """
        Check if lightnovel-crawler supports this URL with robust domain matching.
        
        Strategy:
        - Parse the URL's netloc (domain) and compare against each source's homes.
        - Treat a source as supporting the URL if the URL's netloc equals or endswith
          any home domain (handles subdomains like www., m., etc.).
        - As a secondary check, look for any home URL substring in the full URL.
        """
        if not LIGHTNOVEL_CRAWLER_AVAILABLE:
            return False

        try:
            from urllib.parse import urlparse
            from lncrawl.core.sources import crawler_list

            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if not netloc:
                return False

            for crawler in crawler_list:
                try:
                    homes = getattr(crawler, 'home', [])
                    if not isinstance(homes, list):
                        continue
                    for home in homes:
                        if not home:
                            continue
                        home_str = str(home).lower()
                        # Extract domain if home is a full URL, else treat as domain/pattern
                        domain = None
                        if home_str.startswith('http://') or home_str.startswith('https://'):
                            try:
                                domain = urlparse(home_str).netloc.lower()
                            except Exception:
                                domain = None
                        else:
                            domain = home_str

                        # Domain match (handles subdomains)
                        if domain and (netloc == domain or netloc.endswith('.' + domain)):
                            return True
                        # Fallback: substring match on full URL
                        if home_str and home_str in url.lower():
                            return True
                except Exception:
                    continue

            return False
        except Exception:
            # Be conservative: unknown error → not supported
            return False

    def get_supported_sites(self) -> List[str]:
        """
        Return a user-friendly list of supported sites.
        
        Format: "domain (SourceName)" from dynamic crawler list, or the comprehensive
        list from supported_sites.py as fallback.
        Results are cached per instance for performance.
        """
        if not LIGHTNOVEL_CRAWLER_AVAILABLE:
            # If lightnovel-crawler is not available, use the comprehensive fallback
            return get_supported_sites_formatted()

        # Simple per-instance cache
        cache_attr = '_supported_sites_cache'
        cached = getattr(self, cache_attr, None)
        if isinstance(cached, list) and cached:
            return cached

        try:
            from urllib.parse import urlparse
            from lncrawl.core.sources import crawler_list

            entries = {}
            for crawler in crawler_list:
                try:
                    homes = getattr(crawler, 'home', [])
                    if not isinstance(homes, list):
                        continue
                    # Use class name as source label
                    label = getattr(crawler, '__name__', 'UnknownSource')
                    for home in homes:
                        if not home:
                            continue
                        home_str = str(home)
                        domain = None
                        if home_str.startswith('http://') or home_str.startswith('https://'):
                            try:
                                domain = urlparse(home_str).netloc
                            except Exception:
                                domain = None
                        else:
                            domain = home_str
                        if domain:
                            # Keep the first label encountered for the domain
                            entries.setdefault(domain, label)
                except Exception:
                    continue

        
            # Build formatted list and sort
            result = [f"{d} ({entries[d]})" for d in entries.keys()]
            result.sort(key=lambda s: s.lower())

            # Fallback to comprehensive list if empty or use dynamic list if we got results
            if not result:
                result = get_supported_sites_formatted()

            # Cache and return
            setattr(self, cache_attr, result)
            return result
        except Exception:
            # Use comprehensive fallback list if dynamic fetching fails
            return get_supported_sites_formatted()
