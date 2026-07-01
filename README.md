# SageMTL

SageMTL is a desktop-first workflow for crawling web novels, translating them locally, and exporting cleaned output.

## Current capabilities

- Offline translation with Argos Translate language packs.
- Optional translation backend selection (`argos`, optional `googletrans`, `echo`) for desktop jobs.
- Translation memory cache for repeated chunk reuse during desktop translation jobs.
- Adaptive chunking for large chapters with language-aware punctuation handling.
- Novel search and crawl execution through `LightNovelCrawlerWrapper`.
- Search results are grouped by novel first, then per-site source selection with chapter-count preview.
- Source selection auto-prefetches chapter counts for top rows in the background.
- Site-specific crawl profiles (delay, user-agent, retries, robots policy, worker count).
- URL-based chapter discovery and selective download (all, first N, custom range) with generic fallback and bounded chapter download workers.
- Resume support for partially downloaded novels by source URL.
- Batch URL crawl queue from dialog input or multiline fetch input.
- Optional direct EPUB export from crawler output during crawl.
- Glossary workflows (global and per-novel) with CSV import/export.
- Glossary enforcement now applies global + novel terms in processing flows, including CJK-safe matching for contiguous source text.
- EPUB import, TXT/EPUB export, and persistent local novel library.
- Manual novel renames persist across resume crawls for the same source URL.
- UI language selection (English/Spanish) and actionable recovery hints for common errors.
- Active search progress dialog can be hidden/reopened while background search continues.
- Detailed in-app workflow/options guide available from Help menu (`F1`).
- Shared desktop/CLI settings model via `~/.sagemtl/config.toml`.
- Batch job processing with progress and structured logs.

## Quick start (desktop app)

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements-desktop.txt
```

3. Install at least one Argos language model (example: Chinese to English).

```powershell
python -c "import argostranslate.package as p; p.update_package_index(); pkg=[x for x in p.get_available_packages() if x.from_code=='zh' and x.to_code=='en'][0]; p.install_from_path(pkg.download())"
```

4. Optional: install `googletrans` backend support.

```powershell
pip install googletrans==4.0.0rc1
```

5. Launch the desktop app.

```powershell
python -m sagemtl_desktop.main
```

## Manga module (optional)

SageMTL also has a Manga mode that translates raw manga/manhwa/manhua in place:
detect text -> OCR (Japanese via manga-ocr, Korean/Chinese via PaddleOCR) ->
translate (offline m2m100 by default, or a cloud vision-LLM) -> erase + inpaint ->
re-letter, plus a MangaDex crawler and CBZ/PDF export. Switch between Novels and
Manga from the **Manga** menu.

The manga dependencies and model weights are **not** installed with the desktop
app -- the novel path works without them. Install them on demand:

```powershell
python scripts/setup_manga.py            # installs requirements-manga.txt + warms the model cache
# or: pip install -r requirements-manga.txt
```

- Models download on first use into `~/.sagemtl/models/` (nothing is bundled).
- CPU works out of the box (ONNX detector, `PaddleOCR(enable_mkldnn=False)`); for
  CUDA install the matching `torch` / `onnxruntime-gpu` / `paddlepaddle-gpu` wheels.
- Cloud translation reads the API key from an environment variable only (e.g.
  `ANTHROPIC_API_KEY`); keys are never stored in `config.toml`.
- Only permissive (Apache-2.0 / MIT / OFL) weights and fonts ship; non-commercial
  models are never bundled and require an explicit research-mode opt-in. See
  `LICENSES-MANGA.md`. Default and promoted crawler source is the MangaDex official
  API; use the tool for content you have a right to access.

## CLI entry points

- Show help: `python -m sagemtl --help`
- Clean text: `python -m sagemtl clean --help`
- Crawl HTML extraction helpers: `python -m sagemtl crawl --help`
- Release checklist automation: `python -m sagemtl release-check`
- TUI (early stage): `python -m sagemtl tui`

## Project structure

- `sagemtl_desktop/` desktop UI and desktop core services (manga module under `core/manga/` and `ui/manga/`)
- `sagemtl/` shared CLI, cleaning, crawl helpers, queue, config
- `sagemtl_crawler/` adapter-based crawler engine (currently separate from desktop runtime path)
- `sagemtl_manga_crawler/` page-image crawler (MangaDex official-API source)
- `tests/` automated tests

## Documentation

- `DEV.md` developer setup, architecture, testing, optimization audit
- `ROADMAP.md` single execution plan with completed and pending work
- `AGENTS.md` operating instructions for AI coding agents
- `LICENSES-MANGA.md` manga model/font licenses and the non-commercial-model policy

## License

MIT. See `LICENSE`.
