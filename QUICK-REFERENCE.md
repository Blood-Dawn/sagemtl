# SageMTL Quick Reference Guide

## Critical File Locations

### Backend Core
| Feature | Path | Key Class/Function |
|---------|------|-------------------|
| **API Server** | `/home/user/sagemtl/sagemtl/serve/api_v2.py` | `app: FastAPI` |
| **Compose Pipeline** | `/home/user/sagemtl/sagemtl/serve/routers/compose.py` | `compose_clean()`, `compose_translate()`, `compose_pipeline()` |
| **Job Management** | `/home/user/sagemtl/sagemtl/serve/routers/jobs.py` | `list_jobs()`, `job_progress_websocket()` |
| **Dataset API** | `/home/user/sagemtl/sagemtl/serve/routers/datasets.py` | `list_datasets()`, `import_dataset()` |
| **Crawl API** | `/home/user/sagemtl/sagemtl/serve/routers/crawl.py` | `crawl_chapters()`, `save_chapters_to_dataset()` |

### Job Queue & Storage
| Component | Path | Key Class |
|-----------|------|-----------|
| **Job Storage** | `/home/user/sagemtl/sagemtl/jobs/store.py` | `JobRecord`, `JobStore` |
| **Translation Queue** | `/home/user/sagemtl/sagemtl/translate/queue.py` | `TranslationRequest`, `TranslationQueue` |
| **Translation Providers** | `/home/user/sagemtl/sagemtl/translate/providers.py` | `EchoProvider`, `UnconfiguredProvider` |
| **Glossary System** | `/home/user/sagemtl/sagemtl/translate/glossary.py` | `GlossaryEntry`, `load_glossary()`, `apply_glossary()` |

### Processing Pipelines
| Pipeline | Path | Key Function |
|----------|------|--------------|
| **Text Cleaning** | `/home/user/sagemtl/sagemtl/clean/pipeline.py` | `clean_text()`, `iter_clean_batch()` |
| **Text Normalization** | `/home/user/sagemtl/sagemtl/clean/text_normalize.py` | `normalize_text()` |
| **Web Crawling** | `/home/user/sagemtl/sagemtl/crawl/pipeline.py` | `crawl_html()` |
| **HTML Fetching** | `/home/user/sagemtl/sagemtl/crawl/http.py` | `fetch_text()` |
| **HTML Extraction** | `/home/user/sagemtl/sagemtl/crawl/extract.py` | Text block extraction |
| **Batch Processing** | `/home/user/sagemtl/sagemtl/batch/runner.py` | `BatchRunner` |

### Data Management
| Feature | Path | Key Class |
|---------|------|-----------|
| **Dataset Registry** | `/home/user/sagemtl/sagemtl/datasets/registry.py` | `DatasetRecord`, `DatasetRegistry` |
| **MTL Backends** | `/home/user/sagemtl/sagemtl/mtl/translate.py` | `_HF`, `_CT2`, `get_translator()` |
| **Configuration** | `/home/user/sagemtl/sagemtl/config.py` | `Settings`, `load_config()`, `save_config()` |

### Frontend Pages
| Page | Path | Purpose |
|------|------|---------|
| **Compose** | `/home/user/sagemtl/ui/src/pages/compose.tsx` | Unified Clean+Translate+Glossary |
| **Clean** | `/home/user/sagemtl/ui/src/pages/clean.tsx` | Text normalization UI |
| **Crawl** | `/home/user/sagemtl/ui/src/pages/crawl.tsx` | Web crawling interface |
| **Translate** | `/home/user/sagemtl/ui/src/pages/translate.tsx` | Direct translation |
| **Datasets** | `/home/user/sagemtl/ui/src/pages/datasets.tsx` | Dataset management |
| **Jobs** | `/home/user/sagemtl/ui/src/pages/jobs.tsx` | Job monitoring & control |
| **Settings** | `/home/user/sagemtl/ui/src/pages/settings.tsx` | Configuration UI |

### Frontend Infrastructure
| Component | Path | Purpose |
|-----------|------|---------|
| **API Client** | `/home/user/sagemtl/ui/src/api/client-v2.ts` | All API calls |
| **Routing** | `/home/user/sagemtl/ui/src/routes.tsx` | Route definitions |
| **WebSocket Hook** | `/home/user/sagemtl/ui/src/hooks/use-job-websocket.ts` | Real-time job updates |
| **Layout Store** | `/home/user/sagemtl/ui/src/state/layout-store.ts` | Global state (Zustand) |
| **App Shell** | `/home/user/sagemtl/ui/src/components/app-shell.tsx` | Main layout |
| **Electron Entry** | `/home/user/sagemtl/ui/electron-main.cjs` | Electron bootstrap |

---

## API Endpoint Map

### Compose Router (`/api/compose/`)
```
POST /api/compose/clean
  Request: { text: string, options: CleanOptions }
  Response: { text: string, meta: dict, glossary_applied: bool }

POST /api/compose/translate
  Request: { text: string, src_lang, tgt_lang, provider, glossary_path, ... }
  Response: { job_id: string, status: string }

POST /api/compose/pipeline
  Request: { source_text: string, clean_options, src_lang, tgt_lang, ... }
  Response: { translate_job_id: string, status: string, message: string }
```

### Jobs Router (`/api/jobs/`)
```
GET /api/jobs
  Response: List[JobResponse] with all job details

GET /api/jobs/{job_id}
  Response: JobResponse (single job)

DELETE /api/jobs/{job_id}
  Response: { status: "cancelled", job_id: string }

POST /api/jobs/{job_id}/retry
  Response: { status: "retried", new_job_id: string }

DELETE /api/jobs?keep_running=true
  Response: { purged: int }

WebSocket /api/jobs/ws/{job_id}
  Messages:
    - { type: "progress", job_id, status, progress, message, updated_at }
    - { type: "complete", job_id, status, result, error, updated_at }
    - { type: "error", message }
```

### Datasets Router (`/api/datasets/`)
```
GET /api/datasets
  Response: List[DatasetRecord]

POST /api/datasets/import
  Request: multipart/form-data with files
  Response: { dataset_id, name, files_imported, total_bytes, items }

GET /api/datasets/{dataset_id}
  Response: DatasetRecord

DELETE /api/datasets/{dataset_id}
  Response: { status: "deleted" }

GET /api/datasets/{dataset_id}/export
  Response: Binary file (zip or original format)

GET /api/datasets/novels
  Response: List[NovelDataset]

POST /api/datasets/novels
  Request: { name, title, chapters_json }
  Response: { id, name, chapter_count }
```

### Crawl Router (`/api/crawl/`)
```
POST /api/crawl/chapters
  Request: {
    start_url: string,
    depth: int,
    max_chapters?: int,
    allow_selectors: List[str],
    block_selectors: List[str],
    render_js: bool,
    dataset_name?: string,
    novel_title?: string
  }
  Response: { job_id, status, message }

GET /api/crawl/jobs/{job_id}
  Response: Job status with extracted chapters
```

---

## Key Enums & Constants

### Job Status
```
"queued"      - Waiting to run
"running"     - Currently executing
"done"        - Completed successfully
"failed"      - Execution error
"cancelled"   - User cancelled
```

### Dataset Formats
```
"jsonl"       - Line-delimited JSON
"csv"         - Comma-separated values
"txt"         - Plain text
"html"        - HTML documents
"json"        - JSON array
"epub"        - EPUB ebook
```

### Translation Providers
```
"echo"        - Default (returns input unchanged)
"hf"          - HuggingFace Transformers
"ctranslate2" - CTranslate2
```

### Clean Options
```
smart_quotes        - Convert " ' to curly variants
em_dash            - Normalize dashes
minus_sign         - Normalize minus signs
nbsp_to_space      - Replace non-breaking spaces
zero_width         - Remove zero-width characters
collapse_blank_lines - Remove extra blank lines
ensure_trailing_lf - Add final newline
trim_trailing_spaces - Remove line-end spaces
unicode_nfkc       - Unicode normalization
normalize_eol      - Normalize line endings (lf/crlf/preserve)
```

---

## Data Storage Locations

```
~/.sagemtl/
├── config.toml                 # Configuration (TOML format)
├── jobs.json                   # Job records (JSON array)
└── data/
    ├── datasets.json          # Dataset registry metadata
    ├── dataset1/
    │   ├── meta.json          # Dataset metadata
    │   └── files/
    │       ├── item1.txt
    │       ├── item2.jsonl
    │       └── ...
    └── dataset2/
        ├── meta.json
        └── files/
            └── ...
```

Environment variable overrides:
- `SAGEMTL_CONFIG` - Config file path
- `SAGEMTL_DATA_DIR` - Data directory path
- `SAGEMTL_JOBS_PATH` - Jobs file path

---

## Common Development Tasks

### Start Backend API Server
```bash
cd /home/user/sagemtl
python -m sagemtl serve
# Or directly with Uvicorn:
uvicorn sagemtl.serve.api_v2:app --reload --port 8000
```

### Start Frontend Dev Server
```bash
cd /home/user/sagemtl/ui
npm install
npm run dev
# Runs on http://localhost:5173
```

### Start Desktop App (Electron + Vite)
```bash
cd /home/user/sagemtl/ui
npm run electron:dev
# Requires both Vite (5173) and Electron running
```

### Run Tests
```bash
cd /home/user/sagemtl
pytest                              # All tests
pytest tests/test_api.py -v        # Specific test file
pytest tests/test_*.py -k "clean"  # Filter by keyword
pytest --cov=sagemtl               # With coverage
```

### Build Frontend
```bash
cd /home/user/sagemtl/ui
npm run build
# Output in dist/
```

---

## Architecture Decision Records

### Why Thread-based Queue?
- Simple, synchronous model
- Persistent JSON storage survives restarts
- Single worker processes jobs sequentially
- No need for external job broker (Redis, RabbitMQ)

### Why Pydantic Models?
- Type validation on request/response
- Auto API documentation (FastAPI/Swagger)
- JSON serialization built-in

### Why Zustand for Frontend State?
- Lightweight global state (vs Redux)
- Fine-grained reactivity
- Minimal boilerplate

### Why Electron?
- Cross-platform desktop (Windows, macOS, Linux)
- Reuse React UI code
- Built-in auto-update support

### Why Split API v1 & v2?
- v1 maintains backward compatibility
- v2 uses modular routers for better organization
- Both available simultaneously

---

## Testing Coverage

**Backend:** 14 test files covering
- API endpoints (REST)
- Job queue operations
- Text cleaning/normalization
- Web crawling
- Dataset registry
- CLI commands
- Configuration loading

**Frontend:** E2E capable with Playwright (configured in package.json)

---

## Dependencies Summary

### Backend (Python)
Core: `fastapi`, `pydantic`, `uvicorn`, `typer`
Processing: `beautifulsoup4`, `lxml`, `selectolax`
Other: `httpx`, `websockets`, `textual`

### Frontend (Node)
Core: `react@19`, `react-router-dom@7`, `vite@7`
UI: `@radix-ui/*`, `tailwindcss`, `lucide-react`
State: `zustand`, `jotai`
Editor: `@monaco-editor/react`
Desktop: `electron@39`

---

## Performance Considerations

1. **Job Storage**: JSON file - suitable for small-to-medium workloads (< 10k jobs)
2. **Translation Queue**: Single daemon thread - sequential processing only
3. **WebSocket Polling**: 500ms interval - balance between responsiveness and load
4. **Clean/Crawl**: No async I/O - synchronous processing
5. **Frontend**: React lazy routes for code splitting (opportunity)

---

## Future Enhancement Points

1. Real async job processing (async def in FastAPI)
2. External job queue (Redis/RabbitMQ)
3. Distributed translation workers
4. Database storage (SQLite/PostgreSQL vs JSON)
5. Real-time WebSocket instead of polling
6. Streaming API responses
7. Rate limiting & auth
8. Caching layer (Redis)
9. Metrics/monitoring (Prometheus)
10. Deployment containerization (Docker)
