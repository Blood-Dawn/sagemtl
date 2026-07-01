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
- Wrapper search now has non-integration regression coverage for lncrawl result-schema drift (grouped search results vs legacy result objects).
- Search UX now includes live progress-bar updates during source scanning (not only stage-log updates).
- Glossary enforcement now applies manager terms in processing flows with regression coverage for CJK contiguous-text matching.
- User-renamed novel titles now persist across resume crawls via title-lock semantics.
- Search UX now supports reopenable active-search progress dialogs, grouped novel results, and per-source chapter-count previews with top-row auto-prefetch.
- Manga module build started (Milestone D): Phase 0 skeleton landed with lazy ML imports, `MangaConfig`, model registry, and crawler scaffolding; the novel path gains no heavy import.
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

### Milestone D - Manga module

Adds a raw-manga translation system (detect -> OCR -> translate -> inpaint ->
typeset) plus a manga crawler, reusing the existing core (JobManager, Translator,
GlossaryManager, NovelLibrary pattern, app_settings, i18n, exporters). Heavy ML
deps (torch/paddle/onnxruntime) stay lazy inside `core/manga/*`; the novel path
gains no heavy import. Driven by `MANGA_MODULE_BUILD_SPEC.md` and
`MANGA_BUILD_TASKLIST.md`. Ship only permissive (Apache-2.0 / MIT / OFL) weights
and fonts.

- [x] Phase 0 - Skeleton and environment.
- [x] Phase 1 - Detection and reading order.
- [x] Phase 2 - OCR (routed).
- [x] Phase 3 - Translation (offline first, then cloud).
- [x] Phase 4 - Erase and inpaint.
- [x] Phase 5 - Typeset and first end-to-end page.
- [x] Phase 6 - Webtoon and long-strip.
- [x] Phase 7 - MangaDex crawler.
- [x] Phase 8 - Library, UI, reader.
- [x] Phase 9 - Export.
- [x] Phase 10 - Manual correction and quality polish.
- [x] Phase 11 - Packaging, docs, release.

Implementation note (2026-06-30): Phase 0 complete. Created the `core/manga/`,
`ui/manga/`, and `sagemtl_manga_crawler/` package trees; added the stage/persist
dataclasses (`TextRegion`, `PageResult`, `MangaPage`, `MangaChapter`,
`MangaSeries`) and crawler dataclasses (`SeriesResult`, `ChapterRef`,
`PageImage`); added `MangaConfig` wired through `app_settings.py` and
`sagemtl/config.py` with a `manga_` prefix (API keys read from env only); added a
lazy `model_registry.py` (`ensure`/`load` singletons, CPU/CUDA select, permissive
models only); added the three manga `JobType`s; added `requirements-manga.txt`
and `scripts/setup_manga.py`. Gate met: importing
`sagemtl_desktop.core.manga.pipeline` loads no torch/onnxruntime/numpy (verified
in a clean subprocess); `MangaConfig` round-trips through `config.toml`.

Implementation note (2026-06-30): Phase 1 complete. `detect.py` runs the default
`ogkalu/comic-text-and-bubble-detector` (RT-DETR-v2, Apache-2.0) via ONNX Runtime
(CPU-capable, no torch): preprocess RGB->640x640->/255 (no mean/std), inputs
`images` + `orig_target_sizes=[[W,H]]`, outputs labels/boxes(xyxy)/scores; classes
bubble/text_bubble/text_free; box-based union text mask; debug overlay
(`save_debug_overlay`) to `~/.sagemtl/debug/`. `reading_order.py` implements a
manga109-style layered recursive cut (horizontal tiers top-to-bottom, then
vertical columns RTL for JP / LTR for KO/ZH/webtoon) with optional panel grouping.
Gate met: on A1 (JP, 29 regions) and A5 (KR) the boxes land on the text and
overlays are saved (integration test); the 2-panel JP ordering is right-to-left
(unit test). Scope note: the tighter `comic-text-segmenter-yolov8m` mask is
deferred to Phase 4 (inpaint), run via ONNX Runtime to avoid an AGPL `ultralytics`
runtime dependency; the box-based mask meets the Phase 1 gate.

Implementation note (2026-06-30): Phase 2 complete. `ocr.py` routes recognition by
language: Japanese -> manga-ocr (recognition-only, multi-line); Korean/Chinese ->
PaddleOCR PP-OCRv5 (lang korean/ch). Because Stage 1 already localized regions,
Stage 2 recognizes each crop; PaddleOCR crops are padded + upscaled first (small
crops otherwise yield nothing) and run with `enable_mkldnn=False` (works around a
paddlepaddle 3.x oneDNN/PIR crash on some CPUs). Script detection mirrors
`translator.detect_language` (kana/Hangul prioritized) and back-fills `region.lang`.
VLM escalation (PaddleOCR-VL) fires on empty/low-confidence/`text_free` regions;
the logic is always active and unit-tested with a mock, the concrete VLM engine is
optional and degrades to a no-op when its deps are absent. Gate met: on A1 (JP,
manga-ocr), A3 (ZH) and A6 (KR) (PaddleOCR) >= 80% of detected text regions return
non-empty text in the expected script (integration test: all 100%). Scope note:
A5 (KR, 233px) is below OCR-usable resolution (~33%), so the higher-resolution
Tier A image A6 is the KR OCR fixture; A5 remains the Phase 1 detection fixture.

Implementation note (2026-06-30): Phase 3 complete. `translate.py` offline-first:
m2m100 (facebook/m2m100_1.2B, direct CJK->EN, default wired engine), Argos (reuses
the app Translator, lightest), and a llama.cpp GGUF engine for Sugoi/X-ALMA
(optional/heavy, degrades to empty if absent). Glossary reuses `GlossaryManager`
keyed by `series_id`: applied to the source pre-translation (so a name's target
rendering passes through verbatim) and to the output post-translation for
sentence-level engines, and injected as a prompt block for LLM engines.
`providers.py` adds the cloud path (Anthropic/OpenAI/Google) behind one
`BaseCloudProvider` with the Appendix C prompt, JSON-per-region parsing,
exponential backoff on transient/429 errors, a per-chapter `CostTracker` ceiling,
and an image-disabled fallback; the orchestration is fully unit-tested via an
injected `complete_fn` (no API key). Gate met: offline integration test
translates JP/ZH to English with no key and the glossary name appears verbatim;
mocked-provider unit tests pass (retry/backoff, cost ceiling, JSON parsing,
glossary block). Scope note: the default offline model in config (X-ALMA-13B) is
not auto-downloaded; m2m100 is the wired default and Sugoi/GGUF the optional
llama.cpp path. Gate verification convention: the model-level claim ("coherent
English through a real model") is proven by the `integration`-marked test, which is
deselected by the default `-m "not integration"` command and so is run explicitly
each phase; the default suite covers the wiring (lang mapping, src-lang
resolution, glossary pre/post, retry trigger `_map_transient`, mode routing). A CI
job that runs the integration gates is deferred to Phase 11.

Implementation note (2026-06-30): Phase 4 complete. `inpaint.py` is classical and
permissive by default (no torch, no AGPL): `build_mask` makes a tight glyph mask
per text region via Otsu thresholding (polarity auto-detected from the box border,
using OpenCV's binary output so perfectly-bimodal crops don't collapse) then
dilates; `run` flat-fills solid-color bubbles with the sampled background color
(flawless, no halo) and `cv2.inpaint` (Telea) handles text-over-art. An optional
`LamaInpainter` wraps IOPaint (Apache-2.0) and degrades to the classical path if
unavailable. `save_debug_sidebyside` writes an original|cleaned PNG. Gate met:
deterministic unit tests prove no residual text / no halo / variance drop on
synthetic bubbles; the A1 integration test confirms dark glyph coverage inside the
mask drops > 50% and saves a before/after image. Scope note: the deferred YOLO
segmenter mask (Phase 1) is replaced by the classical glyph mask to stay permissive
(its weights ship only as AGPL-`ultralytics` `.pt`); the classical mask meets the
gate.

Implementation note (2026-06-30): Phase 5 complete (first demo milestone).
`typeset.py` renders translated text with Pillow: `fit_text` binary-searches the
largest font size whose greedily-wrapped text fits the bubble, drawn centered with
a stroke outline; text/outline color is estimated from the cleaned bubble
background. Ships Comic Neue (OFL) under `core/manga/fonts/`.
`pipeline.MangaPipeline.process_page` now chains stages 1-5 (detect -> reading
order -> OCR -> translate -> inpaint -> typeset), caching loaded models across
pages and returning a `PageResult` with clean/rendered PNG bytes + per-stage
timings; `process_chapter` loops it. Gate met: deterministic typeset unit tests
prove text stays inside the bubble box (no overflow); the A1 end-to-end integration
test produces a fully translated, typeset page with no API key (offline m2m100) in
~75s and saves `~/.sagemtl/debug/phase5_A1_rendered.png`. Review fixes: render draws
each region onto a box-sized layer and pastes it clipped so text can never spill
even when it does not fit at min_font (small bubbles); a default-suite pipeline
wiring test (`tests/test_manga_pipeline.py`, monkeypatched stages) proves the
chain (right region set per stage, typeset gets the cleaned page, translate gets
the page bytes) without models.

Implementation note (2026-06-30): Phase 6 complete. `webtoon.py` handles tall
strips: `is_strip` (height/width >= 2.5), `split` cuts inside low-variance gutter
bands (per-row std) so a bubble is never sliced, with an overlap-tiling hard-cut
fallback when no gutter is near a needed cut; `restitch` reassembles tiles
losslessly for gutter cuts; `dedup_regions` removes seam-overlap duplicates by IoU;
`tiled_detect` runs the detector per tile and maps boxes to global coords.
`pipeline.process_page` routes strips through `tiled_detect` (the rest of the
chain runs on the full strip). Gate met: deterministic unit tests prove no cut
falls inside a bubble band and restitch is lossless; an integration test stacks the
real A1 page into a tall strip and confirms tiled detection finds text in both
halves with a lossless gutter restitch. Note: only classical CV (OpenCV) is used.
Review fix: the gutterless fallback now cuts at the lowest-activity row in the
window (lands between bubbles) and overlaps symmetrically on both sides, so bubbles
near a forced cut stay whole; a deterministic test with thin-gap (non-band) bubbles
asserts every bubble survives whole in some tile.

Implementation note (2026-06-30): Phase 7 complete. `sagemtl_manga_crawler` builds
the MangaDex official-API source: `rate_limit.TokenBucket` (per-host), `fetch.MangaFetcher`
(httpx, per-host rate limit, retries+backoff on 429/5xx, per-page Referer, honest
UA, injectable client for tests), `registry` (importlib discovery + `_index.json`),
and `sources/mangadex.py` (search/feed/at-home with pure parse helpers
`search_parse`/`feed_parse`/`build_page_urls`, `download_chapter` re-requesting
at-home on a stale 403, and image reporting to api.mangadex.network). Reporting is
fire-and-forget (short timeout, no retries, circuit-breaker after 3 failures) so an
unreachable report endpoint never blocks downloads -- this fixed a hang where 37
per-page reports each blocked ~90s. `exporters/cbz_exporter.py` writes CBZ +
ComicInfo.xml and folder layouts. Gate met: 16 unit tests (URL build, parse,
rate-limit, CBZ round-trip, registry, MockTransport search/at-home/report/403-reretry,
lazy-import) + a live integration test (search returns results; a public chapter
downloads all pages via at-home; CBZ is valid) pass. Read endpoints are public (no
auth/key). Review fix: `download_chapter`'s at-home refresh budget now counts
consecutive failures at the current page (reset on each successful page, default 3)
so a long chapter spanning several baseUrl expirations succeeds; the loop stays
bounded (a persistent 403 at one page still trips the budget).

Implementation note (2026-06-30): Phase 8 complete. `core/manga/library.py`
(`MangaLibrary`) mirrors `novel_library.py` with the spec 10.2 disk layout
(index.json + per-series series.json + raw/out page dirs), `upsert_series_from_crawled`
(resume by source_url, title-lock), and page-image save helpers. `core/manga/jobs.py`
holds Qt-free orchestration (`add_series_from_url`, `translate_chapter`,
`export_chapter`) wired with dependency injection so it is testable with fakes.
`ui/manga/reader_widget.py` (before/after toggle + region overlay + status) and
`ui/manga/manga_view.py` (series list + chapter selector + reader, buttons wired to
JobManager jobs) are thin PySide6 widgets. `MainWindow` gained a Novels/Manga mode
switch (a QStackedWidget wrapping the unchanged novel UI; the manga view is created
lazily so startup stays light) and a Manga menu (add/translate/reader/export). en/es
i18n keys added. Gate met: MangaLibrary CRUD/resume/title-lock, jobs (add/translate/
export with fakes), i18n, and offscreen Qt smoke tests (reader, manga view, and
MainWindow Novels<->Manga mode switch) all pass (213 non-integration total). Review
fixes: chapter merge on resume now keys off a stable identity (source_url, else
number|title, else id) instead of the minted uuid, so scraper sources that emit only
number+title dedup correctly on re-crawl; the MainWindow mode-switch test now only
skips on ImportError (real wiring regressions fail rather than green-via-skip).

Implementation note (2026-06-30): Phase 9 complete. `core/manga/exporter.py`
exports a translated chapter to CBZ (+ ComicInfo.xml, via the shared crawler
exporter), PDF (one image per page, Pillow), or a page folder; `jobs.export_chapter`
routes through it (PDF now works). `ui/export_dialog.py` gained an additive
`manga=True` mode offering CBZ/PDF/folder (novel txt/epub path unchanged), wired
into the MangaView export button. Gate met: CBZ round-trips to a valid ZIP with
ComicInfo and the right page count; the PDF has exactly one page per image
(verified with pypdfium2); the ExportDialog manga/novel modes and the jobs PDF path
are tested (218 non-integration total).

Implementation note (2026-06-30): Phase 10 complete. `ui/manga/typeset_editor.py`
(`TypesetEditor`) lets the user edit each region's OCR text + translation and nudge
its X/Y, then re-render just that page via `jobs.rerender_page` (typeset only -- no
models, sub-second). `ocr.run` and `translate.run` gained optional per-region
content-hash caches (crop hash for OCR; src-lang+target+glossary-pre-applied source
for MT) so re-runs do no recompute; `MangaPipeline` holds those caches and reuses
loaded models across a chapter. `process_chapter` threads a one-page rolling
summary (previous page's translations, truncated) into each page's translate call
(used by the cloud path). Gate met: `rerender_page` re-renders a page in well under
1s (deterministic test); OCR/MT cache-hit, rolling-summary threading, and the
editor edit+re-render are all tested (225 non-integration total). Review fixes: the
OCR cache key now includes the crop shape (byte-identical but differently-shaped
crops no longer collide to one wrong result); added editor X/Y placement-nudge
coverage (box moves, size preserved).

Implementation note (2026-06-30): Phase 11 complete -- the manga module (Milestone
D) is finished. `requirements-manga.txt` pinned to a confirmed Python 3.11 CPU
matrix (optional deps left commented). `LICENSES-MANGA.md` lists every model/font
license and the non-commercial policy; `model_registry` enforces it with a
research-mode guard (`set_research_mode`) that refuses non-commercial weights by
default. `pyinstaller-desktop.spec` documents the first-run-download approach (the
default installer still excludes numpy/PIL, so novel mode ships without manga deps).
README/DEV/AGENTS updated with the manga setup, architecture, and legal stance.
`python -m sagemtl release-check` extended with `manga_licenses` and
`manga_lazy_imports` checks (and lint/imports now cover `sagemtl_manga_crawler`).
Gate met: full release checklist passes (docs, lint, LICENSES present, manga
lazy-import guard, 227 non-integration tests, import smoke); the novel path gains
no heavy import so it launches without manga deps installed; manga deps/models
install on demand.

### Milestone E - Manga Studio + extensible sources

Post-module enhancements (2026-06-30):

- [x] Studio editor (manual cleaner + typesetter pass). `core/manga/studio.py`
  (`StudioModel` + `TextLayer`, Qt-free) holds an editable cleaned page plus freely
  positioned, richly styled text layers and the scanlation cleanup toolset (input
  levels/gamma, mask-paint re-inpaint, clone-stamp redraw, bubble fill, despeckle,
  reset) with a compositing `render`/`render_layer`. `ui/manga/studio.py`
  (`StudioWindow` + `StudioCanvas`) is a QGraphicsView canvas: drag text items,
  edit font/size/color/stroke/alignment/line-spacing/bold, paint masks and run the
  cleanup tools, then Save back to the library. Reached from the Manga view's "Open
  in Studio" button and the Manga menu; opens on the page shown in the reader and
  writes the re-rendered page back. Researched from scanlation cleaning/redrawing/
  typesetting practice (clean -> redraw -> typeset; levels, brush, clone, heal,
  despeckle).
- [x] Extensible sources (Mihon-style). Our `MangaSource` ABC already mirrors
  Mihon's HttpSource request/parse split; added `ParsedHttpSource`
  (`sagemtl_manga_crawler/core/http_source.py`) as a request/parse template so a
  user can add a source in a few lines, and `SuwayomiSource`
  (`sagemtl_manga_crawler/sources/suwayomi.py`) bridging to a user-run
  Suwayomi-Server (which runs their own Mihon extension APKs) -- reaching the whole
  Mihon catalog WITHOUT bundling any scraper (legally clean, the spec's
  bring-your-own-extensions path). `registry.build_source` selects mangadex |
  suwayomi by name; `MangaConfig`/`config.toml` gained `suwayomi_url` +
  `suwayomi_source_id`; translation uses the series' source. No piracy-site
  scrapers are shipped. Pure parse helpers + the source are unit-tested via
  httpx MockTransport (no network); a live Suwayomi server is user-supplied.

## 5. Legacy items closed or deferred

- [x] Crawler toggle UI between SageCrawler and lncrawl closed as obsolete while SageCrawler remains deprecated. (Deferred)
- [x] "SageCrawler-only fallback" planning notes closed and superseded by the current architecture audit. (Deferred)

## 6. Definition of done for any roadmap item

- [ ] Implementation merged.
- [ ] Automated test coverage added or updated.
- [ ] `python -m pytest -m "not integration"` passes.
- [ ] Relevant docs (`README.md`, `DEV.md`, `AGENTS.md`, this file) updated.
