# SageMTL Manga Module: Build Specification

> Single source-of-truth implementation plan for adding a raw-manga translation system to SageMTL, plus a manga crawler and a full app refresh. Written to be executed step by step by Claude Code. Every model ID, library, and test link below was verified during research (June 2026).

**Author of plan:** generated build spec
**Date:** 2026-06-29
**Target executor:** Claude Code (ultracode)
**Repo:** `sagemtl` (Python 3.13, PySide6 desktop app)

---

## 0. How to use this document

Read this top to bottom once before touching code. The build is split into ordered phases (Section 9). Each phase is independently testable and ends with an acceptance check. Do not skip the test assets in Section 10; they are the ground truth for "is the pipeline working."

Decisions already locked with the product owner:

| Decision | Choice |
|---|---|
| Source languages | Language-agnostic CJK. Detect script, route OCR per language (Japanese, Korean, Chinese). |
| Engine strategy | Hybrid. Local detection + OCR + inpaint always available offline. Optional cloud vision-LLM for top-tier translation. Offline fallback never requires a key. |
| Output style | In-place typesetting. Erase original text, inpaint the hole, redraw translated text fitted to the bubble. |
| App integration | New "Manga" section inside the existing PySide6 app, reusing the shared core (jobs, glossary/term system, library, settings, export). |

Guiding principle for licensing: ship only permissive weights and your own code. Treat GPL reference projects as study material, not as code to copy. Full detail in Section 11.

---

## 1. Current state of SageMTL (what you are extending)

SageMTL today is a desktop-first novel translator. Confirmed by reading the codebase:

**Stack:** Python 3.13, PySide6 6.10, `argostranslate` 1.10 (offline MT), optional `googletrans`, `lightnovel-crawler` 3.10.1, `ebooklib`, `httpx`, `beautifulsoup4`. Entry point `sagemtl_desktop/main.py` builds a `QApplication` and `MainWindow`.

**What already works (per the owner):** text cleaning returns the right extracted body, and the per-term grammar/glossary replacement (the "wtr lab term" system) applies correctly. Those two are the foundation the manga path reuses.

The modules you will reuse, with their real paths:

| Concern | File | Key symbols | Reuse for manga |
|---|---|---|---|
| App entry | `sagemtl_desktop/main.py` | `main()` | Unchanged. |
| Main UI | `sagemtl_desktop/ui/main_window.py` | `MainWindow`, `_create_menu_bar()`, left `FileListPanel`, center splitter, `LogPanel` | Add a Manga view/tab and menu. |
| Jobs/threads | `sagemtl_desktop/core/job_manager.py` | `JobManager`, `JobWorker(QThread)`, signals `progress_changed`, `log_emitted`; processor signature `processor(job, progress_cb, log_cb)` | Run every manga stage as a job. |
| Translation | `sagemtl_desktop/core/translator.py` | `Translator.translate(text, source_lang, target_lang, ..., backend, max_chunk_size)`, backends `argos`/`googletrans`/`echo`, in-memory TM cache, `detect_language()` | Reuse for the offline text-only fallback path and language detect. |
| Glossary / terms | `sagemtl_desktop/core/glossary_manager.py` | `GlossaryManager.apply_glossary(text, novel_id=None)`, global `~/.sagemtl/glossaries/global.json`, per-work `novels/{id}.json`, CJK-safe matching, CSV import/export | Reuse verbatim for character names and term consistency. Per-series glossary == per-novel glossary. |
| Legacy glossary | `sagemtl_desktop/core/glossary.py` | CSV compatibility | Leave as-is. |
| Library | `sagemtl_desktop/core/novel_library.py` | `NovelLibrary`, `SavedNovel`, `SavedChapter`, `upsert_novel_from_crawled(...)`, title-lock | Mirror the pattern for a manga library. |
| Crawl wrapper | `sagemtl_desktop/core/lightnovel_crawler_wrapper.py` | `LightNovelCrawlerWrapper(CrawlerInterface)`, `search_novel_by_name`, `discover_chapters`, `fetch_selected_chapters` | Architectural template for the manga source registry. |
| Crawl service | `sagemtl_desktop/core/crawl_service.py` | strategy selection, bounded concurrency, resume | Mirror for manga page download. |
| Crawl settings | `sagemtl_desktop/core/crawl_settings.py` | `CrawlSettings` (delay, retries, UA, workers, robots) | Reuse the dataclass shape per source. |
| Crawler base | `sagemtl_desktop/core/crawler_interface.py` | `CrawlerInterface` ABC | Subclass for `MangaSource`. |
| Generic crawler | `sagemtl_desktop/core/generic_crawler.py` | heuristic discovery + download | Template for generic manga-reader scraping. |
| Settings bridge | `sagemtl_desktop/core/app_settings.py` + `sagemtl/config.py` | `DesktopSettingsStore.load/save`, `~/.sagemtl/config.toml` | Add manga config fields here. |
| i18n | `sagemtl_desktop/ui/i18n.py` | `tr(language, key, **kwargs)`, `_TRANSLATIONS` (en/es) | Add manga string keys. |
| Clean pipeline | `sagemtl/clean/pipeline.py`, `text_normalize.py` | `clean_text()`, `normalize_text()` | Optional post-OCR cleanup of recognized text. |
| Export | `sagemtl_desktop/core/exporter.py`, `novel_exporter.py`, `epub_writer.py`, `ui/export_dialog.py` | EPUB/TXT writers, `ExportDialog` | Add CBZ/PDF writer alongside. |
| Shared models | `sagemtl_desktop/core/models.py` | `Job`, `JobType`, crawled models | Add manga dataclasses or a `manga/models.py`. |

Take-away: jobs, glossary, library, settings, i18n, and export are all generic enough to extend. The genuinely new work is the image pipeline (Sections 3 to 8) and the page-image crawler (Section 9).

---

## 2. Target architecture

### 2.1 New code layout

Add two new top-level package areas plus a crawler package, mirroring how `sagemtl_crawler` sits beside `sagemtl`.

```
sagemtl_desktop/
  core/
    manga/
      __init__.py
      models.py            # MangaSeries, MangaChapter, MangaPage, TextRegion, PageResult
      pipeline.py          # MangaPipeline: orchestrates stages 1..8 for one page/chapter
      detect.py            # Stage 1: bubble/text detection + masks
      reading_order.py     # Stage 1b: order regions per source language
      ocr.py               # Stage 2: routed OCR (manga-ocr / PaddleOCR / VLM escalation)
      translate.py         # Stage 3: cloud vision-LLM + offline MT, glossary injection
      inpaint.py           # Stage 4: mask build + LaMa/AOT fill
      typeset.py           # Stage 5: fit + render translated text into bubble
      webtoon.py           # Stage 6: long-strip split + restitch
      providers.py         # cloud LLM provider abstraction (key mgmt, retries)
      model_registry.py    # model IDs, download/caching, lazy load, device select
      library.py           # MangaLibrary persistence (mirrors novel_library.py)
      exporter.py          # CBZ / PDF / per-page folder export (+ ComicInfo.xml)
  ui/
    manga/
      __init__.py
      manga_view.py        # main Manga workspace widget (series list + reader)
      reader_widget.py     # page viewer with before/after toggle, region overlay
      manga_source_dialog.py  # search/add by URL or source search
      typeset_editor.py    # optional manual correction of OCR/translation/placement

sagemtl_manga_crawler/      # mirrors sagemtl_crawler; page-image sources
  __init__.py
  core/
    source_base.py         # MangaSource ABC (search, read_series, fetch_page_list, download_page)
    registry.py            # filesystem discovery sources/<lang>/<letter>/<site>.py + _index.json
    fetch.py               # httpx client w/ referer-per-page, retries, rate limit
    models.py              # SeriesResult, ChapterRef, PageImage
    rate_limit.py          # token bucket / per-host concurrency
  sources/
    mangadex.py            # FLAGSHIP legal source (official API)
    _index.json
    _rejected.json
  exporters/
    cbz_exporter.py
```

Rationale: keep the heavy image/ML code isolated under `core/manga/` so the existing novel path has zero new imports at startup. Everything ML is lazy-loaded (Section 8.4).

### 2.2 Data flow (one chapter)

```
MangaSource.fetch_page_list(chapter)        # crawler -> ordered page image URLs
  -> download_page() per page (referer set) # raw PNG/WebP/JPEG bytes preserved
  -> for each page:
       webtoon.split() if tall strip
       detect.run()       -> regions + masks
       reading_order.sort()
       ocr.run()          -> source text per region (routed by language)
       translate.run()    -> target text (glossary + page context)
       inpaint.run()      -> clean page (text erased)
       typeset.render()   -> final page (translated text drawn)
       webtoon.restitch() if split
  -> MangaLibrary.save()
  -> exporter.to_cbz() / to_pdf()
```

Every arrow above is a job stage that emits progress and logs through the existing `JobManager`.

### 2.3 The pipeline contract

`core/manga/pipeline.py` exposes one orchestrator the UI and CLI both call:

```python
@dataclass
class PageResult:
    index: int
    regions: list[TextRegion]      # box, polygon, mask ref, source_text, target_text, lang
    clean_image: bytes             # after inpaint
    rendered_image: bytes          # after typeset
    debug: dict                    # timings, model used per stage, confidences

class MangaPipeline:
    def __init__(self, config: MangaConfig, glossary: GlossaryManager): ...
    def process_page(self, image: bytes, *, source_lang: str | None,
                     series_id: str, page_index: int,
                     progress_cb=None, log_cb=None) -> PageResult: ...
    def process_chapter(self, pages: list[bytes], *, source_lang, series_id,
                        progress_cb=None, log_cb=None) -> list[PageResult]: ...
```

`MangaConfig` (Section 9 config) selects engine mode (`offline`, `hybrid`, `cloud`), model choices, target language, font, and cloud provider/key.

---

## 3. Stage 1: Bubble and text detection

**Goal:** turn a page into (a) text regions with boxes/polygons, (b) a per-pixel text mask for inpainting, (c) class labels (`bubble`, `text_bubble`, `text_free`).

**Default model:** [`ogkalu/comic-text-and-bubble-detector`](https://huggingface.co/ogkalu/comic-text-and-bubble-detector) (RT-DETR-v2, 42.9M params, Apache-2.0, ONNX + safetensors, ~1 to 2 GB VRAM, CPU-capable). Three classes, trained on manga + webtoon + manhua + western, and it splits tall webtoons vertically. This is the same detector `comic-translate` uses, so its behavior is well proven.

**Fallback (text mask quality):** [`ogkalu/comic-text-segmenter-yolov8m`](https://huggingface.co/ogkalu/comic-text-segmenter-yolov8m) (Apache-2.0) segments the glyphs themselves for a tighter erase mask. Pair with the bubble detector above.

**Fallback (bubble boxes, webtoon-robust):** [`ogkalu/comic-speech-bubble-detector-yolov8m`](https://huggingface.co/ogkalu/comic-speech-bubble-detector-yolov8m) (Apache-2.0).

**Optional panel detector (reading order aid):** [`mosesb/best-comic-panel-detection`](https://huggingface.co/mosesb/best-comic-panel-detection) (YOLOv12x, Apache-2.0).

**Heavy do-everything tier (do NOT ship weights):** `ragavsachdeva/magiv2` does panels + text + characters + reading order + speaker attribution, but it is research/non-commercial. Allow it only as a user-supplied optional engine, never bundled.

**Interface:**

```python
@dataclass
class TextRegion:
    box: tuple[int,int,int,int]      # x1,y1,x2,y2
    polygon: list[tuple[int,int]]    # tight outline
    cls: str                          # bubble | text_bubble | text_free
    mask: np.ndarray | None          # per-pixel text mask (uint8), page-cropped
    source_text: str = ""
    target_text: str = ""
    lang: str = ""
    conf: float = 0.0

class Detector:
    def __init__(self, model_id: str, device: str): ...
    def detect(self, image: np.ndarray) -> tuple[list[TextRegion], np.ndarray]:
        """Returns (regions, full_page_text_mask)."""
```

Libraries: `onnxruntime` (CPU or `onnxruntime-gpu`) for the ONNX weights, or `transformers` + `torch` for safetensors. Prefer ONNX for the default so CPU users work out of the box.

**Acceptance:** on the Japanese test page (Section 10), the detector returns >= 4 regions, and the union mask visibly covers the lettering when overlaid. Provide a debug export that saves the page with boxes + mask overlay.

---

## 4. Stage 1b: Reading order

No learned model is required. Use a heuristic keyed on source language:

- **Japanese manga:** right-to-left, top-to-bottom. Order panels and bubbles by proximity to the panel top-right corner.
- **Korean manhwa, Chinese manhua, webtoons:** left-to-right, top-to-bottom. Vertical-scroll strips are effectively one top-to-bottom column, so order by y.

For dense multi-panel manga pages, drop in [`manga109/panel-order-estimator`](https://github.com/manga109/panel-order-estimator) (Kovanen and Aizawa layered cut: recursive horizontal pivots top-to-bottom, then vertical pivots right-to-left for Japanese, handles two-page spreads and 4-koma). Feed it the panel boxes from the optional panel detector.

**Interface:** `reading_order.sort(regions, panels, source_lang) -> list[TextRegion]`.

**Acceptance:** on a 2-panel JP page, region order matches a human read (right panel before left). Add a unit test with synthetic boxes.

---

## 5. Stage 2: OCR (routed)

**Strategy:** specialized OCR by default, escalate hard regions to a vision-LLM. Detection quality matters more than recognition; if a region is missed in Stage 1, no OCR can save it.

| Source language | Default OCR | Repo / project | License | Notes |
|---|---|---|---|---|
| Japanese | manga-ocr | [`kha-white/manga-ocr-base`](https://huggingface.co/kha-white/manga-ocr-base) | Apache-2.0 | ViT encoder + transformer decoder, vertical + horizontal, furigana, multi-line bubble in one pass. ~110M, CPU-OK. 7.2M downloads. |
| Chinese, Korean | PaddleOCR PP-OCRv5 | [`PaddlePaddle/PP-OCRv5_server_det`](https://huggingface.co/PaddlePaddle/PP-OCRv5_server_det) + rec, or the `paddleocr` pip toolkit | Apache-2.0 | Simplified + Traditional Chinese, Korean recognizers, handles vertical/rotated/curved. Mobile tier runs on CPU. |
| Weak secondary | EasyOCR | [github.com/JaidedAI/EasyOCR](https://github.com/JaidedAI/EasyOCR) | Apache-2.0 | `ch_sim`/`ch_tra`/`ja`/`ko`. Easiest API, lowest accuracy. Last resort only. |

**VLM escalation (when specialized OCR is low-confidence, SFX, hand-lettered, or text-on-art):**

| VLM | Repo | License | Why |
|---|---|---|---|
| PaddleOCR-VL-0.9B | [`PaddlePaddle/PaddleOCR-VL`](https://huggingface.co/PaddlePaddle/PaddleOCR-VL) | Apache-2.0 | Sub-1B, 109 languages, fast. Best price/perf escalation. Updated 2026-06-27. |
| Qwen3-VL (4B/8B) | [`Qwen/Qwen3-VL-8B-Instruct`](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | Apache-2.0 | Max robustness on stylized text, 32 languages including CJK. |
| dots.mocr | [`rednote-hilab/dots.mocr`](https://huggingface.co/rednote-hilab/dots.mocr) | MIT | Layout + reading order + recognition in one VLM when you need bubble layout too. |

Korean note: there is no permissive manga-ocr equivalent for Hangul. Use PP-OCRv5 `ko` or a VLM. Avoid `OpenLLM-Korea/VARCO-VISION-2.0-1.7B-OCR` in any shippable build; it is CC-BY-NC.

**Routing logic:**

```
for region in regions:
    lang = region.lang or detect_script(region.crop)
    if lang == 'ja': text, conf = manga_ocr(region.crop)
    elif lang in ('ko','zh'): text, conf = paddle_ocr(region.crop, lang)
    if conf < CONF_THRESHOLD or region.cls == 'text_free' (SFX likely):
        text = vlm_ocr(region.crop)        # escalate
    region.source_text = text
```

`detect_script(crop)` can reuse the Unicode-range logic already in `translator.py:detect_language`.

**Interface:** `ocr.run(regions, page_image, source_lang, escalate=True) -> regions` (fills `source_text`).

**Acceptance:** on each language test image, >= 80% of detected bubbles produce non-empty plausible text. Log per-region confidence and which engine was used.

---

## 6. Stage 3: Translation (hybrid)

This is the hybrid lever: cloud vision-LLM by default for quality, local MT for the offline fallback. Both receive the injected glossary from `GlossaryManager`.

### 6.1 Cloud vision-LLM (default in hybrid/cloud mode)

Send the whole page image plus the detected source text plus the per-series glossary plus a 1-page rolling summary, and ask for one translated string per region as JSON. Whole-page context is what fixes dropped pronouns, honorifics (`-san`, `-nim`, formal vs informal), gendered voice, and name/term consistency. This is empirically the SOTA approach (COLING 2025, "Context-Informed Machine Translation of Manga using Multimodal LLMs", arXiv 2411.02589). Quality peaks at one page of full context, so do one page per call plus a short rolling summary, not a whole volume.

Provider abstraction lives in `core/manga/providers.py`. Pin a specific model snapshot in config; verify exact IDs in each provider console at build time, since these move.

| Provider | Current family (June 2026) | Role |
|---|---|---|
| Anthropic Claude | `claude-opus-4-8` (hard pages), `claude-sonnet-4-6` (production default), `claude-haiku-4-5` (bulk/cheap) | Best idiomatic and honorific fidelity. |
| Google Gemini | current Flash tier for bulk, current Pro tier for hard pages | Strong JP/KR/ZH, best cost at scale. Verify the live model ID. |
| OpenAI | current GPT-4.x / GPT-5-class vision model | Large-context workhorse, clean JSON-per-bubble output. Verify the live model ID. |

Treat provider + model as configuration. Do not hard-code a single vendor. The provider interface:

```python
class CloudTranslator(Protocol):
    def translate_page(self, page_png: bytes, regions: list[TextRegion],
                       glossary: list[GlossaryTerm], target_lang: str,
                       rolling_summary: str) -> list[str]:  # one per region
        ...
```

Implement retries, exponential backoff on 429, a hard token/cost ceiling per chapter, and a "redact then translate text-only" fallback if image upload is disabled.

### 6.2 Offline MT (fallback, no key)

| Model | Repo | License | Use |
|---|---|---|---|
| Sugoi 14B Ultra (GGUF) | [`sugoitoolkit/Sugoi-14B-Ultra-GGUF`](https://huggingface.co/sugoitoolkit/Sugoi-14B-Ultra-GGUF) | Apache-2.0 | Best offline JA to EN. Q4_K_M ~9 GB. Full context + glossary in system prompt. |
| X-ALMA-13B-Group6 | [`haoranxu/X-ALMA-13B-Group6`](https://huggingface.co/haoranxu/X-ALMA-13B-Group6) | MIT | Covers en/zh/ja/ko in one module. Best open all-CJK quality. |
| Qwen3-14B | [`Qwen/Qwen3-14B`](https://huggingface.co/Qwen/Qwen3-14B) | Apache-2.0 | Strong ja/ko/zh to en with glossary prompting. |
| m2m100 1.2B | [`facebook/m2m100_1.2B`](https://huggingface.co/facebook/m2m100_1.2B) | MIT | Tiny CPU last resort, direct CJK to EN (no English pivot). |
| Argos (existing) | already in app | MIT | Lightest fallback, lowest quality. Already wired in `translator.py`. |

License trap to enforce in code review: NLLB, TowerInstruct, Sugoi-v4-fairseq, and VARCO are non-commercial. Do not select them as a shippable default. The table above is commercial-safe.

Local LLM runners: `llama-cpp-python` for the GGUF models, `transformers` + `torch` for the rest. Lazy-load only when offline mode is selected.

### 6.3 Glossary and term injection (reuse the wtr lab term system)

For LLM translators (cloud or local), build the prompt from three parts: a system prompt (task + tone), a few-shot example, and a glossary block produced from `GlossaryManager.get_global_terms()` + per-series terms. For sentence-level MT (m2m100, Argos), apply `GlossaryManager.apply_glossary()` as pre-translation source rewrite and post-translation output fix, exactly as the novel path does. The per-series glossary is the same structure as the per-novel glossary; key it by `series_id`.

A ready prompt template lives in Appendix C.

**Interface:** `translate.run(regions, page_png, source_lang, target_lang, glossary, mode, rolling_summary) -> regions` (fills `target_text`).

**Acceptance:** translated output for the JP test page is coherent English, character names match the glossary, and an offline run with Sugoi/X-ALMA produces text without any API key set.

---

## 7. Stage 4: Erase and inpaint

**Goal:** remove original text and fill the hole so the page looks untouched.

Mask quality bounds everything here. Build the mask, then fill.

**Mask build:** take the Stage 1 text segmentation, threshold to binary, dilate a few pixels (OpenCV morphology) so anti-aliased edges, outlines, and drop-shadows are covered. Otherwise the inpainter leaves a faint glyph halo. The region you OCR (the box/polygon) is not the region you erase (the dilated mask).

**Hybrid fill:**
- If the masked text sits inside a detected solid-color bubble, flat-fill with the sampled bubble color. Fast and flawless, no ML.
- If text is over artwork (SFX on screentone, captions over background, free-floating manhwa text), neural-inpaint.

| Role | Model / lib | Repo | License |
|---|---|---|---|
| Default neural | LaMa, manga-finetuned | [`dreMaz/AnimeMangaInpainting`](https://huggingface.co/dreMaz/AnimeMangaInpainting) | MIT (verify the exact weight file you ship) |
| Fallback neural | AOT-GAN, manga-trained | ONNX [`mayocream/aot-inpainting`](https://huggingface.co/mayocream/aot-inpainting), arch [github.com/researchmm/AOT-GAN-for-Inpainting](https://github.com/researchmm/AOT-GAN-for-Inpainting) | Apache-2.0 arch |
| Heavy optional | FLUX.1 Fill or SDXL inpaint | [`black-forest-labs/FLUX.1-Fill-dev`](https://huggingface.co/black-forest-labs/FLUX.1-Fill-dev) | FLUX weights NC, do not bundle |
| Toolkit shortcut | IOPaint (was lama-cleaner) | [github.com/Sanster/IOPaint](https://github.com/Sanster/IOPaint) | Apache-2.0 |

The cleanest implementation is to wrap IOPaint, which bundles LaMa + a manga erase model + diffusion behind one CPU/GPU API. If you prefer fewer deps, load the `dreMaz/AnimeMangaInpainting` LaMa weights directly (same one manga-image-translator uses). Resize to ~512 to 1024 working side, pad to a multiple of 8.

**Interface:** `inpaint.run(page_image, text_mask, regions) -> clean_image`.

**Acceptance:** the cleaned JP page has no visible text and no halo where bubbles were solid white. Provide a side-by-side debug image.

---

## 8. Stage 5 and 6: Typeset, webtoon handling, and runtime concerns

### 8.1 Stage 5: Typeset / re-letter

Default renderer is Pillow: `ImageFont` + `ImageDraw.text` with `stroke_width`/`stroke_fill` for the white-outline-on-black look. Fit text by binary-searching the font size: pick a max size, greedily wrap to the bubble width, measure with `font.getbbox`, shrink and repeat until it fits. Optional hyphenation via `pyphen`, but expose a `no_hyphenation` flag since hyphens look wrong in comics. Estimate text color and outline from the original region (BallonsTranslator does this).

For real vertical Japanese (tate-gaki) or mixed-script vertical CJK, the Pillow path is not enough. Provide an optional HarfBuzz/Pango (or skia) renderer with OpenType `vert`/`vrt2` and right-to-left column order. The koharu project is the reference implementation. For an English target on modern manhwa/manhua (mostly horizontal), default Pillow is correct, and vertical is a per-region feature.

**Fonts:** ship only OFL/CC0/Apache fonts. Default to **Comic Neue** (SIL OFL, [github.com/crozynski/comicneue](https://github.com/crozynski/comicneue)). Add **Bangers** (OFL) for SFX/titles and **Noto Sans CJK / Source Han Sans** (OFL) for vertical CJK output. Put them in `sagemtl_desktop/core/manga/fonts/`. Let users drop their own Wild Words or Anime Ace into that folder; do not bundle those (proprietary / non-commercial).

**Interface:** `typeset.render(clean_image, regions, font_cfg, target_lang) -> rendered_image`.

**Acceptance:** the rendered JP page reads cleanly, text stays inside bubbles, and nothing overflows. A reviewer can read the page top to bottom.

### 8.2 Stage 6: Webtoon / long-strip

A webtoon is one image thousands of pixels tall. Cut it into model-sized segments without slicing through a bubble, process, then restitch.

1. **Blank-row / gutter detection (default):** scan rows, compute per-row variance; cut only inside wide low-variance bands (solid white or black dividers). Reference: [`eskutcheon/ManhwaFormatter`](https://github.com/eskutcheon/ManhwaFormatter) (MIT).
2. **Overlap tiling fallback:** when clean gutters are sparse, use fixed-height tiles (~2000 to 3000px) with an overlap margin, then de-duplicate boxes in the overlap. The canonical tensor-level pattern is manga-image-translator's `det_rearrange_forward` ([PR #146](https://github.com/zyddnys/manga-image-translator/pull/146)): reshape the strip into overlapping patches, detect once, un-rearrange logits, average overlaps.

**Interface:** `webtoon.split(strip) -> list[(tile, y_offset)]` and `webtoon.restitch(tiles) -> strip`.

**Acceptance:** a tall Korean strip is split with no bubble cut across a seam, and the restitched output has no visible seam line.

### 8.3 Model registry, download, and caching

`core/manga/model_registry.py` centralizes every model ID, the HF download (`huggingface_hub.snapshot_download`), a local cache under `~/.sagemtl/models/`, device selection (CUDA if available else CPU), and a first-run download manager that the UI can show progress for. Never download at import time. Expose `ensure(model_key) -> path` and `load(model_key) -> handle` with lazy singletons.

### 8.4 Performance and packaging

- Lazy-import torch/onnxruntime/paddle only inside `core/manga/*` functions, never at module top level, so launching the novel side stays fast and PyInstaller can exclude them when manga is unused.
- Process pages on a `JobWorker` thread; never block the UI.
- Batch within a chapter; reuse loaded models across pages.
- Cache OCR and translation per region hash so re-runs are cheap (mirror the TM cache in `translator.py`).
- Heavy deps (`torch`, `onnxruntime`, `paddleocr`, `opencv-python`, `shapely`, `huggingface_hub`, `llama-cpp-python`) go in a new `requirements-manga.txt`, installed on demand, not in `requirements-desktop.txt`.

---

## 9. The manga crawler

Build this as a sibling to the novel crawler, reusing the same mental model. The one conceptual change from novels to manga: a chapter is not an HTML body, it is an ordered list of page-image URLs. So `download_chapter` becomes `fetch_page_list`. Almost everything downstream (registry discovery, rate limiting, retries, resume) ports nearly unchanged from `lightnovel-crawler` and your existing `crawl_service.py`.

### 9.1 Source plugin contract

`sagemtl_manga_crawler/core/source_base.py`:

```python
@dataclass
class SeriesResult: title: str; url: str; source: str; cover: str | None

@dataclass
class ChapterRef: id: str; number: str; title: str; url: str; lang: str

@dataclass
class PageImage: index: int; url: str; referer: str | None; headers: dict

class MangaSource(ABC):
    base_url: str
    lang: str                 # 'ja','ko','zh','en',...
    name: str
    is_webtoon: bool = False
    nsfw: bool = False
    can_search: bool = True

    @abstractmethod
    def search(self, query: str) -> Iterable[SeriesResult]: ...
    @abstractmethod
    def read_series(self, url: str) -> tuple[dict, list[ChapterRef]]: ...   # meta, chapters
    @abstractmethod
    def fetch_page_list(self, chapter: ChapterRef) -> list[PageImage]: ...   # the core manga method
    def download_page(self, page: PageImage, dest: Path) -> Path:            # preserve format + referer
        ...
```

Split each network method into a request builder and a parse step (Mihon's `*_request` / `*_parse` pattern) so HTML, JSON, and API sources share plumbing. Preserve original image format (PNG/WebP/JPEG), do not force-JPEG. Always set `Referer` to the reader page; manga CDNs hotlink-protect.

### 9.2 Source registry and discovery

Copy the lightnovel-crawler convention verbatim: `sources/<lang>/<letter>/<site>.py`, dynamic `importlib` discovery, a filter that keeps concrete `MangaSource` subclasses with a valid `base_url`, a prebuilt `sources/_index.json` (carrying `name`, `lang`, `is_webtoon`, `nsfw`, `base_urls`), and a `sources/_rejected.json` host-to-reason map to disable dead sites without deleting code. Ship template base classes (a generic manga-reader template, plus Madara and MangaThemesia theme bases) so most sources reduce to ~10 lines of CSS selectors.

### 9.3 Flagship source: MangaDex (implement first)

MangaDex has an official, free, well-documented REST API. It needs no scraping and no Cloudflare solving, and it is the clean legal default. Verified live in June 2026.

**Base URLs:**

| Purpose | URL |
|---|---|
| REST API | `https://api.mangadex.org` |
| Covers | `https://uploads.mangadex.org/covers/{mangaId}/{filename}` |
| Image report | `https://api.mangadex.network/report` (note `.network`) |
| Auth (OAuth2) | `https://auth.mangadex.org` |

**Key endpoints:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/manga?title=...&limit=...&includes[]=cover_art` | Search series |
| GET | `/manga/{id}/feed?translatedLanguage[]=ja&order[chapter]=asc` | Chapter list |
| GET | `/at-home/server/{chapterId}` | Image delivery metadata |
| GET | `/chapter/{id}` | One chapter |
| POST | `https://api.mangadex.network/report` | Report image success/failure |

**Page URL construction:**
1. `GET /at-home/server/{chapterId}` returns `baseUrl`, `chapter.hash`, `chapter.data[]` (full) and `chapter.dataSaver[]` (compressed).
2. Build each page: `{baseUrl}/data/{hash}/{data[i]}` (full quality) or `{baseUrl}/data-saver/{hash}/{dataSaver[i]}`.
3. `baseUrl` expires in ~15 minutes; a stale one returns 403, so re-call the at-home endpoint.
4. For every image fetched from a non-`mangadex.org` node, POST a small report `{url, success, cached, bytes, duration}` to the report endpoint. This keeps the volunteer CDN healthy.

**Auth:** read endpoints (search, feed, at-home, cover) are fully public, no token. Only authenticated actions use OAuth2 personal clients. Send auth only to `api.mangadex.org` / `auth.mangadex.org`, never to the CDN.

**Rate limits:** global ~5 requests/second per IP; `/at-home/server` 40/min; `/report` 10/min. Honor `X-RateLimit-*` headers and back off on 429. Pagination `offset + limit <= 10000`, `limit` max 100 (500 on some feeds).

**ToS to follow in code and docs:** credit MangaDex, credit scanlation groups and honor takedowns, no ads or paid access on their content, no mass-scraping (use server-side filters + pagination), send an honest non-spoofed `User-Agent`, never send a `Via` header, proxy users' image requests through your backend rather than hotlinking.

### 9.4 Fetch, rate limit, retries

`sagemtl_manga_crawler/core/fetch.py`: an httpx client with a per-host token-bucket rate limiter, bounded concurrency (manga is 20 to 40 images per chapter, so throttling matters more than for novels), retries with backoff, per-page `Referer`, and robots/ToS respect. Reuse the shape of your `CrawlSettings` dataclass (delay, retries, user-agent, workers, robots policy) per source.

For sites behind Cloudflare or aggressive hotlink protection, do not bundle a bypass. Either skip the site or support pointing at a user-run [Suwayomi-Server](https://github.com/Suwayomi/Suwayomi-Server) (MPL-2.0) GraphQL endpoint so power users bring their own extensions while your distribution stays clean.

### 9.5 Output

`sagemtl_manga_crawler/exporters/cbz_exporter.py`: write `NNN_PPP.<ext>` page images plus a `ComicInfo.xml` sidecar into a `.cbz` (ZIP), and support a raw folder-per-chapter layout. CBZ with `ComicInfo.xml` is the native manga target. For PDF, stitch one image per page. The translated output (after the pipeline) exports the same way through `core/manga/exporter.py`.

### 9.6 Mapping table (novel crawler to manga crawler)

| lightnovel-crawler / SageMTL novel path | Manga analog |
|---|---|
| `Crawler` ABC + capability flags | `MangaSource` ABC + `is_webtoon`/`nsfw` |
| `download_chapter` sets `chapter.body` HTML | `fetch_page_list` returns ordered page image URLs |
| embedded-image extraction | first-class page images, format preserved, referer set |
| Madara/Soup templates | manga-reader + Madara + MangaThemesia templates |
| `importlib` discovery + `_index.json` | identical, plus `_rejected.json` |
| bounded chapter workers + resume | identical, tighter per-host caps |
| EPUB/TXT export | CBZ + `ComicInfo.xml`, folder, PDF |

### 9.7 Crawler legal stance (put this in the UI and README)

Default and promote the MangaDex official-API source. Ship the adapter framework and legal sources; treat third-party site modules the way Mihon does, as separately installed user extensions the app does not host. Frame the tool for content the user has a right to access (purchased, official, public-domain, or their own scans). Respect copyright, site ToS, robots.txt, and declared rate limits. Full guidance in Section 16.

---

## 10. Data models and persistence

### 10.1 Models (`core/manga/models.py`)

```python
@dataclass
class MangaPage:
    index: int
    source_image_path: str        # raw downloaded page
    clean_image_path: str = ""     # after inpaint
    rendered_image_path: str = ""  # after typeset
    regions: list[dict] = field(default_factory=list)  # serialized TextRegion (no numpy)
    status: str = "pending"        # pending|ocr|translated|typeset|done|error

@dataclass
class MangaChapter:
    chapter_id: str
    number: str
    title: str
    source_url: str
    lang: str
    pages: list[MangaPage]
    is_webtoon: bool = False

@dataclass
class MangaSeries:
    series_id: str                 # uuid
    title: str
    source_url: str
    source_name: str               # e.g. 'mangadex'
    cover_path: str
    lang: str
    chapters: list[MangaChapter]
    title_locked: bool = False
    created_at: str = ""
    updated_at: str = ""
```

### 10.2 Library (`core/manga/library.py`)

Mirror `novel_library.py`. Store under `~/.sagemtl/library/manga/`:

```
manga/
  index.json                       # list of MangaSeries metadata (no page blobs)
  {series_id}/
    series.json                    # full MangaSeries with chapters/pages
    cover.jpg
    raw/{chapter}/{page}.ext       # downloaded originals
    out/{chapter}/{page}.png       # rendered translated pages
```

Keep image bytes on disk, not in JSON. The index holds metadata only so the library list loads fast. Implement `upsert_series_from_crawled(...)`, resume by `source_url`, and title-lock semantics identical to the novel library so user renames persist across re-crawls. Reuse `GlossaryManager` keyed by `series_id` for per-series character/term glossaries.

---

## 11. UI integration

Add a Manga workspace without disturbing the novel UI. The owner approved a light refresh, so use a top-level mode switch.

1. **Mode switch:** add a left-rail or top toggle in `MainWindow` between "Novels" and "Manga". Manga mode swaps the central widget to `ui/manga/manga_view.py`.
2. **Manga menu:** in `_create_menu_bar()`, add a `Manga` menu with: Add Series by URL, Search Source, Translate Selected Chapter(s), Open Reader, Export CBZ/PDF, Manga Settings. Wire each `QAction.triggered` to a `MainWindow` slot that creates a `JobManager` job.
3. **Manga view:** a series list (reuse the `FileListPanel` pattern) plus a reader. The reader (`reader_widget.py`) shows a page with a before/after toggle, an optional region overlay (boxes + recognized + translated text), and per-page status. Progress and logs flow through the existing `LogPanel` via job signals.
4. **Job types:** extend `JobType` in `core/models.py` with `MANGA_CRAWL`, `MANGA_TRANSLATE`, `MANGA_EXPORT`. Each stage reports progress 0 to 100 so the existing progress bar works unchanged.
5. **Manual correction (optional, high value):** `typeset_editor.py` lets the user fix a wrong OCR string, edit a translation, or nudge text placement, then re-render just that page. This mirrors BallonsTranslator ergonomics and dramatically improves output quality.
6. **i18n:** add keys to both `en` and `es` dicts in `ui/i18n.py` (`menu.manga`, `action.manga_add`, `action.manga_translate`, etc.). Follow the existing `namespace.key` convention.

Keep UI logic thin per `AGENTS.md`: the view calls into `core/manga/*`, business logic never lives in the widget.

---

## 12. Settings and configuration

Extend the existing settings bridge (`core/app_settings.py` + `sagemtl/config.py`), do not invent a new config system. Add a `MangaConfig` and persist its fields to `~/.sagemtl/config.toml` with a `manga_` prefix.

```python
@dataclass
class MangaConfig:
    engine_mode: str = "hybrid"        # offline | hybrid | cloud
    target_lang: str = "en"
    source_lang: str = "auto"          # auto | ja | ko | zh
    # models
    detector_model: str = "ogkalu/comic-text-and-bubble-detector"
    ja_ocr_model: str = "kha-white/manga-ocr-base"
    cjk_ocr_engine: str = "paddleocr"  # paddleocr | easyocr
    ocr_vlm_model: str = "PaddlePaddle/PaddleOCR-VL"
    inpaint_model: str = "dreMaz/AnimeMangaInpainting"
    offline_mt_model: str = "haoranxu/X-ALMA-13B-Group6"
    # cloud
    cloud_provider: str = "anthropic"  # anthropic | google | openai | none
    cloud_model: str = "claude-sonnet-4-6"
    cloud_api_key_env: str = "ANTHROPIC_API_KEY"   # read key from env, never store in toml
    cost_ceiling_usd_per_chapter: float = 1.0
    # typeset
    font_path: str = "core/manga/fonts/ComicNeue-Bold.ttf"
    enable_vertical_cjk: bool = False
    # device
    device: str = "auto"               # auto | cpu | cuda
```

Store API keys only in environment variables or the OS keyring, never in `config.toml`. Validate `engine_mode`, `cloud_provider`, and `device` on load like the existing `_VALID_BACKENDS` check.

---

## 13. Dependencies

Create `requirements-manga.txt` (installed on demand, not at app launch):

```
# core image + ML
numpy
opencv-python-headless
pillow>=10
shapely
huggingface_hub
onnxruntime            # or onnxruntime-gpu when CUDA present
torch                  # CPU or CUDA build per platform
transformers
# OCR
manga-ocr
paddleocr
paddlepaddle           # or paddlepaddle-gpu
easyocr                # optional secondary
# inpaint (option A, direct): load LaMa weights via torch
# inpaint (option B: toolkit)
iopaint
# offline LLM translation
llama-cpp-python       # for GGUF (Sugoi/Qwen) ; optional
# typeset vertical CJK (optional)
# system libs: harfbuzz, pango  (document install per OS)
# cloud providers
anthropic
google-genai
openai
```

Notes for the implementer:
- Pin versions during Phase 0 once you confirm a working matrix on the target machine. Leave them unpinned here so you resolve against current wheels.
- Keep all of the above out of `requirements-desktop.txt`. Gate the import behind `engine_mode` and the model registry so a user who never opens Manga mode pays nothing.
- `paddlepaddle` and `torch` are the heavy ones; offer a "CPU-only" and a "CUDA" install path in the README.
- For PyInstaller, add hidden-imports and data files for the chosen models, or download models at first run into `~/.sagemtl/models/` (preferred, smaller installer).

---

## 14. Step-by-step build plan

Each phase is ordered, independently testable, and ends with an acceptance gate. Do not start a phase until the previous gate passes. Run `python -m ruff check` and the relevant tests after every phase, and update `ROADMAP.md` (the repo convention).

### Phase 0: Skeleton and environment
- Create the package tree from Section 2.1 with empty modules and the dataclasses from Sections 3, 10.
- Add `requirements-manga.txt` and a `scripts/setup_manga.py` that installs it and warms the model cache.
- Implement `model_registry.py` with `ensure()` / `load()` lazy singletons and a CPU/CUDA selector.
- Add `MangaConfig` and wire it through `app_settings.py` and `config.toml`.
- **Gate:** `python -c "import sagemtl_desktop.core.manga.pipeline"` succeeds with zero heavy imports loaded (assert torch is not in `sys.modules`).

### Phase 1: Detection + reading order
- Implement `detect.py` against `ogkalu/comic-text-and-bubble-detector` (ONNX via onnxruntime).
- Implement `reading_order.py` heuristic + optional panel-order estimator.
- Add a debug exporter that saves the page with boxes, class labels, and the mask overlay.
- **Gate:** on the JP and KR test images (Section 15.3), boxes visibly land on every text area; the overlay is saved; reading order on a 2-panel JP page is right-to-left. Unit test with synthetic boxes for ordering.

### Phase 2: OCR routing
- Implement `ocr.py`: manga-ocr for JP, PaddleOCR for KO/ZH, script detection via the existing Unicode logic, and VLM escalation on low confidence or `text_free` regions.
- **Gate:** >= 80% of detected bubbles on each language test image return non-empty plausible text; per-region engine + confidence logged.

### Phase 3: Translation
- Implement the offline path FIRST (no key needed): wire `X-ALMA-13B-Group6` (all-CJK) or `Sugoi-14B-Ultra` (JP) through `llama-cpp-python`, plus `m2m100_1.2B` and existing Argos as light fallbacks. Inject glossary via `GlossaryManager`.
- Then implement `providers.py` cloud path with one page image per call, glossary block, rolling summary, JSON-per-region output, retries, and the per-chapter cost ceiling.
- **Gate:** offline run translates the JP page to coherent English with zero API key set; cloud run (if a key is present) returns one string per region and respects glossary names. Add a mocked-provider unit test so CI needs no key.

### Phase 4: Inpaint
- Implement `inpaint.py`: build dilated mask from Stage 1 segmentation, flat-fill solid bubbles, neural-inpaint text-on-art via `dreMaz/AnimeMangaInpainting` (or wrap IOPaint).
- **Gate:** cleaned JP page shows no residual text and no halo on white bubbles; side-by-side debug image saved.

### Phase 5: Typeset and first end-to-end page
- Implement `typeset.py`: Pillow renderer, binary-search font fit, stroke outline, color/outline estimated from source, Comic Neue default.
- Wire `pipeline.py:process_page` to run Stages 1 to 5 in sequence.
- **Gate:** a single raw JP page goes in, a fully translated typeset page comes out, readable end to end. This is the first real milestone, demo it.

### Phase 6: Webtoon handling
- Implement `webtoon.py`: blank-row split + overlap-tiling fallback + restitch.
- **Gate:** a tall KR strip processes with no bubble cut at a seam and no visible seam in the restitched output.

### Phase 7: MangaDex crawler
- Implement `sagemtl_manga_crawler` core (source base, registry, fetch with rate limit/referer) and the MangaDex source per Section 9.3.
- Implement CBZ + folder export with `ComicInfo.xml`.
- **Gate:** search "Test" on MangaDex returns results; a public chapter downloads all pages via the at-home flow; report POST fires; output opens as a valid CBZ.

### Phase 8: Library, UI, reader
- Implement `MangaLibrary` (Section 10.2).
- Add the Manga mode switch, menu, series list, and reader to the UI; wire `MANGA_CRAWL` / `MANGA_TRANSLATE` / `MANGA_EXPORT` jobs.
- Add i18n keys (en/es).
- **Gate:** from the app, add a MangaDex series, translate a chapter, and read before/after pages in the reader. Progress and logs show in the existing panels.

### Phase 9: Export
- Implement `core/manga/exporter.py` to write translated CBZ/PDF and a per-page folder; add format options to `ExportDialog`.
- **Gate:** translated chapter exports to CBZ and PDF; both open in a standard reader.

### Phase 10: Manual correction + quality polish
- Implement `typeset_editor.py` for OCR/translation/placement fixes and single-page re-render.
- Add per-region caching, batch model reuse across pages, and the rolling-summary context.
- **Gate:** editing one bubble re-renders only that page in under a second on cached models.

### Phase 11: Packaging, docs, release
- Update `requirements-manga.txt` pins, PyInstaller spec (hidden imports or first-run download), `README.md`, `DEV.md`, `ROADMAP.md`, `AGENTS.md`.
- Extend `python -m sagemtl release-check`.
- **Gate:** clean install on a fresh machine, novel mode launches without manga deps, manga mode prompts to install/download on first use, full test suite green.

---

## 15. Testing strategy and test assets

### 15.1 Test pyramid
- **Unit (no network, no GPU):** reading-order on synthetic boxes, mask dilation, font-fit binary search, webtoon split points on a synthetic strip, glossary injection string-building, MangaDex URL construction from a recorded at-home JSON, JSON-per-region parsing. Mock the cloud provider so CI needs no key.
- **Integration (local models, no network):** detector + OCR + inpaint + typeset on bundled fixture images; assert region counts, non-empty OCR, no-residual-text after inpaint (mean ink in mask region drops below a threshold), and that the rendered page differs from the clean page where regions are.
- **End to end (network + models):** MangaDex search and chapter download, then a full translate of one chapter, behind an `integration` pytest marker (the repo already separates these with `-m "not integration"`).

### 15.2 Fixture handling
Add `tests/manga/fixtures/` and a `scripts/fetch_test_assets.py` that downloads the public-domain images in 15.3 once and caches them. Commit only the small public-domain images; pull the larger ones at test time. Keep a golden-output folder for visual regression (compare structural similarity, not exact bytes).

### 15.3 Test images to pull and translate (verified June 2026)

**Tier A: public-domain / CC, safe to commit and redistribute.** Use these as the primary automated fixtures.

| # | Language | URL | Content | License |
|---|---|---|---|---|
| A1 | JP | `https://upload.wikimedia.org/wikipedia/commons/9/94/Tagosaku_to_Mokube_no_Tokyo_Kenbutsu.jpg` | Kitazawa Rakuten, 1902, multi-panel with JP captions/dialogue | PD |
| A2 | JP | `https://upload.wikimedia.org/wikipedia/commons/6/6d/Tokyo_Puck_-_Februari_1909%2C_RP-P-2005-572.jpg` | Tokyo Puck 1909 color cartoon with JP text, hi-res | CC0 |
| A3 | ZH | `https://upload.wikimedia.org/wikipedia/commons/d/da/%E8%BF%9E%E7%8E%AF%E5%B9%B4%E7%94%BB_%E7%8E%89%E9%BA%92%E9%BA%9F_%E4%B9%8B%E5%9B%9B.jpg` | Late-Qing lianhuanhua with in-panel Chinese text | PD |
| A4 | ZH | `https://upload.wikimedia.org/wikipedia/commons/5/50/Issue_1%2C_Lianhuanhua_Bao.png` | Lianhuanhua Bao issue 1 (1951), large title calligraphy | PD |
| A5 | KR | `https://upload.wikimedia.org/wikipedia/commons/e/e5/Lee-do-yeong%27s_manhwa_Imitating_Others.jpg` | Lee Do-yeong, 1909, early newspaper manhwa, Hangul | PD |
| A6 | KR | `https://upload.wikimedia.org/wikipedia/commons/b/b8/Manhwa-Yu.Gil-jun-Yahak-01.jpg` | 1908 Korean comic with Hangul dialogue | PD |

**Tier B: modern reference samples from FOSS repos. Local development only, not redistributable (artwork is copyrighted; repo license covers code).** Use for realistic OCR/typeset checks on contemporary art styles, with known good outputs.

| # | Language | Input URL | Expected output URL | Content |
|---|---|---|---|---|
| B1 | JP | `https://user-images.githubusercontent.com/31543482/232265329-6a560438-e887-4f7f-b6a1-a61b8648f781.png` | `https://user-images.githubusercontent.com/31543482/232265339-514c843a-0541-4a24-b3bc-1efa6915f757.png` | Modern JP manga page, in-place EN output reference (manga-image-translator) |
| B2 | JP | `https://user-images.githubusercontent.com/31543482/232264684-5a7bcf8e-707b-4925-86b0-4212382f1680.png` | (run pipeline) | Modern JP manga page |
| B3 | ZH | `https://i.imgur.com/zk7yiKe.jpg` | `https://i.imgur.com/4ycSi8j.jpg` | Chinese comic page + EN output reference (comic-translate) |
| B4 | KR | `https://i.imgur.com/KGwiHJh.jpg` | `https://i.imgur.com/B8RMbRQ.jpg` | Korean webtoon page + EN output reference (comic-translate) |

**Tier C: ground-truth annotated datasets (gated, academic).** For accuracy benchmarking, not shipped.

| Dataset | URL | Notes |
|---|---|---|
| Manga109-s | `https://huggingface.co/datasets/hal-utokyo/Manga109-s` | 87 volumes, box + transcribed text annotations. Gated, academic email required. Read via `manga109api`. |
| Manga109 (full) | `https://huggingface.co/datasets/hal-utokyo/Manga109` | Full 109 volumes. Gated. |
| COMICS (UMD) | `https://obj.umiacs.umd.edu/comics/index.html` | English public-domain Golden-Age comics, ~1.2M panels + OCR CSV. Ungated. Use for English detection/OCR plumbing only. |

### 15.4 Expected behavior assertions
- **Detection:** every Tier A image yields >= 1 region per visible text block. Save overlay PNGs to the golden folder.
- **OCR:** recognized text contains the expected script (JP returns kana/kanji, KR returns Hangul, ZH returns Han). For Tier C, compute character error rate against ground truth and track it.
- **Translation:** output language equals target; injected glossary names appear verbatim; offline mode runs with no key.
- **Inpaint:** within each text mask, mean pixel variance after inpaint approaches the surrounding bubble (no residual glyphs).
- **Typeset:** rendered text bounding box stays within the bubble polygon; no overflow.
- **Crawler:** MangaDex page URLs reconstruct correctly from a recorded `/at-home/server` response (unit), and a live public chapter downloads N pages where N matches the feed (integration).

---

## 16. Licensing and legal (enforce in code review)

**Ship only permissive weights and your own code.** Use GPL projects (manga-image-translator, BallonsTranslator, koharu) as reference, not as copied source.

Commercial-safe to ship (Apache-2.0 / MIT): `ogkalu/comic-text-and-bubble-detector`, `ogkalu/comic-text-segmenter-yolov8m`, `kha-white/manga-ocr-base`, PaddleOCR + `PaddleOCR-VL`, `dreMaz/AnimeMangaInpainting`, `mayocream/aot-inpainting`, `haoranxu/X-ALMA-13B-Group6`, `Qwen/Qwen3-14B`, `Qwen/Qwen3-VL-8B-Instruct`, `sugoitoolkit/Sugoi-14B-Ultra-GGUF`, `facebook/m2m100_1.2B`, IOPaint, Pillow, Comic Neue / Bangers / Noto / Source Han fonts.

Do NOT ship (non-commercial or restricted): `ragavsachdeva/magi` and `magiv2` (research only), NLLB family (CC-BY-NC), `OpenLLM-Korea/VARCO-VISION-2.0-1.7B-OCR` (CC-BY-NC), TowerInstruct (NC), Sugoi v4 fairseq weights (NC), FLUX.1 Fill weights (NC). These may be offered as optional user-supplied engines, downloaded by the user, never bundled.

**Crawler conduct:** default to MangaDex's official API and follow its ToS (credit MangaDex and scanlation groups, honor takedowns, no ads/paid access on their content, no mass-scraping, honest User-Agent, no `Via` header, proxy images rather than hotlink). Do not bundle scrapers for piracy sites; ship the adapter framework and let users add their own extensions, or point at a self-run Suwayomi-Server. Frame the product for content the user has a legal right to access. The depicted artwork is copyrighted even when the tool code is open source; this is a personal translation/reading aid, not a redistribution tool.

Add a `LICENSES-MANGA.md` listing every bundled model and font with its license, and a startup check that refuses to load an NC model unless the user explicitly enabled "research mode."

---

## 17. Risks and gotchas

- **Mask quality dominates inpaint quality.** Spend effort on the text segmenter and dilation, not on a fancier inpainter. A tight default mask with a few-pixel dilation beats a great inpainter on a sloppy mask.
- **Cloud context window trap.** Quality peaks at one page of full context and degrades if you feed a whole volume ("lost in the middle"). One page plus a short rolling summary per call.
- **Webtoon seams.** Never blind-cut every N pixels. Always overlap-tile and de-duplicate boxes, or you lose bubbles at the seam.
- **MangaDex base URL expiry.** The at-home `baseUrl` dies in ~15 minutes. Re-request on 403. Always POST the image report.
- **Vertical Japanese.** Pillow cannot do convincing tate-gaki. If JP vertical output matters, budget for the HarfBuzz/Pango renderer; do not fake it by rotating horizontal text.
- **Startup cost.** If any `torch`/`paddle` import leaks into the novel path, launch time regresses. Keep ML imports lazy and test for it in Phase 0.
- **Model version drift.** Pin cloud model snapshot IDs in config and verify them in each provider console at build time; the families in Section 6.1 move.
- **Korean OCR.** No permissive manga-ocr equivalent for Hangul. PaddleOCR `ko` plus VLM escalation is the commercial-safe route; do not reach for VARCO in a shippable build.

---

## Appendix A: Model registry (quick reference)

| Stage | Default | Fallback | Cloud / heavy |
|---|---|---|---|
| Detect | `ogkalu/comic-text-and-bubble-detector` (Apache-2.0) | `ogkalu/comic-text-segmenter-yolov8m`, `ogkalu/comic-speech-bubble-detector-yolov8m` | `ragavsachdeva/magiv2` (NC, optional) |
| Reading order | language heuristic | `manga109/panel-order-estimator` | Magiv2 |
| OCR JP | `kha-white/manga-ocr-base` (Apache-2.0) | EasyOCR `ja` | `PaddlePaddle/PaddleOCR-VL`, `Qwen/Qwen3-VL-8B-Instruct`, `rednote-hilab/dots.mocr` |
| OCR KO/ZH | PaddleOCR PP-OCRv5 (Apache-2.0) | EasyOCR | same VLMs |
| Translate | cloud vision-LLM (Claude/Gemini/GPT, configurable) | `haoranxu/X-ALMA-13B-Group6` (MIT), `sugoitoolkit/Sugoi-14B-Ultra-GGUF` (JP), `Qwen/Qwen3-14B` | `facebook/m2m100_1.2B`, Argos (lightest) |
| Inpaint | `dreMaz/AnimeMangaInpainting` (MIT) | `mayocream/aot-inpainting` (Apache-2.0) | `black-forest-labs/FLUX.1-Fill-dev` (NC, optional) |
| Typeset | Pillow + binary-fit + stroke | libraqm shaping | HarfBuzz/Pango/skia (vertical CJK) |
| Webtoon | blank-row split | overlap tiling (`det_rearrange_forward` pattern) | learned panel seg |
| Toolkit | IOPaint (Apache-2.0) for erase | | |

## Appendix B: Reference projects (study, mind the license)

| Project | License | Borrow |
|---|---|---|
| [comic-translate](https://github.com/ogkalu2/comic-translate) | Apache-2.0 | Most license-friendly. OCR routing (manga-ocr JP / Pororo KR / PP-OCRv5 else), RT-DETR detector, LLM-as-translator with full-page context. |
| [MangaTranslator](https://github.com/meangrinch/MangaTranslator) | Apache-2.0 | Vision-LLM-native shortcut (detect then VLM does OCR+translate in one call), FLUX inpainting, outside-bubble text pipeline. |
| [manga-image-translator](https://github.com/zyddnys/manga-image-translator) | GPL-3.0 | Modular stage architecture, webtoon `det_rearrange_forward`, offline translators, LaMa/AOT stack. Reference only. |
| [BallonsTranslator](https://github.com/dmMaze/BallonsTranslator) | GPL-3.0 | Best typesetting/rendering reference: source-style estimation, CJK line-breaking, vertical text, manual editor ergonomics. |
| [koharu](https://github.com/mayocream/koharu) | GPL-3.0 | Provider abstraction, headless API/MCP surface, correct vertical-CJK + RTL renderer, PSD export. |
| [lightnovel-crawler](https://github.com/dipu-bd/lightnovel-crawler) | GPL-3.0 | The source-registry + template pattern your novel crawler already follows; manga is first-class there. |
| [comic-text-detector](https://github.com/dmMaze/comic-text-detector) | GPL-3.0 | Origin of the `ctd` detector + U-Net text masks. Reference for mask generation. |

## Appendix C: Cloud translation prompt template

```
SYSTEM:
You are a professional manga/manhwa/manhua localizer translating {source_lang} to {target_lang}.
Preserve tone, register, honorifics, and each character's distinct voice. Keep onomatopoeia
natural for {target_lang}. Use the glossary exactly. Return only JSON.

GLOSSARY (use these renderings verbatim):
{glossary_block}     # e.g. "佐藤 -> Sato (male, casual)", "선배 -> senpai"

RECENT CONTEXT (previous page, summary):
{rolling_summary}

USER (with the page image attached):
Here is one manga page and the detected text regions in reading order:
{regions_json}        # [{"id":0,"text":"..."}, ...]
Translate each region using the whole-page image for context (who is speaking, panel, gender).
Return: {"translations":[{"id":0,"text":"..."}, ...]} with one entry per region id, same order.
```

Apply the same glossary to the offline path via `GlossaryManager.apply_glossary()` as pre- and post-translation string replacement.

## Appendix D: Key papers

| Paper | Link |
|---|---|
| Context-Informed MT of Manga using Multimodal LLMs (COLING 2025) | https://arxiv.org/abs/2411.02589 |
| Towards Fully Automated Manga Translation (AAAI 2021) | https://hf.co/papers/2012.14271 |
| Manga109-v2026: Revisiting Annotations | https://hf.co/papers/2605.21182 |
| The Manga Whisperer / Magi (CVPR 2024) | https://hf.co/papers/2401.10224 |
| Magiv2: Tails Tell Tales (ACCV 2024) | https://hf.co/papers/2408.00298 |
| PATIMT-Bench: Position-Aware Text Image MT (2025) | https://hf.co/papers/2509.12278 |
| Evaluating MLLMs on Vertically Written Japanese (2025) | https://hf.co/papers/2511.15059 |

---

*End of spec. Build in phase order, keep the gates honest, and ship permissive. The first real demo is Phase 5 (one raw JP page in, one translated typeset page out).*


