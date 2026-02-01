# Crawler Setup Guide

SageMTL now uses lightnovel-crawler (lncrawl) as the sole crawler. This guide explains how to set it up and use it.

## Installation

Install desktop dependencies (includes lncrawl):

```bash
pip install -r requirements-desktop.txt
```

Or install lncrawl manually:

```bash
pip install lightnovel-crawler
```

## First Use

1. Launch SageMTL
2. Enter your novel URL and click "Fetch from URL"
3. The app uses lightnovel-crawler exclusively for crawling

## Supported Sites

Lightnovel-crawler supports 460+ web novel sites across multiple languages. See the full list:

[Supported sources (lncrawl GitHub)](https://github.com/lncrawl/lightnovel-crawler#supported-sources)

## Troubleshooting

### lightnovel-crawler not found

If you've installed lightnovel-crawler but SageMTL doesn't detect it:

1. Verify installation: `pip show lightnovel-crawler`
2. Reinstall: `pip install --upgrade --force-reinstall lightnovel-crawler`
3. Ensure your Python environment matches the one running SageMTL

### Crawl fails for a specific site

1. Confirm the site is supported by lncrawl
2. Update lncrawl: `pip install -U lightnovel-crawler`
3. Report issues at lncrawl repo

## Python API (Programmatic)

```python
import asyncio
from sagemtl_desktop.core.lightnovel_crawler_wrapper import LightNovelCrawlerWrapper, LIGHTNOVEL_CRAWLER_AVAILABLE

async def crawl():
    if LIGHTNOVEL_CRAWLER_AVAILABLE:
        novel = await LightNovelCrawlerWrapper().fetch_novel("https://www.royalroad.com/fiction/21220/mother-of-learning")
        print(novel.title, len(novel.chapters))

asyncio.run(crawl())
```

## Credits

- **LightNovel-Crawler**: Developed by dipu-bd and contributors (GPL v3)
