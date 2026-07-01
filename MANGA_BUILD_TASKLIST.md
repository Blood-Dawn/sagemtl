# SageMTL Manga Module: Phase Task List and Prompts

> Companion to `MANGA_MODULE_BUILD_SPEC.md`. Paste the master prompt once, then drive each phase with its prompt. Check the boxes as you go. Every phase ends at a gate; do not cross a gate that is red.

Definition of done for every phase: code implemented, tests written and passing (`python -m pytest -m "not integration"`), `python -m ruff check` clean on touched files, `ROADMAP.md` updated, acceptance gate met. Keep all ML imports lazy. Ship only permissive-licensed weights.

---

## Master kickoff prompt (paste into Claude Code first)

```
You are building the Manga module for SageMTL. Read these in full before writing code:
1. MANGA_MODULE_BUILD_SPEC.md  (the architecture, models, and per-stage detail)
2. MANGA_BUILD_TASKLIST.md      (the phase checklist and gates)
3. AGENTS.md and DEV.md         (repo conventions, test/lint commands)

Rules of engagement:
- Work ONE phase at a time, in order, starting at Phase 0. Do not jump ahead.
- For each phase: implement the checklist tasks, add tests, run
  `python -m pytest -m "not integration"` and `python -m ruff check`, then verify
  the acceptance gate. Stop and report at each gate before continuing.
- Reuse the existing core (JobManager, Translator, GlossaryManager, NovelLibrary
  pattern, app_settings, i18n, exporters). Do not duplicate them.
- Keep every torch/paddle/onnxruntime import lazy and inside core/manga/*; the
  novel path must not gain any heavy import. Test for this in Phase 0.
- Ship only Apache-2.0 / MIT / OFL weights and fonts. Never bundle NC models
  (Magi/Magiv2, NLLB, VARCO, TowerInstruct, Sugoi-v4-fairseq, FLUX weights).
- Update ROADMAP.md after each phase. Keep changes ASCII unless a file needs Unicode.

Begin with Phase 0. When its gate passes, report what you did and wait for my go-ahead
(or continue if I told you to run straight through).
```

---

## Phase 0: Skeleton and environment

**Goal:** package tree, config, lazy model registry, zero heavy imports at startup.

- [ ] Create the `core/manga/` and `ui/manga/` package trees and the `sagemtl_manga_crawler/` package per spec Section 2.1 (empty modules + `__init__.py`).
- [ ] Add the dataclasses: `TextRegion`, `PageResult` (spec 3, 2.3); `MangaPage`, `MangaChapter`, `MangaSeries` (spec 10.1); crawler `SeriesResult`, `ChapterRef`, `PageImage` (spec 9.1).
- [ ] Add `requirements-manga.txt` (spec Section 13), unpinned for now.
- [ ] Write `scripts/setup_manga.py` that installs `requirements-manga.txt` and warms the model cache.
- [ ] Implement `core/manga/model_registry.py`: `ensure(key)`, `load(key)` lazy singletons, `~/.sagemtl/models/` cache, CPU/CUDA auto-select. No download at import time.
- [ ] Add `MangaConfig` (spec 12) and wire load/save through `app_settings.py` and `~/.sagemtl/config.toml` with a `manga_` prefix. Validate enums on load. API keys come from env only.
- [ ] Add `MANGA_CRAWL`, `MANGA_TRANSLATE`, `MANGA_EXPORT` to `JobType` in `core/models.py`.

**Gate:** `python -c "import sagemtl_desktop.core.manga.pipeline"` succeeds and a test asserts `torch` is not in `sys.modules` after that import. `MangaConfig` round-trips through `config.toml`.

**Prompt:**
```
Do Phase 0 of MANGA_BUILD_TASKLIST.md. Create the package trees, dataclasses,
requirements-manga.txt, scripts/setup_manga.py, model_registry.py with lazy loaders,
and MangaConfig wired into app_settings.py + config.toml. Add the three manga JobTypes.
Write a test proving torch is NOT imported by importing core.manga.pipeline, and a
MangaConfig round-trip test. Run ruff + pytest, update ROADMAP.md, report at the gate.
```

---

## Phase 1: Detection and reading order

**Goal:** page in, text regions + mask + reading order out, with a visual debug overlay.

- [ ] Implement `core/manga/detect.py` against `ogkalu/comic-text-and-bubble-detector` via `onnxruntime`. Return regions (box, polygon, class) + full-page text mask.
- [ ] Add the segmenter fallback `ogkalu/comic-text-segmenter-yolov8m` for tighter masks.
- [ ] Implement `core/manga/reading_order.py`: JP right-to-left top-to-bottom, KO/ZH/webtoon left-to-right; optional `manga109/panel-order-estimator` for dense pages.
- [ ] Add a debug exporter that saves the page with boxes, class labels, and mask overlay to `~/.sagemtl/debug/`.
- [ ] Unit test reading order on synthetic boxes (2-panel JP returns right panel first).

**Gate:** on test images A1 (JP) and A5 (KR) from spec 15.3, boxes land on every visible text block and the overlay is saved. Ordering unit test passes.

**Prompt:**
```
Do Phase 1. Implement detect.py (ogkalu RT-DETR via onnxruntime) returning regions +
text mask, with the ogkalu segmenter as fallback. Implement reading_order.py with the
per-language heuristic and optional panel-order-estimator. Add a debug overlay exporter.
Pull test images A1 and A5 from spec 15.3 and save overlays. Add the synthetic-box
ordering unit test. Run ruff + pytest, update ROADMAP.md, report at the gate.
```

---

## Phase 2: OCR (routed)

**Goal:** fill `source_text` per region, routed by language, with VLM escalation.

- [ ] Implement `core/manga/ocr.py`: JP to `kha-white/manga-ocr-base`, KO/ZH to PaddleOCR PP-OCRv5, script detection reusing the Unicode logic in `translator.py:detect_language`.
- [ ] Add VLM escalation (`PaddlePaddle/PaddleOCR-VL` default) when confidence is low or the region is `text_free` (likely SFX).
- [ ] Log per-region engine used and confidence.
- [ ] Integration test on A1 / A3 / A5 (JP/ZH/KR): assert recognized text contains the expected script.

**Gate:** at least 80 percent of detected bubbles on each language test image return non-empty plausible text.

**Prompt:**
```
Do Phase 2. Implement ocr.py with language routing (manga-ocr for JP, PaddleOCR PP-OCRv5
for KO/ZH), script detection reusing translator.py detect logic, and VLM escalation via
PaddleOCR-VL on low confidence or text_free regions. Log engine + confidence per region.
Add a script-presence integration test on images A1/A3/A5. Run ruff + pytest, update
ROADMAP.md, report at the gate (>=80% non-empty).
```

---

## Phase 3: Translation (offline first, then cloud)

**Goal:** fill `target_text`, offline with no key, then optional cloud with page context.

- [ ] Implement the offline path FIRST in `core/manga/translate.py`: `haoranxu/X-ALMA-13B-Group6` (all CJK) or `sugoitoolkit/Sugoi-14B-Ultra-GGUF` (JP) via `llama-cpp-python`, plus `facebook/m2m100_1.2B` and existing Argos as light fallbacks.
- [ ] Inject glossary from `GlossaryManager` (per-series keyed by `series_id`); for sentence-level MT apply `apply_glossary()` pre and post.
- [ ] Implement `core/manga/providers.py` cloud path: one page image per call, glossary block, rolling summary, JSON-per-region output, retries with backoff on 429, per-chapter cost ceiling, provider configurable (Anthropic/Google/OpenAI).
- [ ] Use the prompt template in spec Appendix C.
- [ ] Mocked-provider unit test so CI needs no key.

**Gate:** offline run translates the JP page to coherent English with no API key set; glossary names appear verbatim; mocked cloud test passes.

**Prompt:**
```
Do Phase 3. Implement translate.py offline FIRST (X-ALMA / Sugoi-14B via llama-cpp,
m2m100, Argos), with GlossaryManager injection keyed by series_id. Then implement
providers.py for the cloud path: one page image per call, glossary + rolling summary,
JSON-per-region output, 429 backoff, per-chapter cost ceiling, provider configurable.
Use the Appendix C prompt. Add a mocked-provider test (no key needed). Confirm an offline
run needs no key. Run ruff + pytest, update ROADMAP.md, report at the gate.
```

---

## Phase 4: Erase and inpaint

**Goal:** clean page with text removed, no halos.

- [ ] Implement `core/manga/inpaint.py`: build mask from Stage 1 segmentation, threshold, dilate a few pixels (OpenCV).
- [ ] Flat-fill regions inside solid bubbles with sampled bubble color.
- [ ] Neural-inpaint text-over-art via `dreMaz/AnimeMangaInpainting` (LaMa), with `mayocream/aot-inpainting` as fallback. Option to wrap IOPaint instead.
- [ ] Save a side-by-side before/after debug image.

**Gate:** cleaned JP page shows no residual text and no halo on white bubbles. Assert mean pixel variance inside each mask drops toward the surrounding bubble.

**Prompt:**
```
Do Phase 4. Implement inpaint.py: mask build (threshold + dilate), flat-fill for solid
bubbles, neural inpaint via dreMaz/AnimeMangaInpainting with mayocream/aot-inpainting
fallback. Save before/after debug images. Add the residual-variance assertion test on the
JP page. Run ruff + pytest, update ROADMAP.md, report at the gate.
```

---

## Phase 5: Typeset and first end-to-end page

**Goal:** the first real milestone, a raw JP page becomes a translated typeset page.

- [ ] Implement `core/manga/typeset.py`: Pillow renderer, binary-search font fit, greedy wrap, `stroke_width`/`stroke_fill` outline, color/outline estimated from source region.
- [ ] Bundle Comic Neue (OFL) in `core/manga/fonts/`; add Bangers and Noto/Source Han for later.
- [ ] Wire `core/manga/pipeline.py:process_page` to run Stages 1 to 5 in sequence and return a `PageResult`.
- [ ] End-to-end test: raw JP page in, readable translated page out.

**Gate:** one raw JP page produces a fully translated typeset page, readable top to bottom, no text overflow outside bubbles. Demo it.

**Prompt:**
```
Do Phase 5. Implement typeset.py (Pillow + binary-search fit + stroke, color from source),
bundle Comic Neue, and wire pipeline.process_page to chain Stages 1-5 into a PageResult.
Add an end-to-end test on one JP page asserting text stays within bubble polygons. This is
the first demo milestone. Run ruff + pytest, update ROADMAP.md, report at the gate.
```

---

## Phase 6: Webtoon and long-strip

**Goal:** tall strips processed without cutting bubbles at a seam.

- [ ] Implement `core/manga/webtoon.py`: blank-row/low-variance split (ManhwaFormatter approach), overlap-tiling fallback with box de-duplication (`det_rearrange_forward` pattern), and restitch.
- [ ] Detect strip vs page by aspect ratio in `pipeline.py`; route strips through split then restitch.
- [ ] Test split points on a synthetic tall strip (no cut inside a marked bubble band).

**Gate:** a tall KR strip processes with no bubble cut across a seam and no visible seam in the restitched output.

**Prompt:**
```
Do Phase 6. Implement webtoon.py: blank-row split + overlap-tiling fallback with box
de-dup + restitch. Route tall strips in pipeline.py by aspect ratio. Add a synthetic-strip
split-point test (no cut inside a bubble band). Run ruff + pytest, update ROADMAP.md,
report at the gate.
```

---

## Phase 7: MangaDex crawler

**Goal:** search, download a chapter via the official API, export CBZ.

- [ ] Implement `sagemtl_manga_crawler/core/`: `source_base.py` (MangaSource ABC), `registry.py` (filesystem discovery + `_index.json` + `_rejected.json`), `fetch.py` (httpx, per-host rate limit, per-page Referer, retries), `rate_limit.py`.
- [ ] Implement `sources/mangadex.py` per spec 9.3: search, feed, at-home image URL construction, base-URL expiry handling (re-request on 403), image-report POST, public reads with no auth, 5 req/s limit.
- [ ] Implement `exporters/cbz_exporter.py`: page images + `ComicInfo.xml` into a `.cbz`, plus folder-per-chapter.
- [ ] Unit test: reconstruct page URLs from a recorded `/at-home/server` JSON. Integration test (network): download a public chapter, page count matches the feed.

**Gate:** MangaDex search returns results, a public chapter downloads all pages, the report POST fires, output opens as a valid CBZ.

**Prompt:**
```
Do Phase 7. Build the manga crawler core (MangaSource ABC, filesystem registry with
_index.json/_rejected.json, httpx fetch with rate limit + per-page Referer + retries) and
the MangaDex source per spec 9.3 (search, feed, at-home URL build, 403 re-request, image
report POST, 5 req/s). Add cbz_exporter with ComicInfo.xml. Unit-test URL reconstruction
from a recorded at-home JSON; mark the live download test `integration`. Run ruff + pytest,
update ROADMAP.md, report at the gate.
```

---

## Phase 8: Library, UI, reader

**Goal:** do the whole flow from inside the app.

- [ ] Implement `core/manga/library.py` (`MangaLibrary`) mirroring `novel_library.py`: disk layout in spec 10.2, `upsert_series_from_crawled`, resume by `source_url`, title-lock.
- [ ] Add the Novels/Manga mode switch to `MainWindow`; swap the central widget to `ui/manga/manga_view.py`.
- [ ] Add the `Manga` menu (Add by URL, Search Source, Translate Chapter, Open Reader, Export, Settings); wire each action to a `JobManager` job.
- [ ] Implement `ui/manga/reader_widget.py`: page view, before/after toggle, region overlay, per-page status.
- [ ] Add i18n keys to `en` and `es` in `ui/i18n.py`.

**Gate:** from the app, add a MangaDex series, translate a chapter, and read before/after pages. Progress and logs show in the existing panels.

**Prompt:**
```
Do Phase 8. Implement MangaLibrary (mirror novel_library.py, disk layout in spec 10.2).
Add the Novels/Manga mode switch, the Manga menu wired to JobManager jobs, and a reader
widget (before/after toggle + region overlay + status). Add en/es i18n keys. Keep UI thin;
logic stays in core/manga. Run ruff + pytest, update ROADMAP.md, report at the gate.
```

---

## Phase 9: Export

**Goal:** translated output to CBZ, PDF, and a page folder.

- [ ] Implement `core/manga/exporter.py`: translated CBZ (+ `ComicInfo.xml`), PDF (one image per page), per-page folder.
- [ ] Add CBZ/PDF options to `ui/export_dialog.py`.
- [ ] Test: exported CBZ and PDF open in a standard reader.

**Gate:** a translated chapter exports to CBZ and PDF, both open correctly.

**Prompt:**
```
Do Phase 9. Implement core/manga/exporter.py for translated CBZ (+ComicInfo.xml), PDF,
and folder output. Add the formats to export_dialog.py. Add an export round-trip test
(open the CBZ back, page count matches). Run ruff + pytest, update ROADMAP.md, report at
the gate.
```

---

## Phase 10: Manual correction and quality polish

**Goal:** fix mistakes fast, reuse models across pages.

- [ ] Implement `ui/manga/typeset_editor.py`: edit OCR text, edit translation, nudge placement, re-render that page only.
- [ ] Add per-region caching of OCR and translation by content hash (mirror the TM cache in `translator.py`).
- [ ] Reuse loaded models across pages in a chapter; add the rolling-summary context to cloud calls.

**Gate:** editing one bubble re-renders only that page in under a second on already-loaded models.

**Prompt:**
```
Do Phase 10. Implement typeset_editor.py for OCR/translation/placement fixes with
single-page re-render. Add per-region OCR/translation caching by content hash and model
reuse across a chapter, plus the rolling-summary context for cloud calls. Add a re-render
timing test on cached models. Run ruff + pytest, update ROADMAP.md, report at the gate.
```

---

## Phase 11: Packaging, docs, release

**Goal:** clean install, novel mode stays light, suite green.

- [ ] Pin versions in `requirements-manga.txt` against a confirmed working matrix.
- [ ] Update `pyinstaller-desktop.spec`: hidden imports, or first-run model download into `~/.sagemtl/models/` (preferred, smaller installer).
- [ ] Write `LICENSES-MANGA.md` listing every bundled model and font with its license; add a startup guard that refuses NC models unless "research mode" is enabled.
- [ ] Update `README.md`, `DEV.md`, `ROADMAP.md`, `AGENTS.md` for the manga module; document CPU-only vs CUDA install.
- [ ] Extend `python -m sagemtl release-check` to cover manga.

**Gate:** fresh-machine install works; novel mode launches with no manga deps present; manga mode prompts to install/download on first use; full test suite is green.

**Prompt:**
```
Do Phase 11. Pin requirements-manga.txt, update the PyInstaller spec for first-run model
download, write LICENSES-MANGA.md with a startup NC-model guard, update all four canonical
docs, and extend release-check to cover manga. Verify novel mode launches with no manga
deps installed. Run the full suite, update ROADMAP.md, report at the final gate.
```

---

## Progress tracker

| Phase | Title | Status | Gate met |
|---|---|---|---|
| 0 | Skeleton and environment | [x] | [x] |
| 1 | Detection and reading order | [x] | [x] |
| 2 | OCR (routed) | [x] | [x] |
| 3 | Translation | [x] | [x] |
| 4 | Erase and inpaint | [x] | [x] |
| 5 | Typeset and first end-to-end page | [x] | [x] |
| 6 | Webtoon and long-strip | [x] | [x] |
| 7 | MangaDex crawler | [x] | [x] |
| 8 | Library, UI, reader | [x] | [x] |
| 9 | Export | [x] | [x] |
| 10 | Manual correction and polish | [x] | [x] |
| 11 | Packaging, docs, release | [x] | [x] |

All phases complete (2026-06-30). Gate verification details per phase are in
`ROADMAP.md` (Milestone D). Integration gates are verified under `-m integration`
(detector/OCR/translate/inpaint/pipeline on Tier A images + live MangaDex).

First real demo lands at Phase 5. The crawler is independent of Phases 1 to 6, so Phase 7 can run in parallel if you have a second agent.
