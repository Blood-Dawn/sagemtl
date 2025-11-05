# How to Run SageMTL - Complete Guide

This guide provides step-by-step instructions for running all components of SageMTL, including the new v2 API with enhanced features.

## Quick Start

```bash
# 1. Install SageMTL
cd sagemtl
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]

# 2. Start the API server
sagemtl serve --v2 --port 8000

# 3. In a new terminal, start the UI
cd ui
npm install
npm run dev

# 4. Open browser
# API Docs: http://localhost:8000/docs
# Web UI: http://localhost:5173
```

## Detailed Installation

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for web UI)
- **pip** and **npm**

### Backend Installation

```bash
# Clone the repository
git clone https://github.com/Blood-Dawn/sagemtl.git
cd sagemtl

# Create virtual environment
python -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Install with all features
pip install -e .[dev,serve,tui,docs]

# Verify installation
sagemtl --help
```

### Frontend Installation

```bash
cd ui
npm install
npm run build  # Optional: build for production
```

## Running the Application

### 1. Command-Line Interface (CLI)

The CLI provides direct access to all SageMTL features:

```bash
# Text cleaning
echo "Hello    World" | sagemtl clean
sagemtl clean --in input.txt --out cleaned.txt

# HTML crawling
sagemtl crawl --url https://example.com --out extracted.json
sagemtl crawl --file page.html --allow "article" --block ".sidebar"

# Translation
sagemtl translate "Hello world" --tgt-lang fr --wait
sagemtl translate "Text" --src-lang en --tgt-lang zh --provider echo

# Dataset management
sagemtl datasets list
sagemtl datasets add my-data file.jsonl
sagemtl datasets export my-data --format csv --out data.csv

# Job management
sagemtl jobs list
sagemtl jobs tail <job-id>
sagemtl jobs purge

# Settings
sagemtl settings show
sagemtl settings set thread_count 8
```

### 2. Terminal UI (TUI)

Interactive terminal interface with tabs:

```bash
sagemtl tui
```

**Navigation**:
- Arrow keys or mouse to select tabs
- `Ctrl+N` - Normalize text in Clean tab
- `Ctrl+E` - Extract text in Crawl tab
- `Ctrl+Q` - Quit
- `F1` - Help

### 3. REST API Server

#### Start the API (v2 - Recommended)

```bash
# Start with default settings
sagemtl serve --v2 --port 8000

# Custom host and port
sagemtl serve --v2 --host 0.0.0.0 --port 9000

# Legacy v1 API
sagemtl serve --no-v2 --port 8000
```

#### Using uvicorn directly

```bash
# V2 API
uvicorn sagemtl.serve.api_v2:app --host 127.0.0.1 --port 8000 --reload

# V1 API (legacy)
uvicorn sagemtl.serve.api:app --host 127.0.0.1 --port 8000
```

#### API Documentation

Once the server is running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 4. Web UI (React Dashboard)

```bash
cd ui

# Development mode (hot reload)
npm run dev

# Production build
npm run build
npm run preview

# Linting
npm run lint
```

Access the UI at: **http://localhost:5173**

## API v2 Features & Usage

### Import Datasets

**Upload files via HTTP**:
```bash
curl -X POST "http://localhost:8000/api/datasets/import" \
  -F "files=@chapter1.txt" \
  -F "files=@chapter2.txt" \
  -F "dataset_name=my-novel" \
  -F "dataset_type=novel"
```

**Supported formats**: `.txt`, `.md`, `.html`, `.jsonl`, `.epub`

### Compose Pipeline

**Clean text**:
```bash
curl -X POST "http://localhost:8000/api/compose/clean" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello    World",
    "options": {
      "smart_quotes": true,
      "collapse_blank_lines": true,
      "apply_glossary": false
    }
  }'
```

**Translate text**:
```bash
curl -X POST "http://localhost:8000/api/compose/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "src_lang": "en",
    "tgt_lang": "zh",
    "provider": "echo",
    "glossary_path": "~/.sagemtl/glossaries/names.csv",
    "save_to_dataset": true
  }'
```

**Full pipeline**:
```bash
curl -X POST "http://localhost:8000/api/compose/pipeline" \
  -H "Content-Type: application/json" \
  -d '{
    "source_text": "Hello world",
    "clean_options": {
      "smart_quotes": true,
      "em_dash": true
    },
    "src_lang": "en",
    "tgt_lang": "zh",
    "glossary_path": "~/.sagemtl/glossaries/terms.csv",
    "save_to_dataset": true
  }'
```

### Crawl Chapters

**Crawl a novel**:
```bash
curl -X POST "http://localhost:8000/api/crawl/run" \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com/novel/chapter-1",
    "depth": 10,
    "max_chapters": 50,
    "novel_title": "My Novel",
    "allow_selectors": ["article", ".chapter-content"],
    "block_selectors": [".sidebar", ".ads"]
  }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Crawl job queued. Track at /api/jobs/550e8400..."
}
```

### Track Jobs

**List all jobs**:
```bash
curl "http://localhost:8000/api/jobs"
```

**Get job status**:
```bash
curl "http://localhost:8000/api/jobs/{job-id}"
```

**WebSocket (real-time)**:
```javascript
const ws = new WebSocket("ws://localhost:8000/api/jobs/ws/{job-id}");
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Status: ${data.status}, Progress: ${data.progress}`);

  if (data.type === "complete") {
    console.log("Job finished:", data.result);
  }
};
```

**Cancel a job**:
```bash
curl -X DELETE "http://localhost:8000/api/jobs/{job-id}"
```

## Configuration

### Config File

SageMTL stores configuration in `~/.sagemtl/config.toml`:

```toml
newline_mode = "lf"
thread_count = 8
clean_input_path = "-"
clean_output_path = null
crawl_glob = "*.html"
crawl_outdir = "out"
crawl_jsonl = false
```

**Edit configuration**:
```bash
# Show current config
sagemtl settings show

# Update a value
sagemtl settings set newline_mode '"crlf"'
sagemtl settings set thread_count 16
```

### Environment Variables

Override any setting with `SAGEMTL_*` prefix:

```bash
# Basic settings
export SAGEMTL_THREAD_COUNT=8
export SAGEMTL_NEWLINE_MODE=lf

# Nested settings (use __)
export SAGEMTL_CLEAN__INPUT_PATH=/tmp/input
export SAGEMTL_CRAWL__OUTDIR=./output

# Paths
export SAGEMTL_CONFIG=/custom/path/config.toml
export SAGEMTL_DATA_DIR=/custom/data
export SAGEMTL_JOBS_PATH=/custom/jobs.json
```

### Directory Structure

On first run, SageMTL creates:

```
~/.sagemtl/
├── config.toml          # Configuration file
├── jobs.json            # Job persistence
└── data/                # Datasets
    ├── dataset-abc123/
    │   ├── meta.json    # Dataset metadata
    │   └── files/       # Dataset files
    │       ├── ch0001.txt
    │       ├── ch0002.txt
    │       └── ...
    └── my-novel/
        ├── meta.json
        └── files/
            └── ...
```

## Glossary Management

### Creating a Glossary

**CSV Format**:
```csv
Source,Target,Case Sensitive,Word Boundary,Notes
龙傲天,Long Aotian,true,true,Main character
修真,Cultivation,false,false,Generic term
江湖,Jianghu,true,false,Martial world
```

**JSON Format**:
```json
[
  {
    "source": "龙傲天",
    "target": "Long Aotian",
    "case_sensitive": true,
    "word_boundary": true,
    "notes": "Main character"
  },
  {
    "source": "修真",
    "target": "Cultivation",
    "case_sensitive": false,
    "word_boundary": false,
    "notes": "Generic term"
  }
]
```

Save glossaries to `~/.sagemtl/glossaries/` for easy access.

### Using Glossaries

**In CLI**:
```bash
sagemtl translate "Text with 龙傲天" \
  --src-lang zh --tgt-lang en \
  --glossary ~/.sagemtl/glossaries/names.csv
```

**In API**:
```bash
curl -X POST "http://localhost:8000/api/compose/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Text with 龙傲天",
    "glossary_path": "~/.sagemtl/glossaries/names.csv",
    "apply_glossary_post": true
  }'
```

## Development

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=sagemtl --cov-report=html

# Specific test
pytest tests/test_compose.py

# Watch mode
pytest-watch
```

### Code Quality

```bash
# Format code
ruff format sagemtl/

# Lint code
ruff check sagemtl/

# Run pre-commit hooks
pre-commit run --all-files
```

### Build Documentation

```bash
# Serve docs locally
mkdocs serve

# Visit http://localhost:8000

# Build static docs
mkdocs build
```

## Troubleshooting

### API Server Won't Start

```bash
# Check if port is in use
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Try different port
sagemtl serve --v2 --port 9000

# Check dependencies
pip list | grep fastapi
pip install fastapi uvicorn python-multipart websockets
```

### WebSocket Connection Failed

- Ensure API server is running with `--v2` flag
- Check CORS settings in `api_v2.py`
- Verify WebSocket support: `pip list | grep websockets`

### File Upload Fails

- Install multipart support: `pip install python-multipart`
- Check file size limits
- Verify directory permissions for `~/.sagemtl/data`

### TUI Crashes

```bash
# Reinstall Textual
pip install --upgrade textual

# Check terminal compatibility
echo $TERM  # Should be xterm-256color or similar
```

### UI Build Fails

```bash
cd ui

# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite

# Try building again
npm run build
```

## Production Deployment

### Backend

```bash
# Install production dependencies only
pip install -e .

# Run with Gunicorn (Linux)
gunicorn sagemtl.serve.api_v2:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# Run with uvicorn (production)
uvicorn sagemtl.serve.api_v2:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

### Frontend

```bash
cd ui

# Build for production
npm run build

# Serve with static server
npm install -g serve
serve -s dist -l 5173

# Or use nginx/Apache to serve dist/
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

EXPOSE 8000
CMD ["uvicorn", "sagemtl.serve.api_v2:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Performance Tips

1. **Increase thread count** for faster processing:
   ```bash
   export SAGEMTL_THREAD_COUNT=16
   ```

2. **Use v2 API** for better organization and WebSocket support

3. **Enable HTTP/2** in httpx for faster crawling

4. **Batch processing** for large datasets:
   ```bash
   sagemtl clean batch /large/directory --out processed.jsonl
   ```

5. **Purge old jobs** regularly:
   ```bash
   sagemtl jobs purge
   ```

## Support

- **Documentation**: Run `mkdocs serve` and visit http://localhost:8000
- **API Docs**: http://localhost:8000/docs (when server running)
- **Issues**: https://github.com/Blood-Dawn/sagemtl/issues
- **Discussions**: Use GitHub Discussions for questions

## Next Steps

1. ✅ Backend v2 API is fully functional
2. ⏳ Frontend Compose page implementation
3. ⏳ Monaco Diff Editor integration
4. ⏳ WebSocket client for real-time updates
5. ⏳ Drag-drop file import UI
6. ⏳ Toast notifications

See `IMPLEMENTATION.md` for technical details on the new features.
