# Manga module licenses

SageMTL's manga module ships **only permissive (Apache-2.0 / MIT / OFL) assets and
its own code**. Model weights are not bundled in the installer; they are downloaded
on first use into `~/.sagemtl/models/` via `huggingface_hub`. Every model the app
will auto-download is permissively licensed and listed below.

A startup guard (`core/manga/model_registry.py`) refuses to load any
non-commercial model unless the user explicitly enables **research mode**
(`set_research_mode(True)`); the non-commercial models below are never bundled and
are only usable as user-supplied engines under that opt-in.

## Bundled fonts (shipped in `core/manga/fonts/`)

| Font | License | Use |
|---|---|---|
| Comic Neue (`ComicNeue-Bold.ttf`, `ComicNeue-Regular.ttf`) | SIL OFL 1.1 (`OFL.txt`) | Default typeset font |

Users may drop their own fonts (e.g. Wild Words, Anime Ace) into that folder;
those proprietary/non-commercial fonts are never bundled.

## Models downloaded on demand (permissive)

| Stage | Model | License |
|---|---|---|
| Detection | `ogkalu/comic-text-and-bubble-detector` | Apache-2.0 |
| Detection (fallbacks) | `ogkalu/comic-text-segmenter-yolov8m`, `ogkalu/comic-speech-bubble-detector-yolov8m` | Apache-2.0 |
| Panel detect | `mosesb/best-comic-panel-detection` | Apache-2.0 |
| OCR (JP) | `kha-white/manga-ocr-base` | Apache-2.0 |
| OCR (KO/ZH) | PaddleOCR PP-OCRv5 (`PaddlePaddle/...`) | Apache-2.0 |
| OCR VLM | `PaddlePaddle/PaddleOCR-VL`, `Qwen/Qwen3-VL-8B-Instruct` | Apache-2.0 |
| OCR VLM | `rednote-hilab/dots.mocr` | MIT |
| Inpaint | `dreMaz/AnimeMangaInpainting` | MIT |
| Inpaint | `mayocream/aot-inpainting` | Apache-2.0 |
| MT (offline) | `facebook/m2m100_1.2B` | MIT |
| MT (offline) | `haoranxu/X-ALMA-13B-Group6` | MIT |
| MT (offline) | `Qwen/Qwen3-14B` | Apache-2.0 |
| MT (offline) | `sugoitoolkit/Sugoi-14B-Ultra-GGUF` | Apache-2.0 |

Note: the default inpaint path is classical (OpenCV), so no inpaint weights are
required; `dreMaz/AnimeMangaInpainting` is an optional neural upgrade via IOPaint
(Apache-2.0). The YOLO segmenter/bubble weights are Apache-2.0 but their usual
runtime (`ultralytics`) is AGPL-3.0, so they are not used at runtime by default.

## Never bundled / never auto-loaded (non-commercial)

These are blocked by the research-mode guard and must be user-supplied:

- `ragavsachdeva/magi`, `ragavsachdeva/magiv2` (research only)
- NLLB family, e.g. `facebook/nllb-200-*` (CC-BY-NC)
- `OpenLLM-Korea/VARCO-VISION-2.0-1.7B-OCR` (CC-BY-NC)
- `Unbabel/TowerInstruct-*` (non-commercial)
- Sugoi v4 fairseq weights (non-commercial)
- `black-forest-labs/FLUX.1-Fill-dev` (FLUX weights, non-commercial)

## Cloud providers

Anthropic / OpenAI / Google SDKs are API clients (not bundled weights); usage is
governed by each provider's terms. API keys are read from environment variables
only and are never written to `config.toml`.

## Crawler conduct

The default and promoted source is the MangaDex official API. SageMTL credits
MangaDex and scanlation groups, honors takedowns, sends an honest (non-spoofed)
User-Agent with no `Via` header, reports image fetches to the volunteer CDN, and
does not bundle scrapers for piracy sites. Frame usage for content you have a legal
right to access.
