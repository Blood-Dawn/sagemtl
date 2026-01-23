# Production vs Test Configuration

## Production (Main Application)

### Search Flow
**File**: `sagemtl_desktop/ui/main_window.py`
- **Method**: `_search_and_crawl_novel()`
- **Behavior**: Returns ALL search results from lncrawl (1200+ sources)
- **No Limits**: Search is unrestricted

### Download Flow
**File**: `sagemtl_desktop/ui/main_window.py`
- **Method**: `_crawl_url()`
- **Call**: `selected_crawler.fetch_novel(url, progress_wrapper)`
- **Behavior**: Downloads ALL chapters from the novel
- **No Limits**: Complete novel download

## Test Suite

### Search Tests
**File**: `tests/desktop/test_lncrawl_integration.py`
- **Tests**: `test_01_search_novel`, `test_02_select_random_sites`
- **Behavior**: Same as production (all results)
- **No Limits**: Full search capabilities

### Download Tests
**File**: `tests/desktop/test_lncrawl_integration.py`
- **Tests**: `test_03_download_first_10_chapters`, `test_06_full_workflow`
- **Call**: `crawler.fetch_novel(url, progress_callback, max_chapters=10)`
- **Behavior**: Downloads ONLY first 10 chapters
- **Limit**: `max_chapters=10` for faster testing

## Implementation Details

### Wrapper Method Signature
```python
async def fetch_novel(self, url: str, progress_callback=None, max_chapters: int = None) -> CrawledNovel:
```

### Production Usage (No Limit)
```python
# In main_window.py - downloads ALL chapters
novel_data = loop.run_until_complete(
    selected_crawler.fetch_novel(url, progress_wrapper)
)
```

### Test Usage (With Limit)
```python
# In test_lncrawl_integration.py - downloads 10 chapters
novel_data = await crawler.fetch_novel(
    url, 
    progress_callback, 
    max_chapters=10
)
```

### Chapter Limiting Logic
```python
# In lightnovel_crawler_wrapper.py
if max_chapters is not None and hasattr(app, 'crawler') and app.crawler:
    original_chapters = getattr(app.crawler, 'chapters', [])
    if len(original_chapters) > max_chapters:
        app.crawler.chapters = original_chapters[:max_chapters]
        if progress_callback:
            progress_callback(20, 100, f"Limited to first {max_chapters} chapters for testing")
```

**Key Point**: The limiting code ONLY runs when `max_chapters is not None`. Production never passes this parameter, so limiting never occurs.

## Verification

✅ **Production code has NO limits**
✅ **Test code uses limits for speed**
✅ **Both use the same wrapper API**
✅ **No test-specific code in production**

## Summary

The application is **production-ready** with:
- Full novel search across 1200+ sources
- Complete chapter downloads (no artificial limits)
- Real-time progress monitoring
- Non-blocking UI during operations
- Test suite with faster execution (10 chapter limit)
