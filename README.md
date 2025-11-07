# SageMTL - Machine Translation Toolchain

**SageMTL** (Sage Machine Translation Library) is a comprehensive machine translation and language processing platform that provides a complete **Import → Process → Export** workflow for cleaning, crawling, and translating multilingual text content.

## 🚀 What's New in v2

- **Novel Crawler** with automatic chapter pattern detection and LNCrawl integration
- **Modular API** under `/api/*` with organized routers
- **Dataset Import** with drag-drop file upload (`.txt`, `.md`, `.html`, `.jsonl`, `.epub`)
- **Novel Management** with chapter tracking and metadata
- **Compose Pipeline** - unified Clean + Translate + Glossary workflow
- **Real-time Jobs** with WebSocket progress streaming and detailed metrics
- **Enhanced Glossary** with case-sensitivity and word boundaries
- **Settings Management** - UI and API for config.toml persistence

📖 **[See IMPLEMENTATION.md for complete feature list](./IMPLEMENTATION.md)**
📘 **[Read HOWTORUN.md for detailed usage guide](./HOWTORUN.md)**

## Features

- **Text Cleaning**: Normalize text with configurable options (smart quotes, em-dashes, Unicode normalization, etc.)
- **HTML Crawling**: Extract structured content from HTML with boilerplate removal + chapter extraction
- **Translation Queue**: Asynchronous translation job processing with pluggable providers
- **Dataset Management**: Import, register, and manage datasets (text, novels, translations)
- **Glossary System**: CSV/JSON glossaries with case-sensitive matching and word boundaries
- **Multiple Interfaces**:
  - **CLI**: Command-line interface for automation
  - **TUI**: Interactive terminal UI with Textual
  - **REST API v2**: FastAPI with modular routers, WebSockets, and file uploads
  - **Web UI**: React 19 dashboard (in `ui/` directory)
- **Batch Processing**: High-throughput directory processing with resume capability
- **Configuration**: Layered config (defaults → TOML → ENV vars → CLI args)

## Quickstart

```bash
# create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# install the project with development helpers
pip install -e .[dev]

# explore the command line help
sagemtl --help
```

## Command overview

Each pipeline has a dedicated sub-command. Pass `--help` to any command to see the
available options.

### Cleaning

Clean single files or entire collections. The normaliser exposes toggles for smart
quotes, dash/minus handling, blank-line collapsing and the trailing newline policy.

```bash
# clean a single file to stdout
sagemtl clean --in raw.txt

# batch clean a directory, writing JSONL entries with text + metadata
sagemtl clean batch data/raw --out cleaned.jsonl
```

### Crawling

Extract structured blocks from HTML using the built-in heuristics (boilerplate
removal, selector allow/block lists and CRLF normalisation):

```bash
sagemtl crawl --file page.html --allow "article > p" --block ".sidebar"
```

**Novel Crawling** with automatic chapter pattern detection:

```bash
# Install lightnovel-crawler (optional)
pip install 'sagemtl[lncrawl]'

# Crawl a novel - auto-detects chapter patterns
sagemtl crawl novel https://example.com/novel/chapter-1 --start 1 --end 50 --name "my-novel"

# Supported patterns: /chapter-1, /ch1/, /1/, /1.html, etc.
# Falls back to built-in crawler if URL not supported by LNCrawl
```

### Translation queue

Translations are queued and processed by an in-process worker. Glossaries can be
provided as CSV term→replacement maps.

```bash
sagemtl translate "Hello world" --src-lang en --tgt-lang fr --wait
```

### Dataset registry

Datasets are registered under `~/.sagemtl/data` (override with
`SAGEMTL_DATA_DIR`).

```bash
# list known datasets
sagemtl datasets list

# add a JSONL dataset and export it as CSV
sagemtl datasets add my-set samples.jsonl
sagemtl datasets export my-set --format csv --out export.csv
```

### Job management

Translation jobs are persisted to `~/.sagemtl/jobs.json`. Inspect them via the
`jobs` sub-commands.

```bash
sagemtl jobs list
sagemtl jobs tail <job-id>
sagemtl jobs purge
```

### Settings

Configuration lives in `~/.sagemtl/config.toml`. The CLI can show or edit values:

```bash
sagemtl settings show
sagemtl settings set newline_mode "\"crlf\""
```

### HTTP bridge

Start a FastAPI server that mirrors the CLI functionality:

```bash
# requires uvicorn to be installed in the environment
sagemtl serve --host 127.0.0.1 --port 8000

# or run via uvicorn directly
uvicorn sagemtl.serve.api:app
```

The API enables cross-origin requests from `http://localhost:5173` for UI
development.

### Terminal UI

Launch the interactive Textual-based TUI for experimentation:

```bash
sagemtl tui
```

The TUI provides tabs for Clean, Crawl, Batch, Translate, and Settings with live
preview and status logging.

### Web UI

The React dashboard is located in the `ui/` directory:

```bash
cd ui
npm install
npm run dev
```

Visit `http://localhost:5173` to access the web interface. The UI provides pages for:

- **/clean** - Text cleaning with before/after diff viewer
- **/crawl** - HTML extraction with CSS selector configuration
- **/translate** - Translation job management with progress tracking
- **/datasets** - Dataset registry with table view
- **/jobs** - Job history and monitoring
- **/settings** - Configuration editor

## Configuration

### Config File

SageMTL stores configuration in `~/.sagemtl/config.toml`. Create it manually or use:

```bash
sagemtl settings set newline_mode '"lf"'
sagemtl settings set thread_count 8
```

Example config:

```toml
newline_mode = "lf"
thread_count = 8
clean_input_path = "-"
crawl_outdir = "out"
```

### Environment Variables

Override settings with `SAGEMTL_` prefixed environment variables:

```bash
export SAGEMTL_THREAD_COUNT=4
export SAGEMTL_NEWLINE_MODE=crlf
export SAGEMTL_CLEAN__INPUT_PATH=/tmp/input  # __ for nested keys
```

### Directory Structure

On first run, SageMTL creates:

```
~/.sagemtl/
├── config.toml          # Configuration file
├── jobs.json            # Translation job storage
└── data/                # Registered datasets
```

Override with:
- `SAGEMTL_CONFIG` - Config file path
- `SAGEMTL_JOBS_PATH` - Jobs storage path
- `SAGEMTL_DATA_DIR` - Dataset directory

## Optional Features

### Novel Crawler with LNCrawl

For enhanced novel crawling with support for 600+ novel sites:

```bash
pip install 'sagemtl[lncrawl]'
```

This installs [lightnovel-crawler](https://github.com/dipu-bd/lightnovel-crawler) (GPLv3) which provides:
- Support for RoyalRoad, Webnovel, Wuxiaworld, and 600+ other sites
- Automatic chapter detection and metadata extraction
- EPUB generation
- Cover image download

SageMTL will automatically use LNCrawl when available, or fall back to the built-in pattern-based crawler.

## Development

### Install for Development

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .[dev]

# Optional: Install LNCrawl for novel crawling
pip install -e .[lncrawl]
```

### Run Tests

```bash
pytest
pytest --cov=sagemtl --cov-report=html
```

### Code Quality

```bash
ruff check sagemtl/
ruff format sagemtl/
pre-commit run --all-files
```

### VS Code Configuration

The project includes a `.vscode/settings.json` file with recommended settings:

- **Terminal Profile**: Default terminal is set to PowerShell on Windows, bash on Linux, zsh on macOS
- **Python Formatting**: Auto-format on save with Black (120 char line length)
- **Linting**: Ruff linting enabled
- **Import Organization**: Auto-organize imports on save

**To change the default terminal profile**:
1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
2. Search for **"Terminal: Select Default Profile"**
3. Choose your preferred shell (PowerShell, Command Prompt, Git Bash, WSL, etc.)

The setting is stored in `.vscode/settings.json` under `terminal.integrated.defaultProfile.windows`.

### Build Documentation

```bash
mkdocs serve
# Visit http://localhost:8000
```

## Project Structure

```
sagemtl/
├── sagemtl/              # Python package
│   ├── cli.py           # Typer CLI
│   ├── config.py        # Configuration management
│   ├── clean/           # Text cleaning module
│   ├── crawl/           # HTML crawling module
│   ├── translate/       # Translation queue & providers
│   ├── datasets/        # Dataset registry
│   ├── jobs/            # Job storage
│   ├── batch/           # Batch processing
│   ├── tui/             # Textual TUI
│   └── serve/           # FastAPI server
├── ui/                   # React frontend
│   ├── src/
│   │   ├── pages/       # Page components
│   │   ├── components/  # Reusable components
│   │   └── api/         # API client
├── tests/               # Test suite
├── docs/                # MkDocs documentation
└── pyproject.toml       # Package metadata
```

## API v2 Endpoints

Start the API server with:
```bash
sagemtl serve --v2 --port 8000
```

### Compose (Unified Pipeline)
- `POST /api/compose/clean` - Clean text with glossary support
- `POST /api/compose/translate` - Queue translation with pre/post glossary
- `POST /api/compose/pipeline` - Full workflow: Clean → Translate → Save

### Datasets (Import & Management)
- `GET /api/datasets` - List all datasets
- `POST /api/datasets/import` - Import files (multipart upload)
- `GET /api/datasets/novels` - List novel-type datasets
- `GET /api/datasets/{id}` - Get dataset details
- `GET /api/datasets/{id}/files` - List dataset files
- `DELETE /api/datasets/{id}` - Delete dataset

### Crawl (Chapter Extraction)
- `POST /api/crawl/novel` - Crawl novel with pattern detection (uses LNCrawl if available)
- `POST /api/crawl/run` - Crawl chapters (async job)
- `POST /api/crawl/extract` - Extract HTML (sync)

### Jobs (Real-time Tracking)
- `GET /api/jobs` - List all jobs with metadata (runtime, bytes, provider)
- `GET /api/jobs/{id}` - Get job status with logs
- `DELETE /api/jobs/{id}` - Cancel job
- `POST /api/jobs/{id}/retry` - Retry failed job
- `WebSocket /api/jobs/ws/{id}` - Real-time progress stream

### Settings (Configuration Management)
- `GET /api/settings` - Get current settings
- `PUT /api/settings` - Update settings (persists to config.toml)
- `POST /api/settings/reset` - Reset to defaults

### Legacy Endpoints (v1 - backward compatible)
- `POST /clean` - Clean text
- `POST /crawl` - Extract from HTML
- `POST /translate` - Queue translation job
- `GET /jobs` - List jobs
- `GET /datasets` - List datasets

Visit `http://localhost:8000/docs` for interactive API documentation.

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please check the existing issues or create a new one to discuss your ideas.
