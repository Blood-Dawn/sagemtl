# Getting Started with SageMTL

This guide will walk you through installing and using SageMTL for the first time.

## Installation

### Requirements

- Python 3.11 or higher
- pip package manager
- (Optional) Node.js 18+ for the web UI

### Install from Source

1. Clone the repository:

```bash
git clone https://github.com/Blood-Dawn/sagemtl.git
cd sagemtl
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the package:

```bash
# Basic installation
pip install -e .

# With all optional dependencies
pip install -e .[dev,serve,tui,docs]
```

### Verify Installation

Check that the CLI is available:

```bash
sagemtl --help
```

You should see the command list and options.

## First Steps

### 1. Initialize Configuration

On first run, SageMTL will create a configuration directory at `~/.sagemtl/`:

```bash
sagemtl settings show
```

This displays the current configuration and creates the directory structure:

```
~/.sagemtl/
├── config.toml    # Configuration file
├── jobs.json      # Translation job storage
└── data/          # Dataset directory
```

### 2. Clean Text

Try cleaning some text:

```bash
echo "Hello    World" | sagemtl clean
```

Or clean a file:

```bash
sagemtl clean --in input.txt --out cleaned.txt
```

Enable/disable specific normalizations:

```bash
sagemtl clean --in input.txt --no-smart-quotes --no-em-dash
```

### 3. Crawl HTML

Extract content from an HTML file:

```bash
sagemtl crawl --file page.html
```

Or fetch from a URL:

```bash
sagemtl crawl --url https://example.com --out extracted.json
```

Use CSS selectors to filter content:

```bash
sagemtl crawl --file page.html --allow "article p" --block ".sidebar"
```

### 4. Translation Jobs

Queue a translation:

```bash
sagemtl translate "Hello world" --src-lang en --tgt-lang fr --wait
```

The `--wait` flag blocks until the job completes.

List all jobs:

```bash
sagemtl jobs list
```

View job details:

```bash
sagemtl jobs tail <job-id>
```

### 5. Dataset Management

Register a dataset:

```bash
sagemtl datasets add my-data data.jsonl
```

List datasets:

```bash
sagemtl datasets list
```

Export in different formats:

```bash
sagemtl datasets export my-data --format csv --out data.csv
```

### 6. Batch Processing

Clean multiple files at once:

```bash
sagemtl clean batch /path/to/files --out cleaned.jsonl
```

The output is a JSONL file with cleaned text and metadata for each input file.

## Using the Terminal UI

Launch the interactive TUI:

```bash
sagemtl tui
```

Navigate using:
- Arrow keys or mouse to select tabs
- `Ctrl+N` - Normalize text in Clean tab
- `Ctrl+E` - Extract text in Crawl tab
- `Ctrl+Q` - Quit
- `F1` - Help

## Using the Web UI

1. Start the API server:

```bash
sagemtl serve --host 127.0.0.1 --port 8000
```

2. In a new terminal, start the UI development server:

```bash
cd ui
npm install
npm run dev
```

3. Open your browser to `http://localhost:5173`

The web UI provides a visual interface for all SageMTL features:

- **Clean** - Interactive text cleaning with diff preview
- **Crawl** - HTML extraction with selector builder
- **Translate** - Job queue management
- **Datasets** - Dataset browser with table view
- **Jobs** - Job history and monitoring
- **Settings** - Configuration editor

## Configuration

### Config File

Create or edit `~/.sagemtl/config.toml`:

```toml
newline_mode = "lf"
thread_count = 8
clean_input_path = "-"
```

Or use the CLI:

```bash
sagemtl settings set newline_mode '"crlf"'
sagemtl settings set thread_count 4
```

### Environment Variables

Override any setting with environment variables:

```bash
export SAGEMTL_THREAD_COUNT=8
export SAGEMTL_NEWLINE_MODE=lf
```

### Layered Configuration

Settings are resolved in this order (later takes precedence):

1. Built-in defaults
2. `~/.sagemtl/config.toml`
3. Environment variables (`SAGEMTL_*`)
4. CLI arguments

## Next Steps

- Read the [CLI Reference](cli.md) for detailed command documentation
- Explore the [REST API](api.md) for programmatic access
- Check out [Batch Processing](batch.md) for high-throughput workflows
- Learn about [Configuration](settings.md) options

## Troubleshooting

### Command not found

Make sure your virtual environment is activated and the package is installed:

```bash
source .venv/bin/activate
pip install -e .
```

### TUI not working

Install the TUI dependencies:

```bash
pip install sagemtl[tui]
```

### API server fails to start

Install the serve dependencies:

```bash
pip install sagemtl[serve]
```

### Permission errors

Make sure `~/.sagemtl` directory is writable:

```bash
mkdir -p ~/.sagemtl
chmod 755 ~/.sagemtl
```
