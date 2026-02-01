# LNCrawl Integration Test Suite

## Overview

Comprehensive test suite for the lightnovel-crawler integration. Tests the complete workflow from search to download to extraction.

## Test Configuration

### Pytest Settings (pyproject.toml)

```toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests requiring network access",
]
addopts = "-v --tb=short -m 'not integration'"
asyncio_default_fixture_loop_scope = "function"
filterwarnings = [
    "ignore::DeprecationWarning:pythonjsonlogger.*",
    "ignore:builtin type.*has no __module__ attribute:DeprecationWarning",
]
```

### Default Behavior
- **Skips integration tests** by default (requires `-m integration` to run)
- **Suppresses known warnings** from external libraries
- **Fast execution** for CI/CD pipelines

## Running Tests

### Run All Tests (Except Integration)
```bash
pytest tests/desktop/ -v
```

### Run Integration Tests Only
```bash
pytest tests/desktop/ -v -m integration
```

### Run Specific Test
```bash
pytest tests/desktop/test_lncrawl_integration.py::TestLightNovelCrawlerIntegration::test_07_url_detection -v
```

### Run All Tests Including Integration
```bash
pytest tests/desktop/ -v -m ""
```

## Test File

Location: `tests/desktop/test_lncrawl_integration.py`

## Test Cases

### Unit Tests (Fast - No Network)

#### 7. `test_07_url_detection` ✅
Tests URL vs name detection logic.
- **No Network Required**
- **Fast Execution**
- **Validates**: URLs correctly identified
- **Validates**: Names correctly identified as non-URLs

### Integration Tests (Slow - Requires Network) 🌐

**Marked with**: `@pytest.mark.integration` and `@pytest.mark.slow`

#### 1. `test_01_search_novel`
Tests searching for a novel by name.
- **Requires**: Active internet, working novel sites
- **Validates**: Search returns results
- **Validates**: Progress callbacks are triggered
- **Validates**: Result structure (title, url, info fields)
- **Novel**: "Marvel: I am the leader of the mutant race"

#### 2. `test_02_select_random_sites`
Tests selecting random sites from search results.
- **Requires**: Successful search results
- **Validates**: Can select 3 random results
- **Validates**: Each result has valid URL
- **Validates**: Titles are not empty

#### 3. `test_03_download_first_10_chapters`
Tests downloading limited chapters from a novel.
- **Requires**: Active internet, working novel sites
- **Validates**: Novel data structure (title, author, chapters)
- **Validates**: Chapter count is ≤ 10
- **Validates**: Progress callbacks during download
- **Limit**: First 10 chapters only (for testing speed)

#### 4. `test_04_extract_first_chapter`
Tests extracting and verifying first chapter content.
- **Requires**: Successful download
- **Validates**: Chapter has title and content
- **Validates**: Content is substantial (>100 chars)
- **Displays**: First 500 chars as preview

#### 5. `test_05_verify_all_chapters`
Tests that all downloaded chapters have valid content.
- **Requires**: Successful download
- **Validates**: Every chapter has non-empty title
- **Validates**: Every chapter has non-empty content
- **Reports**: Character count for each chapter

#### 6. `test_06_full_workflow` ⭐
**Main integration test** - runs complete workflow.

**Steps**:
1. Search for novel by name
2. Select 3 random sites from results
3. Download from first selected site (first 10 chapters)
4. Extract first chapter
5. Verify all chapters

**Returns**: Summary dict with:
- `search_results_count`: Total results found
- `selected_sites`: Number of sites selected
- `chapters_downloaded`: Chapters actually downloaded
- `novel_title`: Title of novel
- `novel_author`: Author name
- `first_chapter_title`: First chapter title
- `first_chapter_length`: Character count

#### 8. `test_08_progress_callbacks`
Tests that progress callbacks are invoked.
- **Requires**: Active internet
- **Validates**: Search callbacks are called
- **Validates**: Download callbacks are called
- **Counts**: Total callback invocations

## Test Requirements

### Integration Tests Need:
- ✅ `lncrawl` (lightnovel-crawler) installed
- ✅ Network connection (tests download from real sites)
- ✅ Specific test novel available on at least one site
- ⏱️ May take several minutes to complete

### Why Integration Tests Are Skipped by Default:
1. **Network Dependency**: Rely on external novel websites
2. **Slow Execution**: Can take 5-15 minutes
3. **Flaky**: Sites may be down or blocking requests
4. **Rate Limiting**: Too frequent runs may trigger blocks

## Implementation Details

### sys.argv Override
The wrapper now temporarily overrides `sys.argv` before calling `load_sources()` to prevent argparse conflicts with pytest flags:

```python
original_argv = sys.argv
sys.argv = ['lncrawl']
load_sources()
sys.argv = original_argv
```

This prevents pytest's `-v` flag from being interpreted as lncrawl's `--version`.

### max_chapters Parameter
The wrapper's `fetch_novel()` method now accepts optional `max_chapters` parameter:

```python
novel_data = await crawler.fetch_novel(url, progress_callback, max_chapters=10)
```

This limits chapter download for faster testing.

## Expected Test Results

### Standard Run (No Integration)
```
========== test session starts ==========
collected 21 items / 8 deselected / 13 selected

tests/desktop/test_epub_writer.py ✓✓✓✓✓
tests/desktop/test_translator.py ✓✓✓✓✓✓✓✓

========== 13 passed, 8 deselected in 14.25s ==========
```

### Integration Run
```
========== test session starts ==========
collected 21 items / 13 deselected / 8 selected

tests/desktop/test_lncrawl_integration.py ✓✓✓✓✓✓✓✓

========== 8 passed, 13 deselected in 300.45s ==========
```

## Warnings

All deprecation warnings are filtered:
- ✅ `pythonjsonlogger` module moved warning
- ✅ `SwigPy` warnings from Argos translation models
- ✅ `asyncio_default_fixture_loop_scope` warning

## Notes

- Integration tests use real network connections to novel sites
- Download times vary based on site response
- Chapter limits prevent excessive download during testing
- All tests use "Marvel: I am the leader of the mutant race" as test novel
- Progress callbacks provide real-time feedback during operations
- Tests are marked appropriately for CI/CD pipeline optimization
