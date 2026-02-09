# Development Guide

This document is the single technical reference for active development.

## 1. Environment setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-desktop.txt
```

Optional dev tooling:

```powershell
pip install black ruff pytest pytest-asyncio pytest-cov
```

## 2. Run commands

Desktop app:

```powershell
python -m sagemtl_desktop.main
```

CLI:

```powershell
python -m sagemtl --help
```

Build desktop executable:

```powershell
pyinstaller pyinstaller-desktop.spec
```

## 3. Test and lint commands

Default non-integration test run:

```powershell
python -m pytest -m "not integration"
```

Integration tests only:

```powershell
python -m pytest tests/desktop/test_lncrawl_integration.py -m integration -v
```

Lint:

```powershell
python -m ruff check sagemtl sagemtl_desktop sagemtl_crawler tests
```

## 4. Architecture snapshot

Desktop runtime path:

- `sagemtl_desktop/ui/main_window.py` orchestrates UI, import, crawl, translate, and export.
- `sagemtl_desktop/core/job_manager.py` handles threaded jobs and progress/log signals.
- `sagemtl_desktop/core/translator.py` wraps Argos Translate for offline translation.
- `sagemtl_desktop/core/glossary.py` and `sagemtl_desktop/core/glossary_manager.py` both exist; the app currently uses both flows.
- `sagemtl_desktop/core/novel_library.py` persists crawled content.
- `sagemtl_desktop/core/crawl_service.py` now owns crawl strategy decisions used by the UI.

Crawler flow today:

- Search and URL classification use `LightNovelCrawlerWrapper`.
- UI chapter discovery/download now calls `CrawlService`, which routes to wrapper methods.
- Full and first-N selections use `LightNovelCrawlerWrapper.fetch_novel()` (the tested wrapper path).
- Custom-range selections use wrapper-backed `fetch_selected_chapters()` with `GenericNovelCrawler` fallback.

Shared packages:

- `sagemtl/` contains CLI, clean/crawl helpers, job store, and queue stubs.
- `sagemtl_crawler/` contains an adapter-based crawler engine not fully wired into current desktop flow.

## 5. Verified baseline (2026-02-09)

- Non-integration tests: `27 passed, 8 deselected`.
- Ruff findings: `0` (`python -m ruff check sagemtl sagemtl_desktop sagemtl_crawler tests`).
- Python files: 87 total.
- Largest files by line count:
  - `sagemtl_desktop/ui/main_window.py` (1619)
  - `sagemtl_desktop/core/generic_crawler.py` (809)
  - `sagemtl_desktop/ui/glossary_editor.py` (606)

## 6. Optimization audit

### Completed in latest pass

- Unified production crawl execution around wrapper-backed service flow.
- Replaced deprecated skipped SageCrawler tests with active regression tests.
- Added bounded concurrency for chapter downloads in `GenericNovelCrawler.fetch_chapters()`.
- Added regression coverage for crawl strategy and wrapper delegation paths.
- Fixed deterministic icon resolution in `pyinstaller-desktop.spec`.
- Removed stale SageCrawler UI/help references.
- Cleared low-risk lint debt to a zero-issue baseline.

### Remaining priorities

- Continue decomposing `MainWindow` into smaller controllers/services beyond crawl orchestration.
- Precompile glossary regex patterns for large glossaries.
- Reduce full-file rewrites for high-frequency state updates in job/library storage.
- Eliminate duplicate glossary systems or define strict ownership boundaries.
- Resolve CLI command surface mismatch where `serve` is exposed but module availability is inconsistent.

## 7. Development standards

- Prefer small, testable modules over large UI methods.
- Any crawler behavior change must update both tests and roadmap status.
- Keep docs synchronized with actual runtime behavior in the same PR.
- No new feature is complete without at least one automated test and roadmap status update.
