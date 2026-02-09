"""
Abstraction layer for different crawler implementations.
Provides a stable contract for crawler wrappers used by the desktop app.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CrawledChapter:
    """
    Standardized chapter data structure.

    Both crawlers will return data in this format, making it easy
    for the rest of your application to process chapters regardless
    of which crawler fetched them.
    """
    title: str
    content: str
    chapter_number: Optional[int] = None
    url: Optional[str] = None


@dataclass
class CrawledNovel:
    """
    Standardized novel metadata structure.

    Contains overall information about the novel being crawled.
    """
    title: str
    author: Optional[str] = None
    chapters: List[CrawledChapter] = None

    def __post_init__(self):
        if self.chapters is None:
            self.chapters = []


class CrawlerInterface(ABC):
    """
    Abstract base class that all crawler implementations must follow.

    This ensures that your UI and job manager can work with any crawler
    without knowing the specific implementation details. It's like having
    a universal remote that works with any TV brand.
    """

    @abstractmethod
    async def fetch_novel(
        self,
        url: str,
        progress_callback=None,
        max_chapters: Optional[int] = None
    ) -> CrawledNovel:
        """
        Fetch a complete novel from the given URL.

        Args:
            url: The URL to the novel or first chapter
            progress_callback: Optional function to call with progress updates
                             Should accept (current, total, message) parameters
            max_chapters: Optional chapter cap used by UI/tests for bounded downloads

        Returns:
            CrawledNovel object with all chapters
        """
        pass

    @abstractmethod
    def supports_url(self, url: str) -> bool:
        """
        Check if this crawler can handle the given URL.

        This allows your app to automatically suggest which crawler
        to use, or even automatically fall back to the other crawler
        if one doesn't support a particular site.

        Args:
            url: The URL to check

        Returns:
            True if this crawler can handle the URL, False otherwise
        """
        pass

    @abstractmethod
    def get_supported_sites(self) -> List[str]:
        """
        Return a list of supported site domains.

        This is useful for showing users which sites each crawler supports,
        helping them make an informed choice.

        Returns:
            List of domain names (e.g., ['wuxiaworld.com', 'royalroad.com'])
        """
        pass

    @abstractmethod
    async def discover_chapters(
        self,
        url: str,
        progress_callback=None
    ) -> Tuple[str, Optional[str], List[Tuple[str, str]]]:
        """
        Discover chapter links for a novel URL.

        Args:
            url: Novel URL to inspect
            progress_callback: Optional function(current, total, message)

        Returns:
            Tuple of (title, author, chapter_links) where chapter_links is
            a list of (url, title) tuples.
        """
        pass

    @abstractmethod
    async def fetch_selected_chapters(
        self,
        url: str,
        title: str,
        author: Optional[str],
        selected_chapters: List[Tuple[str, str]],
        progress_callback=None
    ) -> CrawledNovel:
        """
        Download only a selected set of chapter links for a novel.

        Args:
            url: Source novel URL
            title: Novel title
            author: Novel author (if available)
            selected_chapters: List of (chapter_url, chapter_title)
            progress_callback: Optional function(current, total, message)

        Returns:
            CrawledNovel with downloaded chapter content.
        """
        pass
