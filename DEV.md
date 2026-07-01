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
# Novel-focused build (small; manga ML installs on demand from source):
python scripts/build_desktop.py
# Full manga-enabled build (large; bundles torch/paddle/transformers/onnx/opencv/
# manga-ocr + crawler + fonts so the whole app works frozen; model weights still
# download on first use). Add --zip to package dist/SageMTL:
python scripts/build_desktop.py --manga --zip
```

Specs: `pyinstaller-desktop.spec` (novel-focused, excludes numpy/PIL) and
`pyinstaller-manga.spec` (full manga build via PyInstaller `collect_all`). The
manga build is several GB and typically exceeds a GitHub release asset (2 GB per
file), so host it off GitHub. A frozen build cannot `pip install` more into itself,
so anything not bundled by the chosen spec is unavailable in that build.

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
- `sagemtl_desktop/core/translator.py` provides chunked translation with backend selection (`argos`, optional `googletrans`, `echo`) and translation-memory caching.
- `sagemtl_desktop/core/glossary_manager.py` is the primary glossary path for global + per-novel term enforcement; `glossary.py` remains as legacy CSV compatibility.
- `sagemtl_desktop/core/novel_library.py` persists crawled content.
- `sagemtl_desktop/core/crawl_service.py` now owns crawl strategy decisions used by the UI.
- `sagemtl_desktop/core/crawl_settings.py` defines per-site crawl runtime settings.
- `sagemtl_desktop/core/search_service.py` handles crawler search execution, grouped-result shaping, and chapter-prefetch row selection for UI jobs.
- `sagemtl_desktop/core/app_settings.py` bridges desktop preferences to shared `sagemtl.config.Settings`.
- `sagemtl_desktop/ui/i18n.py` and `sagemtl_desktop/ui/error_hints.py` handle UI localization and actionable recovery hints.
- `sagemtl_desktop/ui/dialogs.py` now includes a detailed workflow/options help guide and search-result chapter-count preview UX.

Crawler flow today:

- Search and URL classification use `LightNovelCrawlerWrapper`.
- `LightNovelCrawlerWrapper` normalizes lncrawl search result schemas (`CombinedSearchResult` and legacy result objects) into stable UI rows (`title`, `url`, `site`).
- Search now emits live in-flight progress during lncrawl source scans by polling `app.search_progress`, and the search dialog progress bar subscribes to job progress updates.
- Search progress dialogs are reopenable while jobs remain active (`View -> Show Active Search Progress`).
- Search results are now two-step (grouped novels -> source sites), and source lists can auto-prefetch chapter counts for top rows before crawl selection.
- Interactive and batch URL crawls call `CrawlService` with per-site profiles and staged progress reporting.
- Chapter downloads execute wrapper-backed selected-chapter flow with `GenericNovelCrawler` underneath, enabling retry/delay/robots policies and resume behavior.
- `LightNovelCrawlerWrapper.fetch_novel()` remains available and is still covered by integration tests.
- Translation job processing now applies glossary-manager terms before and after translation, with optional legacy CSV glossary layering.
- Glossary replacement uses CJK-safe boundary behavior (no forced `\b` for CJK sources).
- Manual novel renames set a persistent title lock so resume crawls do not overwrite user-defined titles.

Shared packages:

- `sagemtl/` contains CLI, clean/crawl helpers, job store, shared config, and release-check automation.
- `sagemtl_crawler/` contains an adapter-based crawler engine not fully wired into current desktop flow.

Manga module:

- `sagemtl_desktop/core/manga/` holds the image pipeline: `pipeline.MangaPipeline` chains detect -> reading_order -> ocr -> translate -> inpaint -> typeset (with `webtoon` strip tiling), plus `model_registry` (lazy download/cache + non-commercial guard), `library.MangaLibrary`, `jobs` (Qt-free crawl/translate/export/re-render), and `exporter` (CBZ/PDF/folder).
- `sagemtl_desktop/ui/manga/` holds the thin widgets (`manga_view`, `reader_widget`, `typeset_editor`); `MainWindow` adds a Novels/Manga `QStackedWidget` mode switch and a Manga menu (the manga view is created lazily so startup stays light).
- `sagemtl_manga_crawler/` mirrors the novel crawler for page-image sources (MangaDex official API).
- ALL heavy ML imports (torch, onnxruntime, paddle, transformers, opencv, manga-ocr) are lazy inside `core/manga/*`; the novel path gains no heavy import (enforced by `tests/test_manga_skeleton.py` and the `manga_lazy_imports` release check). Manga deps live in `requirements-manga.txt` (installed on demand via `scripts/setup_manga.py`); models download to `~/.sagemtl/models/` at first use.
- Tests: per-stage unit tests are non-integration (run by default); real-model/network checks are `integration`-marked (detector/OCR/translate/inpaint/pipeline on Tier A images, and a live MangaDex search/download). Run them explicitly with `-m integration`.

## 5. Verified baseline (2026-02-09)

- Non-integration tests: `65 passed, 8 deselected`.
- Ruff findings: `0` (`python -m ruff check sagemtl sagemtl_desktop sagemtl_crawler tests`).
- Python files: 101 total.
- Largest files by line count:
  - `sagemtl_desktop/ui/main_window.py` (2077)
  - `sagemtl_desktop/core/generic_crawler.py` (887)
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
- Added site-specific crawl settings, resume-aware chapter upsert, and batch URL crawl queue support.
- Added direct EPUB export from crawler output path during crawl.
- Added translation memory/cache for repeated chunk reuse.
- Added optional translation backends and adaptive multilingual chunking controls.
- Added glossary regex pattern caching for large dictionary performance.
- Added UI localization (English/Spanish) and actionable recovery hints in core failure paths.
- Unified desktop and CLI settings through shared config fields and desktop settings bridge.
- Added `python -m sagemtl release-check` automation for docs/lint/tests/import smoke checks.
- Added regression coverage for lncrawl search schema compatibility so name-based search does not drop valid raw hits.
- Added CJK-safe glossary matching and regression coverage for contiguous-text term replacement.
- Added title-lock persistence for user-renamed novels with resume-crawl regression coverage.
- Added search-result chapter-count discovery helper coverage (`CrawlService.discover_chapter_count`) and grouped-search shaping coverage in `SearchService`.

### Remaining priorities

- Continue decomposing `MainWindow` into smaller controllers/services beyond current crawl/search extractions.
- Reduce full-file rewrites for high-frequency state updates in job/library storage.
- Eliminate duplicate glossary systems or define strict ownership boundaries.
- Resolve CLI command surface mismatch where `serve` is exposed but module availability is inconsistent.

## 7. Development standards

- Prefer small, testable modules over large UI methods.
- Any crawler behavior change must update both tests and roadmap status.
- Keep docs synchronized with actual runtime behavior in the same PR.
- No new feature is complete without at least one automated test and roadmap status update.
