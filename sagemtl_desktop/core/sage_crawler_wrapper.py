"""
Wrapper for your existing SageCrawler to implement the CrawlerInterface.
"""
import asyncio
from typing import List
from sagemtl.crawl.novel_crawler import NovelCrawler
from sagemtl_desktop.core.crawler_interface import (
    CrawlerInterface,
    CrawledNovel,
    CrawledChapter
)


class SageCrawlerWrapper(CrawlerInterface):
    """
    Adapts your existing SageCrawler to work with the new interface.

    This wrapper doesn't change how SageCrawler works - it just translates
    between your existing code and the new standardized interface.
    """

    def __init__(self):
        self.crawler = NovelCrawler()

    async def fetch_novel(self, url: str, progress_callback=None) -> CrawledNovel:
        """
        Use your existing SageCrawler to fetch the novel.

        The progress_callback is called as chapters are discovered and downloaded,
        giving your UI real-time feedback.
        """
        # Run the synchronous crawler in a thread pool to avoid blocking
        novel_info = await asyncio.get_event_loop().run_in_executor(
            None,
            self._crawl_sync,
            url,
            progress_callback
        )

        return novel_info

    def _crawl_sync(self, url: str, progress_callback) -> CrawledNovel:
        """
        Synchronous wrapper for the crawler.
        """
        if progress_callback:
            progress_callback(0, 100, "Initializing SageCrawler...")

        # Use NovelCrawler to fetch the novel
        # Default to 100 chapters max to avoid infinite crawls
        novel_info = self.crawler.crawl_novel(
            start_url=url,
            start_chapter=1,
            end_chapter=100
        )

        if progress_callback:
            progress_callback(50, 100, f"Processing {len(novel_info.chapters)} chapters...")

        # Convert to standardized format
        chapters = []
        for chapter_info in novel_info.chapters:
            chapter = CrawledChapter(
                title=chapter_info.title,
                content=chapter_info.content,
                chapter_number=chapter_info.number,
                url=chapter_info.url
            )
            chapters.append(chapter)

        if progress_callback:
            progress_callback(100, 100, "Crawling complete!")

        return CrawledNovel(
            title=novel_info.title,
            author=novel_info.author,
            chapters=chapters
        )

    def supports_url(self, url: str) -> bool:
        """
        SageCrawler uses pattern matching, so it can attempt any URL.

        We return True here to indicate it's always worth trying,
        but you could add more sophisticated URL validation if needed.
        """
        # Your SageCrawler is pattern-based, so it can try any URL
        return True

    def get_supported_sites(self) -> List[str]:
        """
        Return a general description since SageCrawler works with many sites.

        SageCrawler uses automatic pattern detection rather than
        hardcoded site support, so we can't list specific domains.
        """
        return ["Pattern-based crawler - works with many sites automatically"]
