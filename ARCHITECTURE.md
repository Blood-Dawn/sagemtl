# SageMTL Codebase Architecture Overview

## Project Summary
**SageMTL** is a comprehensive machine translation toolchain with a complete **Import → Process → Export** workflow. It provides a unified platform for text cleaning, web crawling, translation, and dataset management with both CLI and web UI interfaces.

**Technology Stack:**
- **Backend:** Python 3.11+ with FastAPI, Pydantic, BeautifulSoup4, lxml
- **Frontend:** React 19 + TypeScript with Vite, Radix UI, TailwindCSS
- **Desktop:** Electron for cross-platform desktop application
- **Job Queue:** In-process threaded queue with persistent JSON storage
- **Code Stats:** 2,380 lines of Python backend + 3,806 lines of TypeScript frontend + 14 test files

---

## 1. Project Structure

```
sagemtl/
├── sagemtl/              # Python backend package
│   ├── serve/            # FastAPI application & routers
│   ├── clean/            # Text normalization & cleaning
│   ├── translate/        # Translation services & providers
│   ├── crawl/            # Web crawling & HTML extraction
│   ├── jobs/             # Job queue & persistent storage
│   ├── datasets/         # Dataset registry & management
│   ├── batch/            # Batch processing utilities
│   ├── mtl/              # Machine translation backends
│   ├── tui/              # Terminal UI (Textual)
│   ├── cli.py            # CLI commands
│   └── config.py         # Configuration system
├── ui/                   # Frontend (React + Electron)
│   ├── src/
│   │   ├── pages/        # Page components (7 pages)
│   │   ├── components/   # Reusable UI components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── api/          # API client
│   │   └── routes.tsx    # Route definitions
│   ├── electron-main.cjs # Electron entry point
│   └── vite.config.ts    # Vite build config
├── tests/                # Test suite (14 test files)
└── docs/                 # Documentation
```

---

## 2. Backend Architecture (Python)

### 2.1 FastAPI Application (`serve/`)

#### **Main API Endpoints**

**File:** `/home/user/sagemtl/sagemtl/serve/api_v2.py` (Modern, v2.0)

Two API versions available:
- **API v1** (`api.py`) - Legacy endpoints (backward compatible)
- **API v2** (`api_v2.py`) - Modern modular architecture with routers

**Root Endpoints:**
- `GET /` - API info
- `GET /health` - Health check
- `POST /clean` - Legacy clean endpoint

#### **Routers (Modular Design)**

**1. Compose Router** (`routers/compose.py` - 190 lines)
   - **Purpose:** Unified Clean + Translate + Glossary pipeline
   - **Endpoints:**
     - `POST /api/compose/clean` - Clean text with glossary support
     - `POST /api/compose/translate` - Queue translation job with glossary
     - `POST /api/compose/pipeline` - Full pipeline (Clean → Translate → Save)
   - **Features:**
     - Pre/post-translation glossary application
     - Dataset integration
     - Result persistence

**2. Jobs Router** (`routers/jobs.py` - 226 lines)
   - **Purpose:** Job management & tracking with WebSocket support
   - **Endpoints:**
     - `GET /api/jobs` - List all jobs
     - `GET /api/jobs/{job_id}` - Get job details
     - `DELETE /api/jobs/{job_id}` - Cancel job
     - `POST /api/jobs/{job_id}/retry` - Retry failed job
     - `DELETE /api/jobs` - Purge completed jobs
     - `WebSocket /api/jobs/ws/{job_id}` - Real-time progress streaming
   - **Features:**
     - WebSocket progress updates (JSON messages)
     - Job lifecycle management
     - Configurable purge policies

**3. Datasets Router** (`routers/datasets.py` - 290 lines)
   - **Purpose:** Dataset CRUD, Import/Export, Novel management
   - **Endpoints:**
     - `GET /api/datasets` - List all datasets
     - `POST /api/datasets/import` - Upload & import files
     - `GET /api/datasets/{dataset_id}` - Get dataset details
     - `DELETE /api/datasets/{dataset_id}` - Delete dataset
     - `GET /api/datasets/{dataset_id}/export` - Export dataset
     - `GET /api/datasets/novels` - List novels
     - `POST /api/datasets/novels` - Create novel
   - **Features:**
     - Multi-format support (TXT, CSV, JSONL, JSON, EPUB)
     - Metadata storage (cover_path, chapter_count)
     - Drag-drop file import
     - Novel dataset with chapter management

**4. Crawl Router** (`routers/crawl.py` - 260 lines)
   - **Purpose:** Web crawling & chapter extraction
   - **Endpoints:**
     - `POST /api/crawl/fetch` - Fetch and crawl URL
     - `POST /api/crawl/html` - Crawl HTML content
     - `POST /api/crawl/chapters` - Extract chapters from novel sites
     - `GET /api/crawl/jobs/{job_id}` - Get crawl job status
   - **Features:**
     - JavaScript rendering support
     - Boilerplate removal
     - Selector-based filtering (allow/block lists)
     - Chapter detection and dataset saving

---

### 2.2 Job Queue System (`jobs/`)

**File:** `/home/user/sagemtl/sagemtl/jobs/store.py` (100+ lines)

**Architecture:**
```
JobRecord (dataclass)
├── id: str (UUID)
├── type: str (e.g., "translate", "crawl", "clean")
├── status: str ("queued", "running", "done", "failed", "cancelled")
├── created_at/updated_at: ISO timestamp
├── meta: Dict[str, object] (progress, dataset_id, etc.)
├── payload: Dict[str, object] (request parameters)
├── result: Dict[str, object] | None (output data)
├── error: str | None (error message)
└── log: List[str] (execution logs)

JobStore (thread-safe)
├── _path: JSON file location (~/.sagemtl/jobs.json)
├── _lock: Threading lock
├── _jobs: Dict[str, JobRecord]
├── list() - Get all jobs
├── get(job_id) - Get specific job
├── upsert(record) - Create/update job
├── purge(statuses) - Delete jobs by status
└── _load/_flush - Persistence
```

**Storage:** 
- Location: `~/.sagemtl/jobs.json` (configurable via `SAGEMTL_JOBS_PATH`)
- Format: JSON array of JobRecord objects
- Thread-safe with file locking

---

### 2.3 Translation Queue (`translate/`)

**File:** `/home/user/sagemtl/sagemtl/translate/queue.py` (100+ lines)

**Architecture:**
```
TranslationRequest (dataclass)
├── text: str
├── src_lang: str
├── tgt_lang: str
├── provider_name: str | None
├── glossary_path: str | None
└── meta: Dict[str, object]

TranslationQueue
├── store: JobStore
├── _queue: Queue[str] (job IDs)
├── _worker: Thread (daemon)
├── enqueue(request) → JobRecord
└── _run() [Worker thread]
    ├── Get job from queue
    ├── Set status to "running"
    ├── Get provider
    ├── Execute translation
    ├── Apply glossary (if configured)
    └── Update result/status
```

**Worker Model:**
- Single daemon thread processing jobs sequentially
- Non-blocking enqueue returns immediately
- Glossary applied in worker thread post-translation

---

### 2.4 Translation Providers (`translate/providers.py`)

**Implemented:**
1. **EchoProvider** (default)
   - Returns input text unchanged
   - Used for testing/development

2. **UnconfiguredProvider**
   - Raises `NotConfigured` exception
   - For disabled providers

**Supported Backends (not configured by default):**
- `ctranslate2` - CTranslate2 inference
- `hf-pipeline` / `hf` - HuggingFace Transformers
- Custom providers via name

---

### 2.5 Configuration System (`config.py`)

**File:** `/home/user/sagemtl/sagemtl/config.py` (251 lines)

**Configuration Model:**
```python
Settings (Pydantic BaseModel, frozen=True)
├── newline_mode: Literal["lf", "crlf", "system", "preserve"] = "lf"
├── clean_input_path: str = "-"
├── clean_output_path: str | None = None
├── crawl_glob: str = "*.html"
├── crawl_outdir: str = "out"
├── crawl_jsonl: bool = False
└── thread_count: int = CPU count

load_config(path, use_cache=True) → Settings
save_config(settings, path) → Path
update_config(updates, path) → Settings
resolve_newline(mode) → str | None
```

**Features:**
- TOML file storage (`~/.sagemtl/config.toml`)
- Environment variable overrides (`SAGEMTL_*` prefix)
- Caching for performance
- Flexible newline handling
- Auto thread count calculation

---

### 2.6 Text Cleaning Pipeline (`clean/`)

**File:** `/home/user/sagemtl/sagemtl/clean/pipeline.py` (80+ lines)

**Pipeline Architecture:**
```
clean_text(text, options)
├── Input: str, CleanOptions
├── Call: normalize_text(text, NormalizeOptions)
├── Return: CleanResult
│   ├── text: str (cleaned)
│   └── meta: Dict[str, Any]
│       └── length: int
└── Batch: iter_clean_batch(path, options)
    ├── Supports: JSONL, CSV, Directory, Stdin
    └── Yields: (source, meta | {"text": ...})
```

**Normalization Options:**
```python
NormalizeOptions
├── smart_quotes: bool
├── em_dash: bool
├── minus_sign: bool
├── nbsp_to_space: bool
├── zero_width: bool
├── collapse_blank_lines: bool
└── ensure_trailing_lf: bool
```

---

### 2.7 Web Crawling Pipeline (`crawl/`)

**File:** `/home/user/sagemtl/sagemtl/crawl/pipeline.py` (80+ lines)

**Architecture:**
```
crawl_html(html, source, options)
├── Options:
│   ├── depth: int (nesting level)
│   ├── render_js: bool
│   ├── allow_selectors: List[str]
│   ├── block_selectors: List[str]
│   └── normalize: NormalizeOptions
├── Processing:
│   ├── Parse HTML with BeautifulSoup
│   ├── Apply blocklist (remove ads, nav, etc.)
│   ├── Extract text blocks
│   ├── Detect language per block
│   ├── Normalize text
│   └── Generate CSS path & XPath
└── Returns: CrawlResult
    ├── source: str
    ├── blocks: List[CrawlBlock]
    │   ├── order: int
    │   ├── text: str
    │   ├── css_path: str
    │   ├── xpath: str
    │   └── lang: str | None
    └── meta: dict
```

**Key Features:**
- Boilerplate removal (header, footer, nav, aside)
- Selector-based filtering
- Multi-language detection
- CSS path & XPath generation
- HTTP fetch integration (`fetch_text(url)`)

---

### 2.8 Dataset Management (`datasets/`)

**File:** `/home/user/sagemtl/sagemtl/datasets/registry.py` (100+ lines)

**Data Directory Structure:**
```
~/.sagemtl/data/
├── datasets.json         # Registry metadata
├── dataset1/
│   ├── meta.json        # Dataset metadata
│   └── files/           # Data files
│       ├── item1.txt
│       └── item2.jsonl
└── dataset2/
    ├── meta.json
    └── files/
```

**Registry Model:**
```python
DatasetRecord
├── name: str
├── filename: str
├── format: DatasetFormat ("jsonl" | "csv")
├── created_at: str (ISO)
├── meta: Dict[str, object]
└── path: Path (property)

DatasetRegistry
├── list() → List[DatasetRecord]
├── add(name, source, fmt, meta) → DatasetRecord
├── remove(name) → bool
└── get(name) → DatasetRecord | None
```

**Supported Formats:**
- JSONL (line-delimited JSON)
- CSV (with headers)
- Auto-detection based on file extension

---

### 2.9 Glossary System (`translate/glossary.py`)

**File:** `/home/user/sagemtl/sagemtl/translate/glossary.py` (80+ lines)

**Model:**
```python
GlossaryEntry
├── source: str
├── target: str
├── case_sensitive: bool = True
├── word_boundary: bool = False
└── notes: str

load_glossary(path) → List[GlossaryEntry]
├── Supports: CSV, JSON
└── Returns: List of entries

apply_glossary(text, entries) → str
└── Performs regex-based replacement
```

**CSV Format:**
```
source,target,case_sensitive,word_boundary,notes
Hello,Bonjour,true,false,Greeting
Montreal,Montréal,true,false,City name
```

---

### 2.10 MTL Translation Backends (`mtl/`)

**File:** `/home/user/sagemtl/sagemtl/mtl/translate.py`

**Supported Backends:**
```python
_HF (HuggingFace)
├── Uses: transformers pipeline
├── Model: Loaded from HF Hub
└── Device: Auto-detect CUDA

_CT2 (CTranslate2)
├── Uses: ctranslate2 + sentencepiece
├── Model: Directory with model + src/tgt.model
└── Device: CUDA/CPU auto-detection

get_translator(backend, model, device)
└── Returns: _HF | _CT2 instance
```

**Features:**
- GPU acceleration support
- Batch processing capable
- Proper device management

---

## 3. Frontend Architecture (React + TypeScript)

### 3.1 Project Setup

**Technology:**
- React 19.2.0 + React Router v7
- TypeScript ~5.9.3
- Vite 7.1.12 (build tool)
- Electron 39.1.0 (desktop)
- TailwindCSS 3.4.15 + Radix UI components

**Entry Point:** `ui/src/App.tsx`
```tsx
App
├── ThemeProvider (dark/light mode)
├── Toaster (notification system)
└── RouterProvider
    └── Router with nested routes
```

---

### 3.2 Routing Architecture (`routes.tsx`)

**Route Structure:**
```
/ (AppShell layout)
├── / → /compose (redirect)
├── /compose       (ComposePage)
├── /clean         (CleanPage)
├── /crawl         (CrawlPage)
├── /translate     (TranslatePage)
├── /datasets      (DatasetsPage)
├── /jobs          (JobsPage)
└── /settings      (SettingsPage)
```

**Layout Component:** `AppShell`
- Sidebar navigation
- Header with branding
- Main content area (Outlet)
- Responsive mobile layout

---

### 3.3 API Client (`api/client-v2.ts`)

**Architecture:**
```typescript
const API_BASE_URL = 'http://localhost:8000'

// Compose API
apiClient.composeclean(payload) → Promise<ComposeCleanResponse>
apiClient.composeTranslate(payload) → Promise<ComposeTranslateResponse>
apiClient.composePipeline(payload) → Promise<ComposePipelineResponse>

// Jobs API
apiClient.listJobs() → Promise<{ jobs: JobRecord[] }>
apiClient.getJob(jobId) → Promise<JobRecord>
apiClient.cancelJob(jobId) → Promise<void>
apiClient.retryJob(jobId) → Promise<void>

// Datasets API
apiClient.listDatasets() → Promise<{ datasets: Dataset[] }>
apiClient.importDataset(files) → Promise<ImportResponse>
apiClient.exportDataset(datasetId) → Promise<Blob>
apiClient.listNovels() → Promise<{ novels: Novel[] }>

// Crawl API
apiClient.crawlURL(url, options) → Promise<CrawlResponse>
```

**Type Definitions:**
```typescript
JobRecord
├── id: string
├── type: string ("translate" | "crawl" | "clean")
├── status: string ("queued" | "running" | "done" | "failed" | "cancelled")
├── created_at/updated_at: string (ISO)
├── meta: Record<string, unknown>
├── result?: Record<string, unknown>
├── error?: string
└── log: string[]

CleanOptions
├── smart_quotes?: boolean
├── em_dash?: boolean
├── minus_sign?: boolean
├── ... (7 more boolean options)
├── normalize_eol?: string
├── apply_glossary?: boolean
└── glossary_path?: string
```

---

### 3.4 Pages (7 Main Pages)

#### 1. **Compose Page** (`pages/compose.tsx`)
**Purpose:** Unified Clean + Translate + Glossary Pipeline

**Layout:**
- Left: Source editor + options
- Center: Tabs for Clean, Translate, Glossary, Pipeline
- Right: Monaco diff editor (before/after)

**Features:**
- Real-time clean preview
- Translation job queueing
- Glossary pre/post-processing
- WebSocket job tracking
- Diff view (inline/side-by-side)

**State:**
```tsx
sourceText: string
cleanedText: string
translatedText: string
currentJobId: string | null
cleanOptions: CleanOptions
translateOptions: {
  src_lang, tgt_lang, provider, glossary_path,
  apply_glossary_pre, apply_glossary_post,
  save_to_dataset
}
```

#### 2. **Clean Page** (`pages/clean.tsx`)
**Purpose:** Text normalization with preview

**Features:**
- Input textarea with sample text
- Option toggles (smart quotes, dashes, zero-width, linewrap)
- Live preview
- Metrics cards (queued jobs, latency, artifacts removed)
- Diff viewer

#### 3. **Crawl Page** (`pages/crawl.tsx`)
**Purpose:** Web crawling & HTML extraction

**Features:**
- URL input
- CSS/XPath selector filtering
- JavaScript rendering option
- Depth control
- Chapter extraction
- Chapter preview with metadata

#### 4. **Translate Page** (`pages/translate.tsx`)
**Purpose:** Direct translation interface

**Features:**
- Source text input (with sample)
- Model selection dropdown
- Glossary file upload
- Translation queueing
- Result display
- Layout store integration

#### 5. **Datasets Page** (`pages/datasets.tsx`)
**Purpose:** Dataset management (CRUD, import/export)

**Features:**
- Drag-drop file import
- Dataset listing table with:
  - Name, format, size, item count
  - Created/updated timestamps
  - Type badge (text/novel/translation)
- Search/filter
- Export button
- Novel-specific view

**Table Columns:**
```
Name | Type | Format | Size | Items | Created | Actions
```

#### 6. **Jobs Page** (`pages/jobs.tsx`)
**Purpose:** Job management & monitoring

**Features:**
- Job listing with pagination
- Status badges (queued, running, done, failed, cancelled)
- Progress bar for running jobs
- Real-time status updates (WebSocket)
- Job details modal showing:
  - Full job record
  - Logs/output
  - Error messages
  - Result data
- Actions:
  - View details
  - Cancel (for running/queued)
  - Retry (for failed/cancelled)
- Auto-refresh toggle (5s interval)

**Table Columns:**
```
Job ID | Type | Status | Progress | Created | Updated | Actions
```

#### 7. **Settings Page** (`pages/settings.tsx`)
**Purpose:** Application configuration

**Features:**
- Theme toggle (dark/light)
- API endpoint configuration
- Translation provider selection
- Clean options defaults
- Export configuration

---

### 3.5 Custom Hooks

#### **useJobWebSocket** (`hooks/use-job-websocket.ts`)
```typescript
useJobWebSocket({
  jobId: string,
  enabled: boolean,
  onProgress: (msg) => void,
  onComplete: (msg) => void,
  onError: (msg) => void
})

// Messages:
{
  type: "progress" | "complete" | "error",
  job_id: string,
  status: string,
  progress?: number,
  message?: string,
  result?: Record<string, unknown>,
  error?: string
}
```

#### **useToast** (`hooks/use-toast.ts`)
```typescript
useToast() → {
  toast: (options) => void,
  dismiss: (toastId) => void
}
```

---

### 3.6 State Management

#### **Layout Store** (`state/layout-store.ts`)
Uses **Zustand** for global state:
```typescript
useLayoutStore() → {
  sidebarOpen: boolean,
  selectedJob?: string,
  selectedDataset?: string,
  select: (options) => void,
  toggleSidebar: () => void
}
```

---

### 3.7 UI Components

**Base Components** (Radix UI + Tailwind):
- Button, Card, Input, Textarea, Label
- Select, Dialog, Dropdown Menu
- Badge, Avatar, Progress
- Checkbox, Switch, Separator
- Tabs, Toast, Scroll Area
- Tooltip, Popover, Collapsible

**Custom Components:**
```
app-shell.tsx        - Main layout shell
diff-viewer.tsx      - Monaco-based diff view
data-table.tsx       - TanStack React Table
log-console.tsx      - Scrollable log viewer
metric-card.tsx      - Dashboard metric display
job-status-badge.tsx - Status indicator
wizard-modal.tsx     - Multi-step dialogs
```

---

## 4. Desktop Application (Electron)

**File:** `/home/user/sagemtl/ui/electron-main.cjs`

```javascript
BrowserWindow (1200x800)
├── Dev mode: Load http://localhost:5173 (Vite dev server)
└── Prod mode: Load dist/index.html (built bundle)

Security:
├── nodeIntegration: false
├── contextIsolation: true
└── preload: (not configured yet)

Lifecycle:
├── createWindow() on app.whenReady()
├── Quit on window-all-closed (except macOS)
└── Support for macOS lifecycle events
```

---

## 5. Key Data Flows

### 5.1 Translation Workflow
```
User Input
  ↓
API: POST /api/compose/translate
  ↓
TranslationQueue.enqueue(TranslationRequest)
  ├─ Create JobRecord (status="queued")
  ├─ Store in JobStore
  └─ Queue job ID
  ↓
Worker Thread _run()
  ├─ Status → "running"
  ├─ Get Provider
  ├─ Execute translation
  ├─ Load & apply glossary (if configured)
  ├─ Status → "done" / "failed"
  └─ Update result/error
  ↓
Frontend (WebSocket /api/jobs/ws/{job_id})
  ├─ Polling updates every 500ms
  ├─ Display progress
  └─ Handle completion
```

### 5.2 Clean + Translate Pipeline
```
User provides source text
  ↓
API: POST /api/compose/clean
  ├─ normalize_text(text, options)
  ├─ Apply glossary (optional)
  └─ Return cleaned text
  ↓
API: POST /api/compose/translate
  ├─ Apply pre-glossary (optional)
  ├─ Enqueue translation job
  └─ Return job_id
  ↓
API: POST /api/compose/pipeline
  ├─ Combine above two steps
  ├─ Save results to dataset (optional)
  └─ Return translate_job_id for tracking
```

### 5.3 Dataset Import Workflow
```
User drops files
  ↓
Frontend: Drag-drop detected
  ↓
API: POST /api/datasets/import (FormData with files)
  ├─ Create dataset directory
  ├─ Parse files (detect format)
  ├─ Save to ~/.sagemtl/data/{dataset_name}/
  ├─ Create meta.json
  ├─ Update registry
  └─ Return ImportResponse
  ↓
Frontend: Refresh dataset list
```

### 5.4 Web Crawl Workflow
```
User provides URL + options
  ↓
API: POST /api/crawl/chapters
  ├─ Fetch HTML (with optional JS rendering)
  ├─ Parse with BeautifulSoup
  ├─ Apply allow/block selectors
  ├─ Remove boilerplate
  ├─ Extract text blocks
  ├─ Detect language
  ├─ Generate CSS path & XPath
  ├─ Extract chapters (heuristic)
  ├─ Create crawl job
  └─ Save chapters to dataset
  ↓
Frontend: Display extracted chapters
```

---

## 6. Configuration

### 6.1 Environment Variables

**Python:**
```bash
SAGEMTL_CONFIG=~/.sagemtl/config.toml    # Config file location
SAGEMTL_DATA_DIR=~/.sagemtl/data         # Dataset storage
SAGEMTL_JOBS_PATH=~/.sagemtl/jobs.json   # Job storage
SAGEMTL_THREAD_COUNT=4                   # Worker threads
SAGEMTL_*=value                          # Override config keys
```

**Frontend:**
```bash
VITE_API_URL=http://localhost:8000       # API endpoint
NODE_ENV=development                     # Dev/prod mode
```

### 6.2 Configuration Files

**~/.sagemtl/config.toml:**
```toml
newline_mode = "lf"
clean_input_path = "-"
clean_output_path = null
crawl_glob = "*.html"
crawl_outdir = "out"
crawl_jsonl = false
thread_count = 4
```

---

## 7. Testing

**Test Files:** 14 test modules
- `test_api.py` - API endpoint tests
- `test_batch.py` - Batch runner tests
- `test_clean*.py` - Text cleaning tests (3 files)
- `test_cli*.py` - CLI command tests (2 files)
- `test_crawl*.py` - Crawling tests (2 files)
- `test_config.py` - Configuration tests
- `test_datasets.py` - Dataset registry tests
- `test_extract.py` - HTML extraction tests
- `test_normalize.py` - Normalization tests
- `test_translation_queue.py` - Queue tests
- `test_translate*.py` - Provider tests

**Test Framework:** pytest + pytest-asyncio

---

## 8. Key Features Summary

### Backend Features
✓ FastAPI REST API (v1 & v2)
✓ Job queue with persistent storage
✓ Translation providers (pluggable architecture)
✓ Text normalization pipeline
✓ Web crawling with boilerplate removal
✓ Dataset management (multi-format)
✓ Glossary system (pre/post-processing)
✓ Configuration system (TOML + env vars)
✓ Batch processing with deduplication
✓ CLI with Typer
✓ Terminal UI with Textual
✓ WebSocket support for job monitoring
✓ Job lifecycle management (queue/cancel/retry)
✓ Multi-language detection
✓ XPath & CSS path generation

### Frontend Features
✓ React 19 + TypeScript
✓ 7 main pages (compose, clean, crawl, translate, datasets, jobs, settings)
✓ Real-time job monitoring (WebSocket)
✓ Drag-drop file import
✓ Monaco diff viewer
✓ Responsive design
✓ Dark/light theme
✓ Toast notifications
✓ Data tables with search/filter
✓ Modal dialogs
✓ Log console viewer
✓ Metric cards

### Desktop Features
✓ Electron wrapper
✓ Cross-platform (Windows, macOS, Linux)
✓ Dev mode with hot reload
✓ Isolated renderer process

---

## 9. Critical Files Reference

| Path | Purpose | Lines |
|------|---------|-------|
| `serve/api_v2.py` | Modern API with routers | ~93 |
| `serve/routers/compose.py` | Pipeline coordinator | 190 |
| `serve/routers/jobs.py` | Job management + WebSocket | 226 |
| `serve/routers/datasets.py` | Dataset CRUD | 290 |
| `serve/routers/crawl.py` | Web crawling | 260 |
| `translate/queue.py` | Job queue worker | 100+ |
| `jobs/store.py` | Persistent job storage | 100+ |
| `clean/pipeline.py` | Text normalization | 80+ |
| `crawl/pipeline.py` | HTML extraction | 80+ |
| `datasets/registry.py` | Dataset management | 100+ |
| `config.py` | Configuration system | 251 |
| `ui/src/routes.tsx` | Frontend routing | 27 |
| `ui/src/pages/compose.tsx` | Main compose page | 100+ |
| `ui/src/api/client-v2.ts` | API client | 100+ |
| `ui/electron-main.cjs` | Electron entry | 33 |

---

## 10. Development Commands

```bash
# Backend
python -m sagemtl --help                 # CLI help
python -m sagemtl serve                  # Start FastAPI server
uvicorn sagemtl.serve.api_v2:app         # Direct Uvicorn

# Frontend
cd ui
npm run dev                              # Vite dev server
npm run build                            # Build for production
npm run electron:dev                     # Electron + Vite dev

# Tests
pytest                                   # Run all tests
pytest tests/test_api.py                 # Specific test

# Configuration
$EDITOR ~/.sagemtl/config.toml           # Edit config
```

---

## 11. Architecture Strengths

1. **Clear Separation of Concerns:** Backend/frontend well-isolated
2. **Modular Router Design:** Easy to add new API endpoints
3. **Persistent Job Storage:** Jobs survive restarts
4. **WebSocket Real-time Updates:** No polling required (optional)
5. **Configurable Glossary:** Pre/post-translation flexibility
6. **Multi-format Dataset Support:** TXT, CSV, JSONL, JSON, EPUB
7. **Pluggable Translation Providers:** Easy to add new backends
8. **Type Safety:** Full TypeScript + Pydantic validation
9. **Responsive UI:** Works on desktop & mobile
10. **Cross-platform Desktop:** Electron wrapper

