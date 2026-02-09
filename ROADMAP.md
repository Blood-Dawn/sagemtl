# Roadmap

This is the single planning document for implementation and execution.

Status key:

- `[x]` complete
- `[ ]` pending
- `(In progress)` actively being implemented
- `(Deferred)` intentionally not planned right now

## 1. Current state snapshot

- Desktop app is functional for import, crawl, translate, and export.
- Non-integration tests currently pass.
- Integration coverage exists for wrapper search/download; non-integration regression coverage now includes crawl settings/resume/batch/export plus translation backend/chunking/settings/release-check flows.
- Documentation and implementation were previously out of sync; this roadmap replaces fragmented plans.

## 2. Completed work

### Core product

- [x] Desktop app shell with job queue, logging, and file processing.
- [x] Offline translation through Argos Translate.
- [x] EPUB import and EPUB export support.
- [x] Persistent novel library with chapter-level storage.
- [x] URL history and re-fetch UX.

### Crawler and workflow

- [x] lightnovel-crawler integration for novel search.
- [x] Chapter selection UX implemented (all, first N, custom range).
- [x] Improved URL support detection using crawler source metadata.
- [x] Generic crawler fallback/discovery path implemented.

### Glossary

- [x] Global glossary management.
- [x] Per-novel glossary management.
- [x] Glossary editor UI with CSV import/export.

### Documentation consolidation

- [x] Consolidated legacy markdown docs into `README.md`, `DEV.md`, `ROADMAP.md`, and `AGENTS.md`.

## 3. Immediate priorities (next steps)

### P0 - Architecture and correctness

- [x] Align production crawl execution with tested wrapper path (`main_window` vs wrapper split).
- [x] Remove or rewrite deprecated SageCrawler tests to match active runtime behavior.
- [x] Fix packaging spec icon reference so desktop builds are deterministic.
- [x] Resolve stale UI/help text that still claims removed crawler behavior.

### P1 - Reliability and performance

- [x] Refactor `MainWindow` into smaller controllers/services.
- [x] Add bounded concurrency for chapter downloads.
- [x] Add regression tests for current production crawl flow.
- [x] Remove low-risk lint debt (unused imports, trivial quality issues).

Scope note (2026-02-09): crawl/search orchestration moved further into services (`crawl_service.py`, `search_service.py`) and profile-driven crawl configuration.

## 4. Feature roadmap

### Milestone A - Crawl quality and control

- [x] Site-specific crawl settings (delay, user-agent, retries, robots override policy).
- [x] Resume interrupted downloads for partially fetched novels.
- [x] Batch URL crawling from list/queue input.
- [x] Improve progress granularity and stage reporting.
- [x] Direct EPUB export from crawler output path (avoid intermediate conversions where possible).

Implementation note (2026-02-09): batch crawling is available via File > Batch Crawl URLs and multiline URL paste in the fetch box.

### Milestone B - Translation quality and throughput

- [x] Translation memory/cache layer.
- [x] Optional additional translation backends beyond Argos.
- [x] Better chunking strategy for large chapters and language-specific punctuation.
- [x] Glossary performance improvements for large dictionaries.

Implementation note (2026-02-09): translation now supports backend selection (`argos`, optional `googletrans`, `echo`) with adaptive multilingual chunking and shared chunk-size controls.

### Milestone C - UX and product maturity

- [x] Multi-language UI support.
- [x] Stronger error surfaces with actionable recovery hints.
- [x] Unified settings model across desktop and CLI.
- [x] End-to-end release checklist automation.

Implementation note (2026-02-09): UI menu localization (English/Spanish), actionable recovery hints, shared desktop+CLI config bridge, and `python -m sagemtl release-check` automation are now in place.

## 5. Legacy items closed or deferred

- [x] Crawler toggle UI between SageCrawler and lncrawl closed as obsolete while SageCrawler remains deprecated. (Deferred)
- [x] "SageCrawler-only fallback" planning notes closed and superseded by the current architecture audit. (Deferred)

## 6. Definition of done for any roadmap item

- [ ] Implementation merged.
- [ ] Automated test coverage added or updated.
- [ ] `python -m pytest -m "not integration"` passes.
- [ ] Relevant docs (`README.md`, `DEV.md`, `AGENTS.md`, this file) updated.
