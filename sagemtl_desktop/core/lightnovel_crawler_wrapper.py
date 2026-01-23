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
from typing import List, Optional, Dict, Any
from sagemtl_desktop.core.crawler_interface import (
    CrawlerInterface,
    CrawledNovel,
    CrawledChapter
)

# Try to import lightnovel-crawler, but don't fail if it's not installed
# This allows your app to work even if users haven't installed the optional dependency
LIGHTNOVEL_CRAWLER_AVAILABLE = False
try:
    from lncrawl.core.app import App as LNCrawlApp
    from lncrawl.core.arguments import get_args
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

    def __init__(self):
        if not LIGHTNOVEL_CRAWLER_AVAILABLE:
            raise ImportError(
                "lightnovel-crawler is not installed. "
                "Install it with: pip install lightnovel-crawler"
            )

        # We'll use a temporary directory for lightnovel-crawler's output
        # then read it back into memory. This is necessary because lightnovel-crawler
        # was designed to save files rather than return data in memory.
        self.temp_dir = None

    async def fetch_novel(self, url: str, progress_callback=None) -> CrawledNovel:
        """
        Use lightnovel-crawler to fetch the novel.

        This method integrates with lncrawl's API to download novels.
        It uses JSON format for easy parsing of structured chapter data.
        """
        # Create a temporary directory for this crawl operation
        self.temp_dir = tempfile.mkdtemp(prefix='sagemtl_lncrawl_')

        try:
            # Run the crawler in a thread pool to avoid blocking your UI
            novel = await asyncio.get_event_loop().run_in_executor(
                None,
                self._run_crawler_sync,
                url,
                progress_callback
            )
            return novel
        finally:
            # Clean up temporary files
            if self.temp_dir and Path(self.temp_dir).exists():
                shutil.rmtree(self.temp_dir)

    def _run_crawler_sync(self, url: str, progress_callback) -> CrawledNovel:
        """
        Run lightnovel-crawler synchronously using programmatic API.
        
        This integrates with lncrawl's crawler directly without using CLI.
        """
        if progress_callback:
            progress_callback(0, 100, "Initializing lightnovel-crawler...")

        try:
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

            if progress_callback:
                progress_callback(30, 100, "Downloading chapters...")

            # Start downloading chapters to the output path
            app.start_download()
            
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
                        if domain:
                            if netloc == domain or netloc.endswith('.' + domain):
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
        
        Format: "domain (SourceName)". The list is de-duplicated and sorted.
        Results are cached per instance for performance.
        """
        if not LIGHTNOVEL_CRAWLER_AVAILABLE:
            return []

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

            # Fallback text if empty
            if not result:
                result = ["460+ sites supported (lightnovel-crawler)"]

            # Cache and return
            setattr(self, cache_attr, result)
            return result
        except Exception:
            return ["460+ sites supported (lightnovel-crawler)"]
