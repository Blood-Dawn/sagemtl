# SageMTL - Machine Translation Toolchain

**SageMTL** (Sage Machine Translation Library) is a comprehensive machine translation and language processing platform that provides a complete workflow for cleaning, crawling, and translating multilingual text content.

## Features

- **Text Cleaning**: Normalize text with configurable options (smart quotes, em-dashes, Unicode normalization, etc.)
- **HTML Crawling**: Extract structured content from HTML with boilerplate removal
- **Translation Queue**: Asynchronous translation job processing with pluggable providers
- **Dataset Management**: Register and manage local datasets in JSONL/CSV formats
- **Multiple Interfaces**:
  - **CLI**: Command-line interface for automation
  - **TUI**: Interactive terminal UI with Textual
  - **REST API**: FastAPI HTTP server with OpenAPI docs
  - **Web UI**: React dashboard (in `ui/` directory)
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

## Development

### Install for Development

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .[dev]
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

## API Endpoints

When running `sagemtl serve`, the following endpoints are available:

- `POST /clean` - Clean text
- `POST /crawl` - Extract from HTML
- `POST /translate` - Queue translation job
- `GET /jobs` - List all jobs
- `GET /jobs/{job_id}` - Get job status
- `DELETE /jobs/{job_id}` - Cancel job
- `GET /datasets` - List datasets

Visit `http://localhost:8000/docs` for interactive API documentation.

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please check the existing issues or create a new one to discuss your ideas.
