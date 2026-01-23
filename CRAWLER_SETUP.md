# Crawler Setup Guide

SageMTL supports two crawler backends. This guide explains how to set up and use each one.

## Quick Comparison

| Feature | LightNovel-Crawler |
|---------|-------------|-------------------|
| Installation | Included | `pip install lightnovel-crawler` |
| Site Support | Pattern-based (many sites) | 455+ specifically supported sites |
| License | MIT | GPL v3 |
| Speed | Fast | Moderate (more thorough) |
| Best For | General use | Specific sites, maximum compatibility |

## Using LightNovel-Crawler (Default)

SageMTL uses lightnovel-crawler by default. Install via:

```bash
pip install lightnovel-crawler
```

**Strengths:**
- No additional dependencies
- Fast crawling speed
- Works with many sites automatically

**Limitations:**
- May not work with sites that have unusual structures
- Less thorough metadata extraction

## Using LightNovel-Crawler (Optional)

For maximum site compatibility, you can optionally install lightnovel-crawler.

### Installation
```bash
pip install lightnovel-crawler
```

### First Use

1. Launch SageMTL
2. The app will automatically detect lightnovel-crawler if installed
3. Enter your novel URL and click "Fetch from URL"
4. The app uses lightnovel-crawler exclusively for crawling

### Supported Sites

LightNovel-Crawler supports 455+ web novel sites, including:
- WuxiaWorld
- RoyalRoad
- ScribbleHub
- NovelUpdates
- And hundreds more

## Which Should I Use?

**Start with SageCrawler** - it works well for most sites and requires no setup.

**Switch to LightNovel-Crawler if:**
- SageCrawler fails to detect chapters on a specific site
- You need guaranteed support for a specific source site
- You want more complete metadata (author info, descriptions, etc.)

You can switch between crawlers at any time, and SageMTL will remember your preference.

## License Note

LightNovel-Crawler is licensed under GPL v3. SageMTL uses it as an optional library dependency, which maintains license compatibility. If you have concerns about GPL dependencies, you can use SageMTL without installing lightnovel-crawler - SageCrawler will continue to work perfectly for most use cases.

## Configuration

The crawler preference is stored in your user settings. To manually configure it:

1. Open SageMTL settings (File → Preferences or edit `~/.sagemtl/config.toml`)
2. Set `preferred_crawler` to either `"sage"` or `"lightnovel"`

Example `config.toml`:
```toml
[crawler]
preferred_crawler = "lightnovel"  # or "sage"
```

## Troubleshooting

### LightNovel-Crawler not found

If you've installed lightnovel-crawler but SageMTL doesn't detect it:

1. Verify installation: `pip list | grep lightnovel-crawler`
2. Try reinstalling: `pip install --upgrade lightnovel-crawler`
3. Check Python environment matches SageMTL installation

### Crawl fails with "ModuleNotFoundError"

This usually means lightnovel-crawler dependencies are missing. Reinstall with:
```bash
pip install --upgrade --force-reinstall lightnovel-crawler
```

### Site not supported

If neither crawler works with your site:

1. Check if the site has an API or RSS feed
2. Try manually downloading chapters and importing as EPUB/TXT
3. Report the site at [SageMTL Issues](https://github.com/yourusername/sagemtl/issues)

## Advanced Usage

### Using SageCrawler from CLI

```bash
# Crawl using pattern detection
sagemtl crawl novel https://example.com/novel/chapter-1 --start 1 --end 50
```

### Using LightNovel-Crawler from CLI

```bash
# Install extra dependencies
pip install 'sagemtl[lncrawl]'

# Crawl (will auto-select lightnovel-crawler if available)
sagemtl crawl novel https://wuxiaworld.com/novel/some-novel --all
```

### Python API

```python
from sagemtl_desktop.core.sage_crawler_wrapper import SageCrawlerWrapper
from sagemtl_desktop.core.lightnovel_crawler_wrapper import LightNovelCrawlerWrapper
import asyncio

# Using SageCrawler
async def crawl_with_sage():
    crawler = SageCrawlerWrapper()
    novel = await crawler.fetch_novel("https://example.com/novel/chapter-1")
    print(f"Title: {novel.title}")
    print(f"Chapters: {len(novel.chapters)}")

# Using LightNovel-Crawler
async def crawl_with_lncrawl():
    crawler = LightNovelCrawlerWrapper()
    novel = await crawler.fetch_novel("https://example.com/novel")
    print(f"Title: {novel.title}")
    print(f"Author: {novel.author}")

asyncio.run(crawl_with_sage())
```

## Contributing

Found a bug or want to improve crawler support? Contributions are welcome!

- For SageCrawler improvements: Submit PR to SageMTL repository
- For LightNovel-Crawler issues: Report at [lightnovel-crawler repository](https://github.com/dipu-bd/lightnovel-crawler)

## Credits

- **SageCrawler**: Developed as part of SageMTL
- **LightNovel-Crawler**: Developed by dipu-bd and contributors (GPL v3)
