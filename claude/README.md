# SageMTL - Machine Translation Desktop Application

## Overview

**SageMTL** is a Python-based desktop application for downloading, machine-translating, and exporting web novels. It provides an end-to-end pipeline from web content acquisition to polished e-book output, with a focus on offline operation and user customization.

### Core Value Proposition
- **Download**: Fetch light novels from 460+ supported websites via modular crawlers
- **Translate**: Convert foreign-language novels to English using offline MT (Argos) or cloud APIs
- **Export**: Generate professional e-book formats (EPUB, PDF, TXT, DOCX, MOBI)
- **Customize**: Maintain consistent terminology via per-novel glossaries

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SageMTL Application                          │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  sagemtl (core) │  │ sagemtl_crawler │  │  sagemtl_desktop    │  │
│  │  ~3,300 LOC     │  │  ~1,400 LOC     │  │  ~4,300 LOC         │  │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────────┤  │
│  │ • CLI (Typer)   │  │ • Crawler Engine│  │ • PySide6 UI        │  │
│  │ • Config (TOML) │  │ • Site Adapters │  │ • Job Manager       │  │
│  │ • Text Cleaning │  │ • Exporters     │  │ • Translator        │  │
│  │ • Glossary      │  │ • Data Models   │  │ • Import/Export     │  │
│  │ • SageCrawler   │  │ • HTTP Fetcher  │  │ • Glossary Editor   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Package Breakdown

| Package | Purpose | Key Modules |
|---------|---------|-------------|
| `sagemtl` | Core library (reusable) | CLI, config, cleaning, glossary, SageCrawler |
| `sagemtl_crawler` | Advanced crawler engine | Site adapters, exporters, async fetching |
| `sagemtl_desktop` | Desktop GUI application | PySide6 UI, job management, Argos integration |

---

## Module Deep-Dive

### 1. Crawler System

#### Architecture
```
                    ┌──────────────────────┐
                    │   CrawlerInterface   │  ← Protocol/Abstract
                    │  (fetch_novel)       │
                    └──────────┬───────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
┌──────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│  SageCrawler     │ │ LNCrawl Wrapper │ │  Future: Playwright │
│  (Built-in)      │ │  (455+ sites)   │ │  (JS-rendered)      │
└──────────────────┘ └─────────────────┘ └─────────────────────┘
```

#### SageCrawler (Built-in)
- **Location**: `sagemtl/crawl/novel_crawler.py`
- **Strategy**: Pattern-based URL detection (no site-specific code)
- **Patterns Detected**: `chapter-{num}`, `/{num}/`, `/ch{num}.html`
- **HTTP Client**: httpx (async, HTTP/2, connection pooling)
- **Parser**: BeautifulSoup4 + lxml

#### LightNovel-Crawler Integration (Optional)
- **Location**: `sagemtl_desktop/core/lightnovel_crawler_wrapper.py`
- **License**: GPL v3 (optional dependency)
- **Sites Supported**: 455+ (Wuxiaworld, Webnovel, FanMTL, etc.)
- **Integration**: Thread pool execution, temp directory I/O

#### Site Adapter System
- **Location**: `sagemtl_crawler/sites/`
- **Protocol**: `AdapterBase` in `sagemtl_crawler/core/adapter_base.py`
- **Current Adapters**: FanMTL only
- **Extensibility**: Add new adapters by implementing the protocol

### 2. Translation Pipeline

#### Architecture
```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Raw Text   │ ──► │  Pre-Processing  │ ──► │  Translation    │
│  (Foreign)  │     │  • Cleaning      │     │  • Argos (local)│
└─────────────┘     │  • Glossary Pre  │     │  • Google API   │
                    └──────────────────┘     │  • DeepL API    │
                                             └────────┬────────┘
                                                      │
                    ┌──────────────────┐              │
                    │  Post-Processing │ ◄────────────┘
                    │  • Glossary Post │
                    │  • Formatting    │
                    └────────┬─────────┘
                             ▼
                    ┌─────────────────┐
                    │  Clean English  │
                    └─────────────────┘
```

#### Translation Providers
| Provider | Type | Cost | Quality | Glossary Support |
|----------|------|------|---------|------------------|
| Argos Translate | Offline | Free | Good | Pre/Post |
| Google Cloud | Online | $20/1M chars | Excellent | Native API |
| DeepL | Online | ~€20/mo | Excellent | Pro only |
| Microsoft Azure | Online | $10/1M chars | Very Good | Yes |

#### Glossary System
- **Location**: `sagemtl/translate/glossary.py`
- **Format**: CSV (`source,target`) or JSON
- **Features**:
  - Case-sensitive/insensitive matching
  - Word boundary detection
  - Pre-translation replacement (protect terms)
  - Post-translation correction
- **Per-Novel Storage**: Each novel maintains its own glossary DB

### 3. Desktop UI

#### Framework: PySide6 (Qt6 for Python)

#### Component Hierarchy
```
MainWindow (733 LOC)
├── ControlsPanel (282 LOC)
│   ├── Import Button
│   ├── Fetch URL Button
│   ├── Translate Button
│   ├── Export Button
│   └── Language Selectors
├── FileListPanel (189 LOC)
│   └── Novel/File Browser
├── PreviewPanel (101 LOC)
│   └── Side-by-side Original/Translated
├── LogPanel (166 LOC)
│   └── Real-time Log Viewer
└── ExportDialog (93 LOC)
    └── Format Selection (TXT, EPUB, MD)
```

#### Signal Flow Pattern
```
User Action → ControlsPanel Signal → MainWindow Slot → JobManager.create_job()
                                                               │
JobWorker (QThread) ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
       │
       ├── progress_updated Signal ──► LogPanel Update
       ├── log_message Signal ────────► LogPanel Append
       └── job_completed Signal ──────► FileListPanel Refresh
```

### 4. Output System

#### Supported Formats
| Format | Library | Status | Notes |
|--------|---------|--------|-------|
| TXT | Native | ✓ Default | UTF-8, configurable line endings |
| EPUB | ebooklib | ✓ Default | Full metadata, TOC, cover support |
| PDF | WeasyPrint | ✓ Default | HTML→PDF, bookmarks |
| DOCX | python-docx | ○ Optional | Structured headings |
| MOBI | Calibre CLI | ○ Optional | Via ebook-convert |
| AZW3 | Calibre CLI | ○ Optional | Kindle format |
| HTML | Native | ○ Optional | Single-page bundle |
| JSON | Native | ○ Optional | Structured data export |
| Markdown | Native | ○ Optional | Plain text with headers |

#### Output Directory Structure
```
Documents/
└── lightnovels/
    └── {Novel Name}/
        ├── {Novel Name}.epub
        ├── {Novel Name}.pdf
        ├── {Novel Name}.txt
        └── chapters/           # Interim storage
            ├── 001.html
            ├── 002.html
            └── ...
```

---

## Technology Stack

### Core Dependencies
```toml
[dependencies]
python = ">=3.11"
typer = ">=0.12"              # CLI framework
pydantic = ">=2.6"            # Data validation
beautifulsoup4 = ">=4.12"     # HTML parsing
httpx = ">=0.25"              # Async HTTP (HTTP/2)
lxml = ">=5.3"                # XML/HTML parsing
```

### Desktop Dependencies
```toml
PySide6 = "6.10.0"            # Qt6 GUI framework
argostranslate = "1.10.0"     # Offline translation
ebooklib = "0.20"             # EPUB creation
lightnovel-crawler = "3.10.1" # Optional: 455+ sites
```

### Development Tools
```toml
pytest = ">=8.0"              # Testing
pyinstaller = "6.16.0"        # Executable packaging
ruff = ">=0.1"                # Linting
```

---

## Configuration System

### Config File: `~/.sagemtl/config.toml`
```toml
[general]
newline_mode = "lf"           # lf | crlf | system | preserve
thread_count = 8              # Parallel processing threads

[crawler]
default_engine = "sage"       # sage | lncrawl
request_delay = 0.5           # Seconds between requests
user_agent = "SageMTL/1.0"

[translation]
default_provider = "argos"    # argos | google | deepl
source_language = "zh"        # Chinese
target_language = "en"        # English
chunk_size = 4000             # Characters per translation call

[output]
default_formats = ["epub", "pdf", "txt"]
output_directory = "~/Documents/lightnovels"
```

### Environment Variable Overrides
```bash
SAGEMTL_THREAD_COUNT=16
SAGEMTL_GOOGLE_API_KEY=your_key_here
SAGEMTL_DEEPL_API_KEY=your_key_here
```

---

## Data Models

### Job Model
```python
@dataclass
class Job:
    job_id: str                           # UUID
    job_type: JobType                     # IMPORT | CRAWL | TRANSLATE | EXPORT
    status: JobStatus                     # PENDING | IN_PROGRESS | COMPLETED | FAILED
    name: str                             # Display name
    original_text: str = ""               # Source content
    cleaned_text: str = ""                # Processed content
    progress: float = 0.0                 # 0-100%
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}         # Novel metadata, etc.
```

### Novel/Chapter Models
```python
@dataclass
class CrawledNovel:
    title: str
    author: Optional[str]
    cover_url: Optional[str]
    chapters: List[CrawledChapter]
    volumes: List[Volume]
    metadata: Dict[str, Any]

@dataclass
class CrawledChapter:
    title: str
    url: str
    content: str
    chapter_number: int
    volume_number: Optional[int]
```

### Glossary Entry Model
```python
@dataclass
class GlossaryEntry:
    source_term: str          # Original term (e.g., "灵石")
    target_term: str          # Translation (e.g., "Spirit Stone")
    term_type: str            # character | item | location | technique
    notes: Optional[str]      # Usage notes
    case_sensitive: bool = True
```

---

## Directory Structure

```
sagemtl/
├── sagemtl/                    # Core library
│   ├── __init__.py
│   ├── __main__.py             # Module entry point
│   ├── cli.py                  # Typer CLI (445 LOC)
│   ├── config.py               # Configuration manager (251 LOC)
│   ├── batch/                  # Batch processing
│   ├── clean/                  # Text normalization
│   │   ├── normalize.py
│   │   └── extract.py
│   ├── crawl/                  # SageCrawler
│   │   └── novel_crawler.py
│   ├── datasets/               # Dataset registry
│   ├── jobs/                   # Job state storage
│   ├── mtl/                    # MT providers (stub)
│   ├── translate/              # Translation pipeline
│   │   ├── providers.py        # Provider protocols
│   │   └── glossary.py         # Glossary processing
│   └── tui/                    # Terminal UI (Textual)
│
├── sagemtl_crawler/            # Advanced crawler engine
│   ├── __init__.py
│   ├── core/
│   │   ├── adapter_base.py     # Site adapter protocol
│   │   ├── engine.py           # Crawl orchestrator
│   │   ├── models.py           # Data models
│   │   ├── cleaners.py         # Content cleaning
│   │   └── fetch_httpx.py      # Polite HTTP fetcher
│   ├── exporters/
│   │   ├── json_exporter.py
│   │   ├── epub_exporter.py
│   │   ├── html_exporter.py
│   │   └── txt_exporter.py
│   └── sites/                  # Site adapters
│       └── fanmtl.py           # FanMTL adapter
│
├── sagemtl_desktop/            # Desktop application
│   ├── __init__.py
│   ├── main.py                 # App entry point
│   ├── core/                   # Business logic (no UI imports)
│   │   ├── models.py           # Job, ProcessingOptions
│   │   ├── job_manager.py      # QThread job queue
│   │   ├── translator.py       # Argos wrapper
│   │   ├── glossary.py         # CSV glossary
│   │   ├── crawler_interface.py
│   │   ├── sage_crawler_wrapper.py
│   │   ├── lightnovel_crawler_wrapper.py
│   │   ├── epub_extractor.py
│   │   ├── epub_writer.py
│   │   ├── exporter.py
│   │   ├── import_manager.py
│   │   └── structured_logger.py
│   ├── ui/                     # PySide6 components
│   │   ├── main_window.py
│   │   ├── controls_panel.py
│   │   ├── file_list_panel.py
│   │   ├── preview_panel.py
│   │   ├── log_panel.py
│   │   ├── export_dialog.py
│   │   └── dialogs.py
│   └── resources/              # Assets
│
├── tests/                      # Pytest suite
├── claude/                     # Claude Code prompts (this directory)
├── pyproject.toml              # Build configuration
├── requirements-desktop.txt    # Desktop dependencies
└── pyinstaller-desktop.spec    # Executable build config
```

---

## Key Design Patterns

### 1. Protocol-Based Abstractions
All major components use Python Protocols for loose coupling:
- `CrawlerInterface` → SageCrawler, LNCrawl
- `TranslationProvider` → Argos, Google, DeepL
- `Exporter` → EPUB, PDF, TXT, etc.

### 2. Signal-Slot (Qt Pattern)
UI is completely decoupled from business logic:
```python
# In core/ - no PySide6 imports
class JobManager:
    progress_updated = Signal(str, float)  # job_id, progress

# In ui/ - connects to core signals
self.job_manager.progress_updated.connect(self.on_progress)
```

### 3. Background Threading
All heavy operations run in QThread workers:
- Network I/O (crawling)
- Translation (Argos model inference)
- File I/O (export generation)

### 4. Configuration as Code
Pydantic models ensure type safety:
```python
class Settings(BaseModel):
    thread_count: int = Field(default=8, ge=1, le=64)
    newline_mode: Literal["lf", "crlf", "system"] = "lf"
```

---

## Build & Distribution

### Development Setup
```bash
# Clone and setup
git clone https://github.com/Blood-Dawn/sagemtl.git
cd sagemtl
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in dev mode
pip install -e ".[dev]"
pip install -r requirements-desktop.txt
```

### Running the App
```bash
# Desktop GUI
python -m sagemtl_desktop

# CLI
python -m sagemtl --help
```

### Building Executable
```bash
# Windows executable
pyinstaller pyinstaller-desktop.spec

# Output: dist/SageMTL.exe
```

---

## Modernization Goals (This Document Set)

The `/claude/` directory contains specifications for modernizing SageMTL:

1. **README.md** (this file): Architecture overview and context
2. **roadmap.md**: Phased development plan from MVP to full features
3. **prompt.txt**: Autonomous execution prompt for Claude Code
4. **specs/**: Detailed module specifications
   - `crawler_spec.md`: Internal Python crawler requirements
   - `translation_spec.md`: Translation pipeline requirements
   - `ui_spec.md`: UI modernization requirements
   - `output_spec.md`: Output handling requirements

---

## References

### External Documentation
- [Argos Translate](https://github.com/argosopentech/argos-translate)
- [LightNovel-Crawler](https://github.com/dipu-bd/lightnovel-crawler)
- [PySide6 Documentation](https://doc.qt.io/qtforpython-6/)
- [ebooklib](https://github.com/aerkalov/ebooklib)
- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)

### Internal References
- `pyproject.toml`: All dependency versions
- `config.toml.example`: Configuration template
- `tests/`: Test suite for validation
