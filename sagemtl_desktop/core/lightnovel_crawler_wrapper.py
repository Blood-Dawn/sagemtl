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
    LIGHTNOVEL_CRAWLER_AVAILABLE = True
except ImportError as e:
    # Store the error for debugging
    _import_error = str(e)
except Exception as e:
    # Catch any other errors during import
    _import_error = f"Unexpected error: {str(e)}"


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
                progress_callback(10, 100, "Fetching novel information...")
            
            # Initialize the app
            app.init_search()
            
            if progress_callback:
                progress_callback(30, 100, "Downloading chapters...")
            
            # Start downloading
            app.start_download()
            
            if progress_callback:
                progress_callback(80, 100, "Processing downloaded content...")
            
            # Extract the novel from JSON output
            novel = self._extract_novel_from_json()
            
            if progress_callback:
                progress_callback(100, 100, "Complete!")
            
            return novel
            
        except Exception as e:
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
        Check if lightnovel-crawler supports this URL.
        
        lncrawl has a crawler registry we can query to check URL support.
        """
        if not LIGHTNOVEL_CRAWLER_AVAILABLE:
            return False
        
        try:
            from lncrawl.core.sources import crawler_list
            
            # Check if any crawler can handle this URL
            for crawler in crawler_list:
                # Each crawler class has a method to check if it supports a URL
                try:
                    if hasattr(crawler, 'home') and isinstance(crawler.home, list):
                        # crawler.home contains list of supported URLs/patterns
                        for home_url in crawler.home:
                            if home_url in url:
                                return True
                except (AttributeError, TypeError):
                    continue
            
            return False
        except Exception:
            # If we can't check, be optimistic and return True
            # lncrawl supports 460+ sites, so chances are good
            return True

    def get_supported_sites(self) -> List[str]:
        """
        Return a list of sites supported by lightnovel-crawler.
        
        lncrawl supports 460+ sites across multiple languages.
        """
        if not LIGHTNOVEL_CRAWLER_AVAILABLE:
            return []
        
        try:
            from lncrawl.core.sources import crawler_list
            
            sites = set()
            for crawler in crawler_list:
                try:
                    if hasattr(crawler, 'home') and isinstance(crawler.home, list):
                        for home_url in crawler.home:
                            # Extract domain from URL
                            if 'http' in home_url:
                                # Parse domain from full URL
                                import re
                                match = re.search(r'https?://([^/]+)', home_url)
                                if match:
                                    sites.add(match.group(1))
                            else:
                                sites.add(home_url)
                except (AttributeError, TypeError):
                    continue
            
            # Return sorted list
            return sorted(sites) if sites else ["460+ sites supported"]
        except Exception:
            return ["460+ sites supported (lightnovel-crawler)"]
