# SageMTL Codebase Exploration - Complete Summary

## Executive Summary

SageMTL is a comprehensive machine translation toolchain featuring a complete **Import → Clean → Translate → Export** workflow. It combines a Python FastAPI backend with a React 19 frontend, offering both CLI and web UI interfaces, with Electron support for cross-platform desktop deployment.

**Key Stats:**
- 2,380 lines of Python backend code
- 3,806 lines of TypeScript frontend code  
- 14 comprehensive test modules
- 11 modular backend components
- 7 main frontend pages

---

## 1. Architecture Overview

### Backend Structure (Python)
The backend is organized into 11 modular components:

```
Backend Components:
├── serve/         → FastAPI REST API (v1 & v2) with 4 routers
├── jobs/          → Persistent job storage & lifecycle management
├── translate/     → Translation queue + providers + glossary system
├── clean/         → Text normalization & cleaning pipelines
├── crawl/         → Web crawling & HTML extraction
├── datasets/      → Dataset registry & multi-format management
├── batch/         → Parallel batch processing with deduplication
├── config.py      → TOML-based configuration system
├── mtl/           → ML translation backends (HF, CTranslate2)
├── cli.py         → Typer CLI command interface
└── tui/           → Textual Terminal UI
```

### Frontend Structure (React + TypeScript)
```
Frontend Components:
├── pages/         → 7 main pages (Compose, Clean, Crawl, Translate, Datasets, Jobs, Settings)
├── components/    → UI components (Radix + Tailwind)
├── api/           → TypeScript API client (client-v2.ts)
├── hooks/         → Custom React hooks (WebSocket, Toast)
├── state/         → Zustand global state management
└── electron-main.cjs → Cross-platform desktop wrapper
```

---

## 2. Critical Systems Explained

### Job Queue & Persistence
**Location:** `/home/user/sagemtl/sagemtl/jobs/store.py` & `translate/queue.py`

- **Single daemon thread** processes translation jobs sequentially
- **Persistent JSON storage** at `~/.sagemtl/jobs.json` survives restarts
- **Thread-safe** with file locking
- **Non-blocking enqueue** - returns job ID immediately
- **Job lifecycle:** queued → running → done/failed/cancelled

### Translation Pipeline
**Location:** `/home/user/sagemtl/sagemtl/translate/queue.py`

```
Request → Enqueue → JobStore → Queue → Worker Thread
                                        ├─ Get provider
                                        ├─ Execute translation
                                        ├─ Apply glossary (if configured)
                                        └─ Update result/status
                                        
Frontend monitors via WebSocket (/api/jobs/ws/{job_id})
```

### Unified Clean + Translate Pipeline
**Location:** `/home/user/sagemtl/sagemtl/serve/routers/compose.py`

Three-step process or single unified endpoint:
1. **Clean:** Text normalization with optional glossary
2. **Translate:** Queue translation job with glossary support
3. **Pipeline:** Combined clean → translate → save workflow

### Web Crawling System
**Location:** `/home/user/sagemtl/sagemtl/crawl/pipeline.py` & `routers/crawl.py`

Features:
- BeautifulSoup-based HTML parsing
- Boilerplate removal (header, footer, nav, ads)
- Selector-based filtering (allow/block lists)
- Language detection per block
- Chapter extraction from novel websites
- XPath & CSS path generation

### Dataset Management
**Location:** `/home/user/sagemtl/sagemtl/datasets/registry.py`

Supports multiple formats:
- JSONL (line-delimited JSON)
- CSV (with headers)
- TXT, HTML, JSON, EPUB
- Auto-detection based on file extension
- Storage: `~/.sagemtl/data/{dataset_name}/`
- Metadata: Per-dataset `meta.json`

### Glossary System
**Location:** `/home/user/sagemtl/sagemtl/translate/glossary.py`

Features:
- CSV & JSON format support
- Per-entry options: case sensitivity, word boundaries
- Pre-translation & post-translation application
- Regex-based replacement

---

## 3. API Architecture

### Two API Versions

**v1 (Legacy)** - `/home/user/sagemtl/sagemtl/serve/api.py`
- Simple endpoint functions
- Backward compatibility
- POST /clean, POST /translate, GET /jobs, etc.

**v2 (Modern)** - `/home/user/sagemtl/sagemtl/serve/api_v2.py`
- Modular router architecture
- 4 routers: Compose, Jobs, Datasets, Crawl
- Easier to extend

### Four Main Routers

1. **Compose Router** (190 lines)
   - Clean with glossary
   - Translate with job queueing
   - Full pipeline in one endpoint

2. **Jobs Router** (226 lines)
   - List/get/cancel/retry jobs
   - WebSocket streaming for real-time updates
   - Job purging with status filters

3. **Datasets Router** (290 lines)
   - CRUD operations
   - Multi-format import/export
   - Novel-specific endpoints

4. **Crawl Router** (260 lines)
   - URL crawling with JS rendering
   - Chapter extraction
   - Save to dataset

---

## 4. Frontend Architecture

### Page Structure (7 Pages)

1. **Compose** - Unified pipeline interface
   - Tabs: Clean, Translate, Glossary, Pipeline
   - Monaco diff viewer (inline/side-by-side)
   - Real-time results with WebSocket tracking

2. **Clean** - Text normalization
   - Live preview with metrics
   - Option toggles
   - Diff viewer

3. **Crawl** - Web crawling
   - URL input with selectors
   - JS rendering option
   - Chapter extraction preview

4. **Translate** - Direct translation
   - Source text input
   - Model selection
   - Glossary upload
   - Result display

5. **Datasets** - Dataset management
   - Drag-drop import
   - Table view with filtering
   - Export functionality
   - Novel management

6. **Jobs** - Job monitoring
   - Table with status & progress
   - Job details modal
   - Cancel/retry actions
   - Auto-refresh toggle

7. **Settings** - Configuration
   - Theme toggle
   - API endpoint config
   - Provider selection
   - Export settings

### API Client
**File:** `/home/user/sagemtl/ui/src/api/client-v2.ts`

Comprehensive TypeScript client with typed interfaces for:
- Compose operations
- Job management
- Dataset operations
- Crawl operations

### State Management
Uses **Zustand** for global layout state:
- Sidebar visibility
- Selected job/dataset
- Layout preferences

### Custom Hooks
- `useJobWebSocket` - Real-time job updates
- `useToast` - Notification system

---

## 5. Key Features Summary

### Backend Capabilities
- FastAPI REST API with 2 versions
- Persistent job queue (JSON storage)
- Translation with multiple providers (pluggable)
- Text cleaning/normalization
- Web crawling with boilerplate removal
- Multi-format dataset management
- Glossary system (pre/post-processing)
- TOML configuration with env overrides
- Batch processing with deduplication
- WebSocket real-time updates
- CLI with Typer
- Terminal UI with Textual
- Job lifecycle (queue/cancel/retry)
- Language detection
- Path generation (XPath, CSS)

### Frontend Capabilities
- React 19 + TypeScript with type safety
- 7 specialized pages
- Real-time job monitoring (WebSocket)
- Drag-drop file import
- Monaco diff viewer
- Responsive mobile-friendly design
- Dark/light theme support
- Toast notifications
- Data tables with search/filter
- Modal dialogs
- Log console viewer
- Metric cards

### Desktop Features
- Electron wrapper for cross-platform
- Dev mode with hot reload
- Isolated renderer process (security)
- 1200x800 default window

---

## 6. Configuration System

### Settings Model
```python
Settings (Pydantic, immutable)
├── newline_mode: "lf" | "crlf" | "system" | "preserve"
├── clean_input_path: "-" (stdin)
├── clean_output_path: None (stdout)
├── crawl_glob: "*.html"
├── crawl_outdir: "out"
├── crawl_jsonl: False
└── thread_count: auto-calculated from CPU
```

### Storage & Overrides
- **File:** `~/.sagemtl/config.toml`
- **Env Var:** `SAGEMTL_CONFIG=path/to/config.toml`
- **Env Overrides:** `SAGEMTL_*=value` (e.g., `SAGEMTL_THREAD_COUNT=8`)
- **Caching:** Implemented for performance

---

## 7. Data Flow Examples

### Translation Workflow
```
User submits text
  → POST /api/compose/translate
  → TranslationQueue.enqueue(TranslationRequest)
  → JobStore saves record (status="queued")
  → Daemon thread picks up job
  → Get provider & execute
  → Apply glossary if configured
  → Save result (status="done"/"failed")
  → Frontend receives via WebSocket
  → Display result
```

### Dataset Import
```
User drops files
  → Drag-drop detected
  → POST /api/datasets/import (multipart)
  → Create ~/.sagemtl/data/{dataset_name}/
  → Parse files (auto-detect format)
  → Save to files/ subdirectory
  → Create meta.json
  → Update datasets.json registry
  → Return response with stats
  → Frontend refreshes list
```

### Web Crawl
```
User provides URL
  → POST /api/crawl/chapters
  → fetch_text(url)
  → Parse HTML (BeautifulSoup)
  → Apply allow/block selectors
  → Remove boilerplate
  → Extract blocks (with language detection)
  → Generate CSS path & XPath
  → Extract chapters (heuristic)
  → Save to dataset
  → Return job status
  → Frontend displays chapters
```

---

## 8. Testing Coverage

**14 test modules** covering:
- REST API endpoints
- Job queue operations
- Text cleaning & normalization
- Web crawling & extraction
- Dataset registry
- Configuration loading
- CLI commands
- Translation queue behavior

**Framework:** pytest + pytest-asyncio

---

## 9. Documentation Files Created

Two comprehensive guides have been created in the project root:

1. **ARCHITECTURE.md** (26KB)
   - Detailed architecture overview
   - All 11 backend modules explained
   - Complete API endpoint specification
   - Data models & structures
   - Key data flows
   - Configuration details

2. **QUICK-REFERENCE.md** (11KB)
   - Critical file locations (table format)
   - API endpoint map with request/response
   - Enums & constants
   - Data storage locations
   - Common dev tasks
   - Architecture decision records
   - Performance considerations
   - Future enhancement points

---

## 10. Critical File Reference

### Must-Know Backend Files
```
serve/api_v2.py           - Main FastAPI app
serve/routers/compose.py  - Unified pipeline
serve/routers/jobs.py     - Job management + WebSocket
serve/routers/datasets.py - Dataset CRUD
serve/routers/crawl.py    - Web crawling

jobs/store.py             - Persistent storage
translate/queue.py        - Job queue worker
translate/glossary.py     - Glossary system
translate/providers.py    - Provider plugins

clean/pipeline.py         - Text cleaning
crawl/pipeline.py         - HTML extraction
datasets/registry.py      - Dataset management
config.py                 - Configuration
```

### Must-Know Frontend Files
```
pages/compose.tsx         - Main Compose page
pages/clean.tsx          - Clean page
pages/datasets.tsx       - Dataset management
pages/jobs.tsx           - Job monitoring

api/client-v2.ts         - API client
routes.tsx               - Router setup
hooks/use-job-websocket.ts - WebSocket hook

components/app-shell.tsx - Main layout
electron-main.cjs        - Electron entry
```

---

## 11. Development Quick Start

```bash
# Backend
cd /home/user/sagemtl
python -m sagemtl serve          # or uvicorn sagemtl.serve.api_v2:app --reload

# Frontend  
cd ui
npm install
npm run dev                       # http://localhost:5173

# Desktop (both running)
npm run electron:dev             # Electron + Vite

# Tests
pytest                           # All tests
pytest tests/test_api.py -v     # Specific

# Build
npm run build                    # Production build in dist/
```

---

## 12. Architecture Highlights

### Strengths
1. Clear backend/frontend separation
2. Modular router design for easy extension
3. Persistent storage - jobs survive restarts
4. Type-safe with Pydantic & TypeScript
5. Pluggable translation providers
6. Multi-format dataset support
7. WebSocket real-time updates
8. Configurable glossary (pre/post)
9. Responsive, theme-aware UI
10. Cross-platform desktop support

### Current Limitations
1. Single-threaded translation queue (sequential)
2. JSON file storage (not database)
3. WebSocket via polling (not streaming)
4. No authentication/authorization
5. No rate limiting
6. Synchronous processing (not async)

### Future Enhancement Opportunities
- Async/await refactoring
- External job queue (Redis)
- Database (SQLite/PostgreSQL)
- Real WebSocket streaming
- Distributed workers
- Docker containerization
- Prometheus metrics
- Authentication layer

---

## 13. Key Takeaways

1. **Modular Design:** Each component has clear responsibility
2. **Persistent State:** Jobs survive restarts via JSON storage
3. **Unified Pipeline:** Compose page handles clean+translate+glossary
4. **Real-time Updates:** WebSocket for job progress
5. **Type Safety:** Full Pydantic & TypeScript validation
6. **Multi-format Support:** Datasets handle various input types
7. **Pluggable Architecture:** Easy to add translation providers
8. **Beautiful UI:** Radix + Tailwind with dark/light theme
9. **Cross-platform:** Works as web app, desktop, or CLI
10. **Well-tested:** 14 test modules with pytest

---

Generated: November 7, 2025
Codebase: SageMTL (machine translation toolchain)
Documentation: Complete architecture & reference guides included
