# sagemtl

SageMTL brings together cleaning, crawling and translation tooling behind a single
Python CLI and optional HTTP API.

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
