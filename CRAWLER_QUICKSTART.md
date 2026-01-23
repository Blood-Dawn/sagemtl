# Quick Start: Using the New Crawler

## What Changed?

Your SageMTL app now uses **lightnovel-crawler** as its primary crawler, giving you access to **460+ novel websites** automatically!

## Installation

Everything you need is already in `requirements-desktop.txt`. Just run:

```bash
pip install -r requirements-desktop.txt
```

This installs:
- lightnovel-crawler (460+ sites)
- All dependencies
- Your app is ready to go!

## Usage

### Method 1: Desktop App (Easiest)

1. **Launch the app**:
   ```bash
   python -m sagemtl_desktop.main
   ```

2. **Fetch from any supported URL**:
   - Click "Fetch from URL"
   - Paste any novel URL from supported sites
   - The app automatically picks the best crawler
   - Wait for chapters to download
   - Done!

### Method 2: Programmatic (For Developers)

```python
import asyncio
from sagemtl_desktop.core.lightnovel_crawler_wrapper import (
    LightNovelCrawlerWrapper,
    LIGHTNOVEL_CRAWLER_AVAILABLE
)

async def crawl_novel():
    if LIGHTNOVEL_CRAWLER_AVAILABLE:
        crawler = LightNovelCrawlerWrapper()
        
        # Crawl a novel
        novel = await crawler.fetch_novel(
            url="https://www.royalroad.com/fiction/21220/mother-of-learning",
            progress_callback=lambda curr, total, msg: print(f"{curr}/{total}: {msg}")
        )
        
        # Use the data
        print(f"Title: {novel.title}")
        print(f"Author: {novel.author}")
        print(f"Chapters: {len(novel.chapters)}")
        
        # Access chapters
        for chapter in novel.chapters[:3]:
            print(f"\n{chapter.title}")
            print(chapter.content[:200] + "...")

# Run it
asyncio.run(crawl_novel())
```

## Supported Sites

### Top Sites
- **Royal Road** - https://www.royalroad.com
- **Scribble Hub** - https://www.scribblehub.com
- **WebNovel** - https://www.webnovel.com
- **WuxiaWorld** - https://www.wuxiaworld.com
- **NovelFull** - https://www.novelfull.com
- **And 450+ more!**

### Languages
- English
- Chinese (Simplified & Traditional)
- Japanese
- Korean
- Spanish
- French
- Indonesian
- And more!

### Get Full List

See the [lightnovel-crawler README](https://github.com/lncrawl/lightnovel-crawler#supported-sources) for the complete list of 460+ supported sites.

## How It Works

```
You paste a URL
    ↓
App detects the site
    ↓
Uses lightnovel-crawler (460+ sites)
    ↓
Downloads chapters
    ↓
Ready for translation!
```

## Examples

### Example 1: Royal Road

```python
url = "https://www.royalroad.com/fiction/21220/mother-of-learning"
novel = await crawler.fetch_novel(url)
# Got 99 chapters from Royal Road!
```

### Example 2: Scribble Hub

```python
url = "https://www.scribblehub.com/series/12345/your-novel/"
novel = await crawler.fetch_novel(url)
# Got chapters from Scribble Hub!
```

### Example 3: Chinese Site

```python
url = "https://www.69shu.com/txt/12345.htm"
novel = await crawler.fetch_novel(url)
# Got Chinese novel chapters ready for translation!
```

## Settings

### Change Crawler Preference

By default, the app prefers lightnovel-crawler. To change:

**In the UI**: Settings → Preferred Crawler → Choose

**Programmatically**:
```python
from PySide6.QtCore import QSettings

settings = QSettings("SageMTL", "SageMTL")

# Use lightnovel-crawler (default)
settings.setValue("preferred_crawler", "lightnovel")

# Lightnovel-crawler is the only crawler; no alternative needed
```

## Testing

### Quick Test

Run the included test script:
```bash
python test_lncrawl_integration.py
```

Expected output:
```
============================================================
Testing lightnovel-crawler Integration
============================================================

✓ lightnovel-crawler is installed
✓ Wrapper created successfully
✓ Found N supported sites
...
✓ All tests passed!
============================================================
```

### Test with Real URL

Edit `test_lncrawl_integration.py` and uncomment the crawl test section with your favorite novel URL.

## Troubleshooting

### "lightnovel-crawler is not installed"

```bash
pip install lightnovel-crawler
```

### Pillow Import Error

```bash
pip install --force-reinstall Pillow
```

### Crawler Fails

1. **Check the URL** - Make sure it's from a supported site
2. **Try fallback** - The app will automatically try SageCrawler
3. **Check internet** - You need internet to download chapters
4. **Report issue** - If it should work but doesn't, create an issue

### Site Not Supported

Check the [supported sites list](https://github.com/lncrawl/lightnovel-crawler#supported-sources).

If your site isn't there:
- The app will automatically try SageCrawler (fallback)
- You can request support on the lncrawl repo

## Tips

### Faster Downloads

lightnovel-crawler is respectful of rate limits to avoid IP bans. Be patient!

### Glossary Integration

After crawling:
1. Load your custom glossary
2. Translate the crawled chapters
3. Get consistent terminology across all chapters

### Batch Processing

1. Crawl multiple novels
2. Import them all
3. Queue translations
4. Process overnight

### EPUB Export

After translation:
1. Select translated chapters
2. Export as EPUB
3. Read on your e-reader!

## Advanced Usage

### Custom Progress Tracking

```python
def my_progress(current, total, message):
    percentage = (current / total * 100) if total > 0 else 0
    print(f"[{percentage:5.1f}%] {message}")
    # Update your UI here

novel = await crawler.fetch_novel(url, progress_callback=my_progress)
```

### Check Site Support

```python
crawler = LightNovelCrawlerWrapper()

# Check if a URL is supported
if crawler.supports_url("https://www.royalroad.com/fiction/12345"):
    print("✓ This site is supported!")
    
# Get list of supported sites
sites = crawler.get_supported_sites()
print(f"Total sites: {len(sites)}")
```

### Error Handling

```python
try:
    novel = await crawler.fetch_novel(url)
except Exception as e:
    print(f"Failed to crawl: {e}")
    # Try fallback crawler or notify user
```

## Documentation

- **Integration Guide**: See `LNCRAWL_INTEGRATION.md`
- **Summary**: See `CRAWLER_REVAMP_SUMMARY.md`
- **lncrawl Docs**: https://github.com/lncrawl/lightnovel-crawler

## Need Help?

- **Issues**: [Create an issue](https://github.com/Blood-Dawn/sagemtl/issues)
- **Questions**: [Start a discussion](https://github.com/Blood-Dawn/sagemtl/discussions)
- **lncrawl Issues**: [lncrawl repo](https://github.com/lncrawl/lightnovel-crawler/issues)

## License

- **SageMTL**: MIT License
- **lightnovel-crawler**: GPL v3 License (separate component)

The integration is compliant - lncrawl is used as a library dependency, not incorporated code.

---

**Ready to crawl 460+ sites? Fire up the app and start downloading novels!** 🚀
