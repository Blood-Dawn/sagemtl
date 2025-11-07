# SageMTL Codebase Documentation Index

**Generated:** November 7, 2025

This directory contains comprehensive documentation of the SageMTL codebase, created through systematic exploration of all major components.

## Documentation Files

### 1. CODEBASE_EXPLORATION_SUMMARY.md (346 lines)
**Quick overview of the entire system**
- Executive summary
- Architecture overview
- Critical systems explained
- API architecture
- Frontend architecture
- Key features summary
- Configuration system
- Data flow examples
- Testing coverage
- Development quick start
- Architecture highlights with strengths/limitations
- Key takeaways

**Best for:** Getting oriented, understanding big picture

---

### 2. ARCHITECTURE.md (955 lines)
**Detailed technical specification of every component**
- Project structure with directory tree
- Complete backend architecture (11 modules):
  - FastAPI application & 4 routers (300+ lines detailed)
  - Job queue system with data models
  - Translation queue architecture
  - Translation providers
  - Configuration system (251 lines)
  - Text cleaning pipeline
  - Web crawling pipeline
  - Dataset management
  - Glossary system
  - MTL translation backends
- Frontend architecture (React + TypeScript):
  - Project setup & technology stack
  - Routing architecture (7 pages)
  - API client (client-v2.ts)
  - All 7 pages explained with features & state
  - Custom hooks details
  - State management (Zustand)
  - UI components breakdown
- Desktop application (Electron)
- Key data flows (4 workflows)
- Configuration details
- Testing coverage
- Feature summary
- Critical files reference table
- Development commands
- Architecture strengths

**Best for:** Deep understanding, implementation details, extending code

---

### 3. QUICK-REFERENCE.md (346 lines)
**Quick lookup guide for developers**
- Critical file locations (tables):
  - Backend core files
  - Job queue & storage
  - Processing pipelines
  - Data management
  - Frontend pages
  - Frontend infrastructure
- Complete API endpoint map:
  - Compose router
  - Jobs router
  - Datasets router
  - Crawl router
- Key enums & constants
- Data storage locations
- Common development tasks (with commands)
- Architecture decision records (why certain choices)
- Testing coverage summary
- Dependencies summary
- Performance considerations
- Future enhancement points

**Best for:** Quick lookups, finding files, understanding endpoints

---

## Key Statistics

**Codebase Size:**
- 2,380 lines of Python backend
- 3,806 lines of TypeScript frontend
- 14 test files
- 11 backend modules
- 7 frontend pages

**Documentation Created:**
- 1,782 total lines across 3 files
- 51 KB of comprehensive documentation
- Table-based quick reference
- Detailed explanations
- Code flow diagrams

---

## How to Use This Documentation

### For New Developers
1. Start with **CODEBASE_EXPLORATION_SUMMARY.md** (5-10 min read)
2. Then read relevant section in **ARCHITECTURE.md**
3. Use **QUICK-REFERENCE.md** for specific lookups

### For Implementation
1. Find the feature in **QUICK-REFERENCE.md** (file locations)
2. Read detailed explanation in **ARCHITECTURE.md**
3. Check tests in `tests/` directory
4. Reference API endpoints in **QUICK-REFERENCE.md**

### For Debugging
1. Use file location table in **QUICK-REFERENCE.md**
2. Understand data flow in **CODEBASE_EXPLORATION_SUMMARY.md**
3. Check WebSocket/async handling in **ARCHITECTURE.md**

### For Enhancement
1. Review "Future Enhancement Points" in **QUICK-REFERENCE.md**
2. Check "Architecture Strengths/Limitations" in **CODEBASE_EXPLORATION_SUMMARY.md**
3. Use **ARCHITECTURE.md** for detailed implementation guidance

---

## Critical Concepts

### Job Queue System
- Persistent JSON storage (`~/.sagemtl/jobs.json`)
- Single daemon thread processes sequentially
- Thread-safe with file locking
- Non-blocking enqueue returns immediately
- See **ARCHITECTURE.md** Section 2.2 for details

### Translation Pipeline
- Clean → Translate → Glossary flow
- WebSocket real-time updates
- Pluggable providers
- Pre/post glossary application
- See **ARCHITECTURE.md** Sections 2.3-2.5

### Dataset Management
- Multi-format support (JSONL, CSV, TXT, HTML, JSON, EPUB)
- Auto-format detection
- Storage at `~/.sagemtl/data/{dataset_name}/`
- Per-dataset metadata
- See **ARCHITECTURE.md** Section 2.8

### Web Crawling
- BeautifulSoup-based HTML parsing
- Boilerplate removal
- Selector-based filtering
- Language detection per block
- Chapter extraction for novels
- See **ARCHITECTURE.md** Section 2.7

---

## File Organization

```
SageMTL Root/
├── DOCUMENTATION_INDEX.md       ← You are here
├── CODEBASE_EXPLORATION_SUMMARY.md  (overview)
├── ARCHITECTURE.md              (detailed)
├── QUICK-REFERENCE.md          (lookup)
├── sagemtl/                     (backend Python)
│   ├── serve/                   (FastAPI app)
│   ├── jobs/                    (queue & storage)
│   ├── translate/               (translation)
│   ├── clean/                   (text cleaning)
│   ├── crawl/                   (web crawling)
│   ├── datasets/                (dataset management)
│   ├── config.py                (configuration)
│   └── ... (7 more modules)
├── ui/                          (frontend React)
│   ├── src/
│   │   ├── pages/              (7 pages)
│   │   ├── components/         (UI components)
│   │   ├── api/                (API client)
│   │   ├── hooks/              (custom hooks)
│   │   └── state/              (Zustand store)
│   └── electron-main.cjs        (Electron)
├── tests/                       (14 test files)
└── docs/                        (existing docs)
```

---

## Technology Stack Summary

### Backend
- Python 3.11+
- FastAPI (REST API)
- Pydantic (validation)
- BeautifulSoup4 (HTML parsing)
- Typer (CLI)
- Textual (Terminal UI)
- Threading (job queue)
- TOML (configuration)

### Frontend
- React 19
- TypeScript 5.9
- Vite 7 (build tool)
- Electron 39 (desktop)
- Radix UI (components)
- TailwindCSS (styling)
- Zustand (state)
- React Router v7 (routing)

---

## Getting Started Commands

```bash
# View documentation
cat /home/user/sagemtl/CODEBASE_EXPLORATION_SUMMARY.md

# View architecture details
cat /home/user/sagemtl/ARCHITECTURE.md | less

# View quick reference
cat /home/user/sagemtl/QUICK-REFERENCE.md

# Start backend
python -m sagemtl serve

# Start frontend
cd /home/user/sagemtl/ui && npm run dev

# Run tests
cd /home/user/sagemtl && pytest
```

---

## Quick Links to Key Sections

### API Endpoints
- Compose: **QUICK-REFERENCE.md** → API Endpoint Map
- Jobs: **QUICK-REFERENCE.md** → Jobs Router
- Datasets: **QUICK-REFERENCE.md** → Datasets Router
- Crawl: **QUICK-REFERENCE.md** → Crawl Router

### Backend Components
- Job Queue: **ARCHITECTURE.md** → Section 2.2-2.3
- Translation: **ARCHITECTURE.md** → Section 2.3-2.5
- Cleaning: **ARCHITECTURE.md** → Section 2.6
- Crawling: **ARCHITECTURE.md** → Section 2.7
- Configuration: **ARCHITECTURE.md** → Section 2.5

### Frontend Pages
- All pages detailed: **ARCHITECTURE.md** → Section 3.4
- Page locations: **QUICK-REFERENCE.md** → Frontend Pages
- API client: **ARCHITECTURE.md** → Section 3.3

### Data Flows
- Translation: **CODEBASE_EXPLORATION_SUMMARY.md** → Section 7
- Import: **CODEBASE_EXPLORATION_SUMMARY.md** → Section 7
- Crawl: **CODEBASE_EXPLORATION_SUMMARY.md** → Section 7

---

## Documentation Version

- **Created:** November 7, 2025
- **Branch:** claude/sagemtl-enhance-features-011CUsySwLsBTn5ypSf4apX2
- **Scope:** Complete codebase exploration
- **Status:** Comprehensive, production-ready

---

## Need More Information?

1. **Specific file details?** → Check QUICK-REFERENCE.md file locations
2. **API endpoint format?** → Check QUICK-REFERENCE.md API section
3. **How does feature X work?** → Check ARCHITECTURE.md index
4. **What files to modify?** → Check QUICK-REFERENCE.md critical files
5. **Configuration options?** → Check CODEBASE_EXPLORATION_SUMMARY.md Section 6

---

**Total Documentation:** 1,782 lines | **All files:** Markdown (.md) | **Fully cross-referenced**
