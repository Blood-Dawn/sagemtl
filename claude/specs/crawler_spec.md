# Crawler Module Specification

## Overview

The crawler module replaces external LNCrawl dependency with a built-in Python crawler that can fetch light novel content from public sources. It handles multiple websites, supports searching by novel name or direct URLs, intelligently parses chapters with volume/chapter structure, and saves novels in various e-book formats.

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Crawler Module                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  CrawlerEngine   │───►│  AdapterRegistry │───►│ Site Adapters │  │
│  │  (Orchestrator)  │    │  (Plugin Loader) │    │ (Per-Site)    │  │
│  └────────┬─────────┘    └──────────────────┘    └───────────────┘  │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │   HTTPFetcher    │    │   TOCParser      │    │ ContentParser │  │
│  │   (Rate-limited) │    │   (Structure)    │    │ (Extraction)  │  │
│  └──────────────────┘    └──────────────────┘    └───────────────┘  │
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐                       │
│  │   JobManager     │    │   ChapterStore   │                       │
│  │   (Queue/Resume) │    │   (Persistence)  │                       │
│  └──────────────────┘    └──────────────────┘                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input (URL/Search)
        │
        ▼
┌───────────────┐
│ AdapterSelect │ ─── Match domain to adapter
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Novel Metadata│ ─── Fetch title, author, cover
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   TOC Parse   │ ─── Extract chapter list, volumes
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Chapter Queue │ ─── Create download jobs
└───────┬───────┘
        │
        ▼ (concurrent)
┌───────────────┐
│ Fetch Chapter │ ─── HTTP request + parse
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Store HTML   │ ─── Save to disk
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   Compile     │ ─── Generate output formats
└───────────────┘
```

---

## Core Components

### 1. AdapterBase Protocol

```python
# Location: sagemtl_crawler/core/adapter_base.py

from typing import Protocol, Optional, List, AsyncIterator
from dataclasses import dataclass
from enum import Enum

class SiteCapability(Enum):
    SEARCH = "search"           # Can search for novels
    DIRECT_URL = "direct_url"   # Can crawl from direct novel URL
    LOGIN = "login"             # Supports authenticated access
    VOLUMES = "volumes"         # Has volume structure
    IMAGES = "images"           # Contains chapter images


@dataclass
class NovelMetadata:
    title: str
    author: Optional[str] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    genres: List[str] = None
    status: Optional[str] = None  # Ongoing, Completed, Hiatus
    source_url: str = ""
    source_language: str = "zh"


@dataclass
class ChapterInfo:
    title: str
    url: str
    chapter_number: int
    volume_number: Optional[int] = None
    volume_title: Optional[str] = None


@dataclass
class ChapterContent:
    info: ChapterInfo
    content: str  # HTML or plain text
    images: List[str] = None  # Image URLs if any


class AdapterBase(Protocol):
    """Protocol for site-specific crawlers."""

    # Class attributes
    site_name: str                          # Human-readable name
    base_url: str                           # Site's base URL
    supported_domains: List[str]            # All valid domains
    capabilities: List[SiteCapability]      # What this adapter can do

    async def search(self, query: str, limit: int = 20) -> List[NovelMetadata]:
        """Search for novels by title/keywords."""
        ...

    async def get_novel_metadata(self, url: str) -> NovelMetadata:
        """Fetch novel metadata from novel page URL."""
        ...

    async def get_chapter_list(self, url: str) -> List[ChapterInfo]:
        """Get all chapters for a novel, preserving volume structure."""
        ...

    async def get_chapter_content(self, chapter: ChapterInfo) -> ChapterContent:
        """Fetch and parse a single chapter's content."""
        ...

    def can_handle(self, url: str) -> bool:
        """Check if this adapter can handle the given URL."""
        ...
```

### 2. Adapter Registry

```python
# Location: sagemtl_crawler/core/adapter_registry.py

import importlib
import pkgutil
from typing import Dict, Optional, Type
from pathlib import Path

class AdapterRegistry:
    """Auto-discovers and manages site adapters."""

    _adapters: Dict[str, Type[AdapterBase]] = {}
    _instances: Dict[str, AdapterBase] = {}

    @classmethod
    def discover_adapters(cls, package_path: str = "sagemtl_crawler.sites"):
        """Auto-discover adapters from the sites package."""
        package = importlib.import_module(package_path)
        package_dir = Path(package.__file__).parent

        for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
            module = importlib.import_module(f"{package_path}.{module_name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    hasattr(attr, 'site_name') and
                    hasattr(attr, 'supported_domains')):
                    cls.register(attr)

    @classmethod
    def register(cls, adapter_class: Type[AdapterBase]):
        """Register an adapter class."""
        for domain in adapter_class.supported_domains:
            cls._adapters[domain] = adapter_class

    @classmethod
    def get_adapter(cls, url: str) -> Optional[AdapterBase]:
        """Get appropriate adapter for a URL."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()

        # Try exact match
        if domain in cls._adapters:
            return cls._get_instance(domain)

        # Try without www.
        domain_no_www = domain.replace('www.', '')
        if domain_no_www in cls._adapters:
            return cls._get_instance(domain_no_www)

        # Try subdomain matching
        for registered_domain, adapter_class in cls._adapters.items():
            if domain.endswith(registered_domain):
                return cls._get_instance(registered_domain)

        return None

    @classmethod
    def _get_instance(cls, domain: str) -> AdapterBase:
        """Get or create adapter instance."""
        if domain not in cls._instances:
            cls._instances[domain] = cls._adapters[domain]()
        return cls._instances[domain]

    @classmethod
    def list_adapters(cls) -> List[Dict]:
        """List all registered adapters."""
        seen = set()
        result = []
        for domain, adapter_class in cls._adapters.items():
            if adapter_class.site_name not in seen:
                seen.add(adapter_class.site_name)
                result.append({
                    'name': adapter_class.site_name,
                    'domains': adapter_class.supported_domains,
                    'capabilities': [c.value for c in adapter_class.capabilities]
                })
        return result
```

### 3. HTTP Fetcher

```python
# Location: sagemtl_crawler/core/fetch_httpx.py

import asyncio
import httpx
from typing import Optional, Dict
from dataclasses import dataclass, field
import time
import random

@dataclass
class FetchConfig:
    """Configuration for HTTP fetching."""
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0  # Exponential backoff multiplier
    request_delay: float = 0.5  # Delay between requests (politeness)
    max_concurrent: int = 5     # Max concurrent requests

    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    ])

    headers: Dict[str, str] = field(default_factory=lambda: {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    })


class PoliteFetcher:
    """HTTP fetcher with rate limiting and retry logic."""

    def __init__(self, config: Optional[FetchConfig] = None):
        self.config = config or FetchConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._last_request_time: Dict[str, float] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            follow_redirects=True,
            http2=True,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with random user agent."""
        headers = self.config.headers.copy()
        headers["User-Agent"] = random.choice(self.config.user_agents)
        return headers

    async def _wait_for_rate_limit(self, domain: str):
        """Ensure minimum delay between requests to same domain."""
        now = time.time()
        last_time = self._last_request_time.get(domain, 0)
        wait_time = self.config.request_delay - (now - last_time)

        if wait_time > 0:
            await asyncio.sleep(wait_time)

        self._last_request_time[domain] = time.time()

    async def fetch(self, url: str) -> str:
        """Fetch URL with retry logic and rate limiting."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        async with self._semaphore:
            await self._wait_for_rate_limit(domain)

            last_error = None
            for attempt in range(self.config.max_retries):
                try:
                    response = await self._client.get(
                        url,
                        headers=self._get_headers()
                    )
                    response.raise_for_status()
                    return response.text

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:  # Rate limited
                        wait = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                        await asyncio.sleep(wait)
                    elif e.response.status_code >= 500:  # Server error
                        wait = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                        await asyncio.sleep(wait)
                    else:
                        raise
                    last_error = e

                except (httpx.ConnectError, httpx.ReadTimeout) as e:
                    wait = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    await asyncio.sleep(wait)
                    last_error = e

            raise last_error or Exception(f"Failed to fetch {url}")
```

### 4. Crawler Engine

```python
# Location: sagemtl_crawler/core/engine.py

import asyncio
from typing import Optional, Callable, List
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass
class CrawlJob:
    """Represents a novel download job."""
    job_id: str
    novel_url: str
    output_dir: Path

    # Progress tracking
    total_chapters: int = 0
    completed_chapters: int = 0
    failed_chapters: List[str] = field(default_factory=list)

    # State
    status: str = "pending"  # pending, running, paused, completed, failed
    metadata: Optional[NovelMetadata] = None
    chapters: List[ChapterInfo] = field(default_factory=list)


class CrawlerEngine:
    """Main crawler orchestrator."""

    def __init__(
        self,
        output_dir: Path,
        fetcher: Optional[PoliteFetcher] = None,
        progress_callback: Optional[Callable[[CrawlJob], None]] = None,
    ):
        self.output_dir = Path(output_dir)
        self.fetcher = fetcher or PoliteFetcher()
        self.progress_callback = progress_callback
        self._jobs: Dict[str, CrawlJob] = {}

    async def crawl_novel(
        self,
        url: str,
        job_id: Optional[str] = None,
        resume: bool = True,
    ) -> CrawlJob:
        """Crawl a novel from URL."""
        # Get appropriate adapter
        adapter = AdapterRegistry.get_adapter(url)
        if not adapter:
            raise ValueError(f"No adapter found for URL: {url}")

        # Create or resume job
        job_id = job_id or self._generate_job_id()
        job = await self._get_or_create_job(job_id, url, resume)

        async with self.fetcher:
            try:
                job.status = "running"

                # Fetch metadata if not already done
                if not job.metadata:
                    job.metadata = await adapter.get_novel_metadata(url)
                    self._save_job_state(job)

                # Fetch chapter list if not already done
                if not job.chapters:
                    job.chapters = await adapter.get_chapter_list(url)
                    job.total_chapters = len(job.chapters)
                    self._save_job_state(job)

                # Setup output directory
                novel_dir = self.output_dir / self._sanitize_filename(job.metadata.title)
                chapters_dir = novel_dir / "chapters"
                chapters_dir.mkdir(parents=True, exist_ok=True)
                job.output_dir = novel_dir

                # Download chapters
                await self._download_chapters(adapter, job, chapters_dir)

                job.status = "completed"
                self._save_job_state(job)

            except Exception as e:
                job.status = "failed"
                self._save_job_state(job)
                raise

        return job

    async def _download_chapters(
        self,
        adapter: AdapterBase,
        job: CrawlJob,
        chapters_dir: Path,
    ):
        """Download all chapters with progress tracking."""
        tasks = []

        for chapter in job.chapters:
            chapter_file = chapters_dir / f"{chapter.chapter_number:04d}.html"

            # Skip if already downloaded (resume support)
            if chapter_file.exists():
                job.completed_chapters += 1
                continue

            tasks.append(
                self._download_chapter(adapter, chapter, chapter_file, job)
            )

        # Process with concurrency limit
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _download_chapter(
        self,
        adapter: AdapterBase,
        chapter: ChapterInfo,
        output_file: Path,
        job: CrawlJob,
    ):
        """Download a single chapter."""
        try:
            content = await adapter.get_chapter_content(chapter)

            # Save as HTML
            html = self._format_chapter_html(content)
            output_file.write_text(html, encoding='utf-8')

            job.completed_chapters += 1
            if self.progress_callback:
                self.progress_callback(job)

        except Exception as e:
            job.failed_chapters.append(chapter.url)

    def _format_chapter_html(self, content: ChapterContent) -> str:
        """Format chapter content as HTML."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{content.info.title}</title>
</head>
<body>
    <h1>{content.info.title}</h1>
    <div class="chapter-content">
        {content.content}
    </div>
</body>
</html>"""

    def _save_job_state(self, job: CrawlJob):
        """Save job state for resume capability."""
        state_file = self.output_dir / ".sagemtl" / f"{job.job_id}.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)

        state = {
            'job_id': job.job_id,
            'novel_url': job.novel_url,
            'status': job.status,
            'total_chapters': job.total_chapters,
            'completed_chapters': job.completed_chapters,
            'failed_chapters': job.failed_chapters,
        }

        if job.metadata:
            state['metadata'] = {
                'title': job.metadata.title,
                'author': job.metadata.author,
                'cover_url': job.metadata.cover_url,
            }

        state_file.write_text(json.dumps(state, indent=2))

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize string for use as filename."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()[:200]

    @staticmethod
    def _generate_job_id() -> str:
        """Generate unique job ID."""
        import uuid
        return str(uuid.uuid4())[:8]
```

---

## Site Adapters

### Example: FanMTL Adapter

```python
# Location: sagemtl_crawler/sites/fanmtl.py

from bs4 import BeautifulSoup
from typing import List, Optional
import re

class FanMTLAdapter:
    """Adapter for fanmtl.com"""

    site_name = "FanMTL"
    base_url = "https://fanmtl.com"
    supported_domains = ["fanmtl.com", "www.fanmtl.com"]
    capabilities = [SiteCapability.DIRECT_URL, SiteCapability.SEARCH, SiteCapability.VOLUMES]

    def __init__(self):
        self.fetcher: Optional[PoliteFetcher] = None

    def can_handle(self, url: str) -> bool:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        return any(d in domain for d in self.supported_domains)

    async def search(self, query: str, limit: int = 20) -> List[NovelMetadata]:
        """Search FanMTL for novels."""
        search_url = f"{self.base_url}/search?q={query}"
        html = await self.fetcher.fetch(search_url)
        soup = BeautifulSoup(html, 'lxml')

        results = []
        for item in soup.select('.novel-item')[:limit]:
            title = item.select_one('.novel-title').text.strip()
            url = item.select_one('a')['href']
            cover = item.select_one('img')['src'] if item.select_one('img') else None

            results.append(NovelMetadata(
                title=title,
                source_url=url if url.startswith('http') else f"{self.base_url}{url}",
                cover_url=cover,
            ))

        return results

    async def get_novel_metadata(self, url: str) -> NovelMetadata:
        """Fetch novel metadata from FanMTL."""
        html = await self.fetcher.fetch(url)
        soup = BeautifulSoup(html, 'lxml')

        title = soup.select_one('h1.novel-title').text.strip()
        author = soup.select_one('.author-name')
        author = author.text.strip() if author else None

        cover = soup.select_one('.novel-cover img')
        cover_url = cover['src'] if cover else None

        description = soup.select_one('.novel-description')
        description = description.text.strip() if description else None

        genres = [g.text.strip() for g in soup.select('.genre-tag')]

        return NovelMetadata(
            title=title,
            author=author,
            cover_url=cover_url,
            description=description,
            genres=genres,
            source_url=url,
            source_language='zh',
        )

    async def get_chapter_list(self, url: str) -> List[ChapterInfo]:
        """Get chapter list from FanMTL."""
        html = await self.fetcher.fetch(url)
        soup = BeautifulSoup(html, 'lxml')

        chapters = []
        current_volume = None
        current_volume_num = 0
        chapter_num = 0

        for item in soup.select('.chapter-list-item, .volume-header'):
            if 'volume-header' in item.get('class', []):
                current_volume = item.text.strip()
                current_volume_num += 1
            else:
                chapter_num += 1
                link = item.select_one('a')
                title = link.text.strip()
                href = link['href']

                chapters.append(ChapterInfo(
                    title=title,
                    url=href if href.startswith('http') else f"{self.base_url}{href}",
                    chapter_number=chapter_num,
                    volume_number=current_volume_num if current_volume else None,
                    volume_title=current_volume,
                ))

        return chapters

    async def get_chapter_content(self, chapter: ChapterInfo) -> ChapterContent:
        """Fetch chapter content from FanMTL."""
        html = await self.fetcher.fetch(chapter.url)
        soup = BeautifulSoup(html, 'lxml')

        # Remove unwanted elements
        for element in soup.select('script, style, .ads, .comments, nav, footer'):
            element.decompose()

        content_div = soup.select_one('.chapter-content')
        if not content_div:
            content_div = soup.select_one('article')

        content = str(content_div) if content_div else ""

        # Extract images if any
        images = [img['src'] for img in soup.select('.chapter-content img')]

        return ChapterContent(
            info=chapter,
            content=content,
            images=images,
        )
```

### Adapter Template

```python
# Location: sagemtl_crawler/sites/_template.py
# Copy this template to create new site adapters

"""
Template for creating new site adapters.

To create a new adapter:
1. Copy this file to sagemtl_crawler/sites/{site_name}.py
2. Rename the class to {SiteName}Adapter
3. Fill in the site-specific details
4. Implement all required methods
5. Test with the integration test suite
"""

from bs4 import BeautifulSoup
from typing import List, Optional

class TemplateAdapter:
    """Adapter for [site name]"""

    # Required class attributes
    site_name = "Site Name"                    # Human-readable name
    base_url = "https://example.com"           # Main URL
    supported_domains = ["example.com"]         # All valid domains
    capabilities = [SiteCapability.DIRECT_URL]  # What this adapter can do

    def __init__(self):
        self.fetcher: Optional[PoliteFetcher] = None

    def can_handle(self, url: str) -> bool:
        """Check if this adapter can handle the URL."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        return any(d in domain for d in self.supported_domains)

    async def search(self, query: str, limit: int = 20) -> List[NovelMetadata]:
        """
        Search for novels. Optional - only implement if site supports search.

        Args:
            query: Search keywords
            limit: Max results to return

        Returns:
            List of NovelMetadata for matching novels
        """
        raise NotImplementedError("Search not supported for this site")

    async def get_novel_metadata(self, url: str) -> NovelMetadata:
        """
        Fetch novel metadata from novel page.

        Args:
            url: URL of novel's main page

        Returns:
            NovelMetadata with title, author, cover, etc.
        """
        html = await self.fetcher.fetch(url)
        soup = BeautifulSoup(html, 'lxml')

        # TODO: Implement site-specific parsing
        # Example:
        # title = soup.select_one('h1').text.strip()
        # author = soup.select_one('.author').text.strip()

        raise NotImplementedError("Implement get_novel_metadata")

    async def get_chapter_list(self, url: str) -> List[ChapterInfo]:
        """
        Get list of all chapters.

        Args:
            url: URL of novel's main page or TOC page

        Returns:
            List of ChapterInfo in reading order
        """
        html = await self.fetcher.fetch(url)
        soup = BeautifulSoup(html, 'lxml')

        # TODO: Implement site-specific TOC parsing
        # Handle pagination if TOC spans multiple pages
        # Detect and preserve volume structure

        raise NotImplementedError("Implement get_chapter_list")

    async def get_chapter_content(self, chapter: ChapterInfo) -> ChapterContent:
        """
        Fetch content of a single chapter.

        Args:
            chapter: ChapterInfo from get_chapter_list

        Returns:
            ChapterContent with parsed HTML content
        """
        html = await self.fetcher.fetch(chapter.url)
        soup = BeautifulSoup(html, 'lxml')

        # Remove unwanted elements
        for element in soup.select('script, style, .ads, nav, footer'):
            element.decompose()

        # TODO: Find the content container
        # content_div = soup.select_one('.chapter-content')

        raise NotImplementedError("Implement get_chapter_content")
```

---

## Priority Sites to Implement

| Site | Domain | Capability | Notes |
|------|--------|------------|-------|
| FanMTL | fanmtl.com | Search, Volumes | MTL aggregator |
| Wuxiaworld | wuxiaworld.com | Direct URL | Official translations |
| Webnovel | webnovel.com | Search | QiDian English |
| NovelUpdates | novelupdates.com | Search | Aggregator (links only) |
| RoyalRoad | royalroad.com | Search | Original English |
| Scribble Hub | scribblehub.com | Search | Fan fiction |
| LNMTL | lnmtl.com | Direct URL | Raw MTL |

---

## Testing

### Integration Tests

```python
# Location: tests/test_crawl_integration.py

import pytest
import asyncio
from sagemtl_crawler.core import AdapterRegistry, CrawlerEngine

@pytest.fixture
def engine(tmp_path):
    return CrawlerEngine(output_dir=tmp_path)

@pytest.mark.asyncio
async def test_fanmtl_search():
    """Test FanMTL search functionality."""
    AdapterRegistry.discover_adapters()
    adapter = AdapterRegistry.get_adapter("https://fanmtl.com/novel/test")

    results = await adapter.search("martial god")
    assert len(results) > 0
    assert all(r.title for r in results)

@pytest.mark.asyncio
async def test_fanmtl_metadata():
    """Test FanMTL metadata fetching."""
    AdapterRegistry.discover_adapters()
    adapter = AdapterRegistry.get_adapter("https://fanmtl.com/novel/test")

    metadata = await adapter.get_novel_metadata(
        "https://fanmtl.com/novel/martial-god-asura"
    )

    assert metadata.title
    assert metadata.source_url

@pytest.mark.asyncio
async def test_crawl_resume(engine, tmp_path):
    """Test job resumption after interruption."""
    # Start a crawl
    job = await engine.crawl_novel(
        "https://fanmtl.com/novel/test",
        job_id="test-resume"
    )

    # Simulate interruption
    job.status = "paused"
    engine._save_job_state(job)

    # Resume
    resumed_job = await engine.crawl_novel(
        "https://fanmtl.com/novel/test",
        job_id="test-resume",
        resume=True
    )

    assert resumed_job.completed_chapters >= job.completed_chapters
```

---

## Configuration

```toml
# config.toml - Crawler section

[crawler]
# Default engine to use
default_engine = "sage"

# HTTP settings
request_timeout = 30
max_retries = 3
retry_delay = 1.0
request_delay = 0.5
max_concurrent_requests = 5

# User agent rotation
rotate_user_agents = true

# Politeness
respect_robots_txt = true
obey_rate_limits = true

# Output
chapters_per_file = 1  # For interim storage
preserve_images = false
```

---

## Error Handling

```python
class CrawlerError(Exception):
    """Base exception for crawler errors."""
    pass

class AdapterNotFoundError(CrawlerError):
    """No adapter available for the URL."""
    pass

class FetchError(CrawlerError):
    """HTTP request failed."""
    pass

class ParseError(CrawlerError):
    """Failed to parse page content."""
    pass

class RateLimitError(CrawlerError):
    """Rate limited by the server."""
    pass
```
