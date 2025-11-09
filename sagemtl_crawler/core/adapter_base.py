"""
Base adapter protocol for site-specific crawlers
"""

from typing import Protocol, List, Optional
from .models import SearchHit, NovelTOC, ChapterRef, ChapterContent


class BaseAdapter(Protocol):
    """Protocol that all site adapters must implement"""

    @property
    def name(self) -> str:
        """Adapter name (e.g., 'fanmtl', 'wuxiaworld')"""
        ...

    def can_handle(self, url: str) -> bool:
        """Check if this adapter can handle the given URL"""
        ...

    async def search(self, query: str, limit: int = 20) -> List[SearchHit]:
        """
        Search for novels matching the query.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of search hits
        """
        ...

    async def get_toc(self, url: str) -> NovelTOC:
        """
        Get table of contents for a novel.

        Args:
            url: Novel page URL

        Returns:
            Novel TOC with chapters, metadata, etc.
        """
        ...

    async def get_chapter(self, chapter: ChapterRef) -> ChapterContent:
        """
        Download a single chapter.

        Args:
            chapter: Chapter reference

        Returns:
            Chapter content with HTML and text
        """
        ...


class AdapterRegistry:
    """Registry for site adapters"""

    def __init__(self):
        self._adapters: List[BaseAdapter] = []

    def register(self, adapter: BaseAdapter):
        """Register an adapter"""
        self._adapters.append(adapter)

    def get_adapter(self, url: str) -> Optional[BaseAdapter]:
        """Get the appropriate adapter for a URL"""
        for adapter in self._adapters:
            if adapter.can_handle(url):
                return adapter
        return None

    def get_all_adapters(self) -> List[BaseAdapter]:
        """Get all registered adapters"""
        return self._adapters.copy()

    def search_all(self, query: str, limit: int = 20) -> List[SearchHit]:
        """Search across all adapters"""
        # Note: This would need to be async in practice
        # For now, this is a placeholder
        results = []
        for adapter in self._adapters:
            try:
                hits = adapter.search(query, limit)
                results.extend(hits)
            except Exception as e:
                print(f"Search failed for {adapter.name}: {e}")
        return results[:limit]


# Global registry instance
registry = AdapterRegistry()
