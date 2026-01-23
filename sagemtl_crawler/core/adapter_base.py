"""
Base adapter protocol for site-specific crawlers with enhanced capabilities
"""

from typing import Protocol, List, Optional, Dict, Any, Type, runtime_checkable
from dataclasses import dataclass, field
from enum import Flag, auto
from pathlib import Path
import importlib
import pkgutil
from urllib.parse import urlparse

from .models import SearchHit, NovelTOC, ChapterRef, ChapterContent


class SiteCapability(Flag):
    """Capabilities that a site adapter may support"""
    SEARCH = auto()           # Can search for novels
    DIRECT_URL = auto()       # Can crawl from direct novel URL
    LOGIN = auto()            # Supports authenticated access
    VOLUMES = auto()          # Has volume structure
    IMAGES = auto()           # Contains chapter images
    AJAX = auto()             # Requires JavaScript/AJAX handling
    CLOUDFLARE = auto()       # Protected by Cloudflare


@dataclass
class AdapterInfo:
    """Information about a site adapter"""
    name: str
    display_name: str
    base_url: str
    supported_domains: List[str]
    capabilities: SiteCapability
    description: str = ""
    requires_login: bool = False
    rate_limit: float = 0.5  # Seconds between requests


@runtime_checkable
class BaseAdapter(Protocol):
    """Protocol that all site adapters must implement"""

    @classmethod
    def get_info(cls) -> AdapterInfo:
        """Get adapter information"""
        ...

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
    """Registry for site adapters with auto-discovery"""

    _instance: Optional['AdapterRegistry'] = None
    _adapters: Dict[str, Type[BaseAdapter]] = {}
    _domain_map: Dict[str, str] = {}  # domain -> adapter name
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._adapters = {}
            self._domain_map = {}
            AdapterRegistry._initialized = True

    def register(self, adapter_class: Type[BaseAdapter]) -> None:
        """Register an adapter class"""
        try:
            info = adapter_class.get_info()
            self._adapters[info.name] = adapter_class

            # Map all supported domains to this adapter
            for domain in info.supported_domains:
                # Normalize domain
                domain = domain.lower().replace('www.', '')
                self._domain_map[domain] = info.name

        except Exception as e:
            print(f"Warning: Failed to register adapter {adapter_class}: {e}")

    def get_adapter_class(self, url: str) -> Optional[Type[BaseAdapter]]:
        """Get the appropriate adapter class for a URL"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')

        # Try exact match
        if domain in self._domain_map:
            adapter_name = self._domain_map[domain]
            return self._adapters.get(adapter_name)

        # Try subdomain matching
        for registered_domain, adapter_name in self._domain_map.items():
            if domain.endswith(registered_domain) or registered_domain.endswith(domain):
                return self._adapters.get(adapter_name)

        return None

    def get_adapter(self, name: str) -> Optional[Type[BaseAdapter]]:
        """Get adapter class by name"""
        return self._adapters.get(name)

    def get_adapter_by_name(self, name: str) -> Optional[Type[BaseAdapter]]:
        """Get adapter class by name (alias)"""
        return self._adapters.get(name)

    def get_adapter_for_url(self, url: str, fetcher=None) -> Optional[BaseAdapter]:
        """
        Get an instantiated adapter for a URL.

        Args:
            url: URL to find adapter for
            fetcher: Optional fetcher to pass to adapter

        Returns:
            Instantiated adapter or None if no adapter found
        """
        adapter_class = self.get_adapter_class(url)
        if adapter_class:
            return adapter_class(fetcher)
        return None

    def get_all_adapters(self) -> List[Type[BaseAdapter]]:
        """Get all registered adapter classes"""
        return list(self._adapters.values())

    def list_adapters(self) -> List[AdapterInfo]:
        """List all registered adapters with their info"""
        result = []
        for name, adapter_class in self._adapters.items():
            try:
                info = adapter_class.get_info()
                result.append(info)
            except Exception:
                continue
        return result

    def list_adapters_dict(self) -> List[Dict[str, Any]]:
        """List all registered adapters as dictionaries"""
        result = []
        for name, adapter_class in self._adapters.items():
            try:
                info = adapter_class.get_info()
                result.append({
                    'name': info.name,
                    'display_name': info.display_name,
                    'base_url': info.base_url,
                    'domains': info.supported_domains,
                    'capabilities': [c.name for c in SiteCapability if c in info.capabilities],
                    'description': info.description,
                    'requires_login': info.requires_login,
                })
            except Exception:
                continue
        return result

    async def search_all(self, query: str, limit: int = 20, fetcher=None) -> List[SearchHit]:
        """Search across all adapters that support search"""
        results = []

        for adapter_class in self._adapters.values():
            try:
                info = adapter_class.get_info()
                if SiteCapability.SEARCH not in info.capabilities:
                    continue

                adapter = adapter_class(fetcher) if fetcher else adapter_class(None)
                hits = await adapter.search(query, limit)
                results.extend(hits)

            except Exception as e:
                print(f"Search failed for {adapter_class}: {e}")
                continue

        # Sort by relevance (if available) and limit
        return results[:limit]

    def discover_adapters(self, package_name: str = 'sagemtl_crawler.sites') -> int:
        """
        Auto-discover and register adapters from a package.

        Args:
            package_name: The package to scan for adapters

        Returns:
            Number of adapters discovered
        """
        count = 0

        try:
            package = importlib.import_module(package_name)
            package_path = Path(package.__file__).parent

            for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
                if module_name.startswith('_'):
                    continue

                try:
                    module = importlib.import_module(f'{package_name}.{module_name}')

                    # Look for adapter classes in the module
                    for attr_name in dir(module):
                        if attr_name.startswith('_'):
                            continue

                        attr = getattr(module, attr_name)

                        # Check if it's a class with get_info method
                        if (isinstance(attr, type) and
                            hasattr(attr, 'get_info') and
                            hasattr(attr, 'can_handle') and
                            attr_name.endswith('Adapter')):

                            self.register(attr)
                            count += 1

                except Exception as e:
                    print(f"Warning: Failed to load module {module_name}: {e}")
                    continue

        except ImportError as e:
            print(f"Warning: Could not import package {package_name}: {e}")

        return count


# Global registry instance
registry = AdapterRegistry()


def register_adapter(adapter_class: Type[BaseAdapter]) -> Type[BaseAdapter]:
    """Decorator to register an adapter class"""
    registry.register(adapter_class)
    return adapter_class
