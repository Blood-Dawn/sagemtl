"""
Wrapper for lightnovel-crawler to implement the CrawlerInterface.

This allows your app to use lightnovel-crawler's extensive site support
while maintaining GPL v3 compliance (it's a separate dependency, not
incorporated code).
"""
import asyncio
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List
from sagemtl_desktop.core.crawler_interface import (
    CrawlerInterface,
    CrawledNovel,
    CrawledChapter
)

# Try to import lightnovel-crawler, but don't fail if it's not installed
# This allows your app to work even if users haven't installed the optional dependency
ln_arguments = None
try:
    from lncrawl.core.app import App as LNCrawlApp
    from lncrawl.core import arguments as ln_arguments
    from lncrawl.core.arguments import get_args
    LIGHTNOVEL_CRAWLER_AVAILABLE = True
except ImportError:
    LIGHTNOVEL_CRAWLER_AVAILABLE = False


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

        The challenge here is that lightnovel-crawler runs synchronously and
        expects to write files. We wrap it in asyncio to keep your UI responsive
        and extract the content from the files it creates.
        """
        # Create a temporary directory for this crawl operation
        self.temp_dir = tempfile.mkdtemp(prefix='sagemtl_lncrawl_')

        try:
            # Run the crawler in a thread pool to avoid blocking your UI
            # lightnovel-crawler is synchronous, so we need this wrapper
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
        Run lightnovel-crawler synchronously.

        This is the core integration point. We're essentially automating
        what would normally be command-line arguments to lightnovel-crawler.
        """
        # Prepare arguments for lightnovel-crawler
        # We're simulating: lncrawl -s URL -o OUTPUT_PATH --format txt --all --suppress
        args_list = [
            '-s', url,  # Source URL
            '-o', self.temp_dir,  # Output directory
            '--format', 'txt',  # Text format for easy parsing
            '--all',  # Download all chapters
            '--suppress',  # No interactive prompts
            '--close-directly'  # Don't wait for user input at the end
        ]

        # Parse arguments using lightnovel-crawler's argument parser
        args = self._build_arguments(args_list)

        # Create and run the crawler app
        app = LNCrawlApp()
        app.initialize(args)

        # Progress tracking is tricky with lightnovel-crawler since it doesn't
        # expose a callback API. We'll call the callback at key milestones instead.
        if progress_callback:
            progress_callback(0, 100, "Initializing lightnovel-crawler...")

        # Start the crawling process
        app.start()

        if progress_callback:
            progress_callback(50, 100, "Crawling chapters...")

        # After crawling completes, read the output files
        # lightnovel-crawler creates a directory structure like:
        # temp_dir/
        #   NovelName/
        #     NovelName.txt (all chapters in one file)
        novel = self._extract_novel_from_output()

        if progress_callback:
            progress_callback(100, 100, "Crawling complete!")

        return novel

    def _extract_novel_from_output(self) -> CrawledNovel:
        """
        Parse lightnovel-crawler's output files into our standardized format.

        lightnovel-crawler creates a directory for each novel and saves
        chapters in various formats. We read the TXT format because it's
        simplest to parse.
        """
        temp_path = Path(self.temp_dir)

        # Find the novel directory (usually there's only one)
        novel_dirs = [d for d in temp_path.iterdir() if d.is_dir()]

        if not novel_dirs:
            raise ValueError("No novel data found in crawler output")

        novel_dir = novel_dirs[0]
        novel_title = novel_dir.name

        # Find the TXT file (format: NovelName.txt)
        txt_files = list(novel_dir.glob('*.txt'))

        if not txt_files:
            raise ValueError("No text file found in crawler output")

        # Read the combined text file
        # lightnovel-crawler puts all chapters in one file with markers
        with open(txt_files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse chapters from the combined text
        # lightnovel-crawler uses specific patterns to separate chapters
        chapters = self._parse_chapters_from_text(content)

        return CrawledNovel(
            title=novel_title,
            author=None,  # Could extract from metadata if available
            chapters=chapters
        )

    def _build_arguments(self, args_list):
        """Construct the argparse namespace expected by lightnovel-crawler."""
        previous_argv = list(sys.argv)
        previous_namespace = ln_arguments._builder.arguments
        try:
            sys.argv = ['lncrawl'] + args_list
            ln_arguments._builder.arguments = None
            return get_args()
        finally:
            sys.argv = previous_argv
            ln_arguments._builder.arguments = previous_namespace

    def _parse_chapters_from_text(self, text: str) -> List[CrawledChapter]:
        """
        Split the combined text file into individual chapters.

        lightnovel-crawler typically formats chapters like:

        ═══════════════════════════════════════════
        Chapter 1: Title Here
        ═══════════════════════════════════════════

        Chapter content here...

        We use these separators to split the file.
        """
        chapters = []

        # Split by the separator pattern lightnovel-crawler uses
        # This pattern might need adjustment based on actual output format
        chapter_splits = text.split('═══════════════════════════════════════════')

        chapter_num = 1
        for i in range(1, len(chapter_splits), 2):
            if i + 1 < len(chapter_splits):
                # The odd indices contain chapter titles
                title_line = chapter_splits[i].strip()
                # The even indices contain chapter content
                content = chapter_splits[i + 1].strip()

                chapter = CrawledChapter(
                    title=title_line if title_line else f"Chapter {chapter_num}",
                    content=content,
                    chapter_number=chapter_num,
                    url=None  # lightnovel-crawler doesn't preserve individual URLs in output
                )
                chapters.append(chapter)
                chapter_num += 1

        # Fallback: if the parsing didn't work, treat the whole text as one chapter
        if not chapters:
            chapters.append(CrawledChapter(
                title="Complete Novel",
                content=text,
                chapter_number=1,
                url=None
            ))

        return chapters

    def supports_url(self, url: str) -> bool:
        """
        Check if lightnovel-crawler supports this URL.

        lightnovel-crawler has a registry of supported sites. We query it
        to determine if the URL matches any known crawler patterns.
        """
        if not LIGHTNOVEL_CRAWLER_AVAILABLE:
            return False

        try:
            # lightnovel-crawler has a source registry we can check
            from lncrawl.core.sources import crawler_list

            # Check if any crawler matches this URL
            for crawler_info in crawler_list:
                # Each crawler has a 'domain' or 'urls' list we can check against
                # This is a simplified check - actual implementation might need refinement
                if hasattr(crawler_info, 'domain'):
                    if crawler_info.domain in url:
                        return True

            return False
        except Exception:
            # If there's any error checking, assume it might work
            return True

    def get_supported_sites(self) -> List[str]:
        """
        Return the list of sites supported by lightnovel-crawler.

        lightnovel-crawler supports 455+ sites. We extract this list
        from their source registry.
        """
        if not LIGHTNOVEL_CRAWLER_AVAILABLE:
            return []

        try:
            from lncrawl.core.sources import crawler_list

            sites = []
            for crawler_info in crawler_list:
                if hasattr(crawler_info, 'domain'):
                    sites.append(crawler_info.domain)
                elif hasattr(crawler_info, 'base_url'):
                    # Extract domain from base_url
                    import re
                    match = re.search(r'https?://([^/]+)', crawler_info.base_url)
                    if match:
                        sites.append(match.group(1))

            return sorted(set(sites))  # Remove duplicates and sort
        except Exception as e:
            return [f"455+ sites (error loading list: {str(e)})"]
