# Lightnovel-Crawler Integration Guide

## Overview

SageMTL now uses [lightnovel-crawler](https://github.com/lncrawl/lightnovel-crawler) as its primary crawler engine, providing support for **460+ novel websites** across multiple languages.

## What is lightnovel-crawler?

Lightnovel-crawler (lncrawl) is a comprehensive web novel crawler that supports:
- 460+ websites (English, Chinese, Korean, Japanese, Spanish, French, Indonesian, and more)
- Multiple output formats (EPUB, PDF, MOBI, DOCX, TXT, JSON, etc.)
- Automatic site adapter selection
- Robust chapter extraction and formatting
- Active development and community support

## Architecture

SageMTL integrates lncrawl through a wrapper layer:

```
User Interface (PySide6)
        ↓
CrawlerInterface (ABC)
        ↓
LightNovelCrawlerWrapper
    ↓
lightnovel-crawler library
```

### Key Components

1. **CrawlerInterface** (`sagemtl_desktop/core/crawler_interface.py`)
   - Abstract base class defining the crawler API
   - Ensures both crawlers work interchangeably
   - Provides standardized data structures (`CrawledNovel`, `CrawledChapter`)

2. **LightNovelCrawlerWrapper** (`sagemtl_desktop/core/lightnovel_crawler_wrapper.py`)
   - Integrates lncrawl into SageMTL
   - Handles async/sync conversion
   - Manages temporary files and output parsing
   - Provides progress callbacks to the UI

3. (Removed) SageCrawlerWrapper
    - SageCrawler has been removed; lncrawl is the sole crawler engine

## Usage

### In the Desktop App

The desktop app uses lncrawl exclusively:

1. **Fetch from URL**: Enter any supported novel URL
2. lncrawl handles crawling and chapter extraction

### Crawler Selection

No selection needed; lncrawl is the default and only crawler.

### Programmatic Usage

```python
from sagemtl_desktop.core.lightnovel_crawler_wrapper import (
    LightNovelCrawlerWrapper,
    LIGHTNOVEL_CRAWLER_AVAILABLE
)

if LIGHTNOVEL_CRAWLER_AVAILABLE:
    crawler = LightNovelCrawlerWrapper()
    
    # Check if URL is supported
    if crawler.supports_url("https://www.royalroad.com/fiction/12345"):
        # Fetch novel
        novel = await crawler.fetch_novel(
            url="https://www.royalroad.com/fiction/12345",
            progress_callback=lambda curr, total, msg: print(f"{curr}/{total}: {msg}")
        )
        
        print(f"Title: {novel.title}")
        print(f"Author: {novel.author}")
        print(f"Chapters: {len(novel.chapters)}")
```

## Supported Sites

### Most Popular
- Royal Road
- Scribble Hub
- WebNovel
- WuxiaWorld
- NovelFull
- LightNovelPub
- And 450+ more...

### Get Full List

```python
crawler = LightNovelCrawlerWrapper()
sites = crawler.get_supported_sites()
print(f"Supported sites: {len(sites)}")
```

## Output Formats

LNCrawl can export to multiple formats:
- **JSON** - Structured data (default in wrapper for easy parsing)
- **EPUB** - E-book format
- **TXT** - Plain text
- **PDF** - Requires Calibre
- **MOBI** - Kindle format (requires Calibre)
- **DOCX** - Word document (requires Calibre)
- And more...

## Installation

### Desktop App

lightnovel-crawler is included in `requirements-desktop.txt`:

```bash
pip install -r requirements-desktop.txt
```

### Manual Installation

```bash
pip install lightnovel-crawler
```

### With Calibre (Optional)

For advanced formats (PDF, MOBI, etc.):
1. Install Calibre: https://calibre-ebook.com/download
2. On macOS, add to PATH:
   ```bash
   export PATH="$PATH:/Applications/calibre.app/Contents/MacOS"
   ```

## How It Works

### 1. URL Detection
When you provide a URL, lncrawl:
1. Checks its registry of 460+ crawlers
2. Finds the appropriate site adapter
3. Uses site-specific extraction logic

### 2. Novel Fetching
The wrapper:
1. Creates a temporary directory
2. Configures lncrawl to output JSON
3. Runs the crawler
4. Parses JSON into standardized format
5. Cleans up temporary files

### 3. Data Standardization
All data is converted to SageMTL's standard format:

```python
@dataclass
class CrawledChapter:
    title: str
    content: str
    chapter_number: Optional[int]
    url: Optional[str]

@dataclass
class CrawledNovel:
    title: str
    author: Optional[str]
    chapters: List[CrawledChapter]
```

## Troubleshooting

### "lightnovel-crawler is not installed"
```bash
pip install lightnovel-crawler
```

### Crawler fails for a specific site
1. Check if site is supported: `crawler.supports_url(url)`
2. Try fallback SageCrawler
3. Report issue to lncrawl: https://github.com/lncrawl/lightnovel-crawler/issues

### Slow downloads
- lncrawl respects rate limits to avoid IP bans
- Be patient with large novels
- Check your internet connection

### JSON parsing errors
- Usually means lncrawl output format changed
- Update lightnovel-crawler: `pip install -U lightnovel-crawler`
- Report to SageMTL developers

## Advantages Over Custom Crawlers

1. **Massive Site Support**: 460+ sites vs. handful in custom crawler
2. **Active Maintenance**: Community-maintained with frequent updates
3. **Robust Extraction**: Years of refinement for each site
4. **Anti-Ban Features**: Built-in rate limiting and user-agent rotation
5. **Format Flexibility**: Multiple output formats

## License Compliance

lightnovel-crawler is licensed under GPL v3. SageMTL:
- Uses it as a separate dependency (not incorporated code)
- Maintains its own MIT license for non-GPL components
- Wrapper code is clearly separated
- Users install lncrawl separately

## Future Enhancements

- [ ] UI for selecting crawler (lncrawl vs. SageCrawler)
- [ ] Site-specific settings (delay, user-agent, etc.)
- [ ] Direct EPUB export from lncrawl
- [ ] Batch URL crawling
- [ ] Resume interrupted downloads
- [ ] Chapter range selection UI

## Resources

- **lncrawl GitHub**: https://github.com/lncrawl/lightnovel-crawler
- **lncrawl Documentation**: See README in repo
- **Supported Sites**: https://github.com/lncrawl/lightnovel-crawler#supported-sources
- **SageMTL Issues**: Report integration issues to SageMTL repo

## Contributing

To improve lncrawl integration:

1. Test with various sites
2. Report bugs with:
   - URL attempted
   - Error message
   - Expected vs. actual behavior
3. Submit pull requests with:
   - Clear description
   - Test cases
   - Updated documentation

---

**Note**: This integration prioritizes lncrawl for maximum site compatibility. The original SageCrawler remains as a fallback for edge cases.
