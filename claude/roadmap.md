# SageMTL Modernization Roadmap

## Overview

This roadmap outlines the phased development plan for modernizing SageMTL from its current state to a fully-featured, modern desktop application. Each phase builds upon the previous, ensuring incremental progress with testable milestones.

---

## Phase 0: Foundation & Assessment
**Goal**: Establish development infrastructure and validate existing functionality

### 0.1 Environment Setup
- [ ] Verify Python 3.11+ environment
- [ ] Install all dependencies from `requirements-desktop.txt`
- [ ] Run existing test suite to establish baseline
- [ ] Document any failing tests or missing functionality

### 0.2 Codebase Audit
- [ ] Review all existing modules for compatibility
- [ ] Identify deprecated patterns or libraries
- [ ] Map inter-module dependencies
- [ ] Create integration test coverage report

### 0.3 Development Tooling
- [ ] Configure pre-commit hooks (ruff, mypy)
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Configure test coverage reporting
- [ ] Establish code review guidelines

### Deliverables
- Working development environment
- Baseline test coverage metrics
- Dependency audit report
- CI/CD pipeline configuration

---

## Phase 1: Crawler Module Enhancement
**Goal**: Build a robust, modular crawler with multi-source support

### 1.1 Crawler Core Architecture
- [ ] Refactor `SageCrawler` to use async context managers
- [ ] Implement standardized `AdapterBase` protocol
- [ ] Create adapter registry with auto-discovery
- [ ] Add rate limiting and retry logic with exponential backoff

### 1.2 HTTP Client Enhancement
- [ ] Upgrade `fetch_httpx.py` with connection pooling
- [ ] Add request/response logging
- [ ] Implement robots.txt parsing and respect
- [ ] Add User-Agent rotation capability

### 1.3 Site Adapter Implementation
Priority sites (in order):
1. [ ] **FanMTL** - Complete existing adapter
2. [ ] **Wuxiaworld** - Major translation site
3. [ ] **Webnovel** - QiDian English
4. [ ] **NovelUpdates** - Aggregator with links
5. [ ] **RoyalRoad** - Original English fiction
6. [ ] **Scribble Hub** - Fan fiction
7. [ ] **LNMTL** - Raw MTL source

### 1.4 TOC & Volume Detection
- [ ] Implement multi-pattern TOC parsing
- [ ] Add volume/arc grouping detection
- [ ] Support nested chapter structures
- [ ] Handle paginated TOC pages

### 1.5 Content Extraction
- [ ] Enhance HTML-to-text extraction
- [ ] Remove ads, navigation, comments
- [ ] Preserve formatting (italics, bold, breaks)
- [ ] Extract and cache cover images

### 1.6 Playwright Integration (JS Sites)
- [ ] Add optional Playwright dependency
- [ ] Create JS-rendering adapter base class
- [ ] Implement Cloudflare bypass capability
- [ ] Add headless browser pool management

### 1.7 Job Queue & Resumption
- [ ] Implement chapter-level progress tracking
- [ ] Add job serialization for persistence
- [ ] Support pause/resume functionality
- [ ] Create manifest file for partial downloads

### Deliverables
- 7+ site adapters working
- Async crawler with connection pooling
- Job persistence and resumption
- Integration tests for each adapter

### Testing Milestones
```bash
pytest tests/test_crawl_integration.py -v
# Expected: All adapter tests pass
# Coverage: >80% for sagemtl_crawler/
```

---

## Phase 2: Translation Pipeline
**Goal**: Implement multi-provider translation with glossary support

### 2.1 Provider Architecture
- [ ] Define `TranslationProvider` protocol in `sagemtl/translate/providers.py`
- [ ] Implement provider factory/registry pattern
- [ ] Add async batch translation support
- [ ] Create provider health check mechanism

### 2.2 Argos Translate Enhancement
- [ ] Improve model discovery and installation
- [ ] Add batch translation with chunking
- [ ] Implement memory-efficient processing
- [ ] Add translation quality scoring (optional)

### 2.3 Google Cloud Translation Integration
- [ ] Implement `GoogleTranslateProvider`
- [ ] Add API key configuration
- [ ] Support glossary upload to Google API
- [ ] Implement quota tracking and warnings

### 2.4 DeepL Integration
- [ ] Implement `DeepLProvider`
- [ ] Add API key configuration
- [ ] Support DeepL glossary (Pro only)
- [ ] Handle rate limiting

### 2.5 Microsoft Azure Translator Integration
- [ ] Implement `AzureTranslateProvider`
- [ ] Add subscription key configuration
- [ ] Support custom terminology
- [ ] Implement batch request optimization

### 2.6 Glossary System Enhancement
- [ ] Migrate to SQLite-based glossary storage
- [ ] Implement glossary versioning
- [ ] Add import from LNMTL/Fandom formats
- [ ] Create glossary export (CSV, JSON)
- [ ] Add term frequency analysis
- [ ] Implement fuzzy matching option

### 2.7 Glossary Auto-Generation
- [ ] Implement proper noun detection (NER)
- [ ] Add frequency-based term extraction
- [ ] Integrate existing glossary databases
- [ ] Create confidence scoring for suggestions

### 2.8 Pre/Post Processing Pipeline
- [ ] Implement pre-translation term protection
- [ ] Add post-translation term correction
- [ ] Create pronoun consistency checker
- [ ] Add paragraph join/split normalization

### 2.9 Real-Time vs Batch Modes
- [ ] Implement chapter-by-chapter streaming
- [ ] Add full-novel batch translation
- [ ] Create progress estimation
- [ ] Support translation priority queue

### Deliverables
- 4 translation providers (Argos, Google, DeepL, Azure)
- SQLite glossary database
- Auto-generation with suggestions
- Import/export functionality

### Testing Milestones
```bash
pytest tests/test_translation_pipeline.py -v
# Expected: All provider tests pass
# Coverage: >85% for sagemtl/translate/
```

---

## Phase 3: UI Modernization
**Goal**: Create a modern, themeable desktop interface

### 3.1 Framework Decision
**Recommended**: PySide6 with QML (Qt Quick)
- [ ] Evaluate QML vs PyQt-Fluent-Widgets
- [ ] Create proof-of-concept with chosen framework
- [ ] Document framework decision rationale

### 3.2 Design System
- [ ] Define color palette (light/dark themes)
- [ ] Create typography scale
- [ ] Design icon set (use Fluent UI icons)
- [ ] Establish spacing and sizing constants

### 3.3 Theme Engine
- [ ] Implement theme manager class
- [ ] Add light theme (default)
- [ ] Add dark theme
- [ ] Support system theme detection
- [ ] Add theme persistence

### 3.4 Custom Title Bar
- [ ] Remove native title bar
- [ ] Implement custom draggable title bar
- [ ] Add minimize/maximize/close buttons
- [ ] Support window snapping (Windows)
- [ ] Add macOS traffic light integration

### 3.5 Navigation System
- [ ] Implement sidebar navigation (Fluent-style)
- [ ] Add icons for each section
- [ ] Support collapsed/expanded states
- [ ] Add keyboard navigation

### 3.6 Main Views
- [ ] **Library View**: Grid/list of novels with covers
- [ ] **Download View**: URL input, search, job queue
- [ ] **Translation View**: Source/target comparison
- [ ] **Glossary View**: Term editor with filtering
- [ ] **Settings View**: Organized preference panels

### 3.7 Glassmorphism Effects (Optional)
- [ ] Implement backdrop blur for panels
- [ ] Add acrylic material effect (Windows)
- [ ] Support vibrancy (macOS)
- [ ] Provide fallback for unsupported systems

### 3.8 Dockable Panels
- [ ] Implement panel docking system
- [ ] Support drag-and-drop rearrangement
- [ ] Add panel save/restore layouts
- [ ] Create default layout presets

### 3.9 Batch Configuration UI
- [ ] Multi-URL input dialog
- [ ] Batch settings editor (formats, translation)
- [ ] Queue management interface
- [ ] Bulk operations (select all, remove)

### 3.10 Progress & Notifications
- [ ] Implement toast notification system
- [ ] Add system tray icon with progress
- [ ] Create download/translation progress bars
- [ ] Support background operation notifications

### 3.11 Accessibility
- [ ] Add keyboard shortcuts for all actions
- [ ] Implement screen reader support
- [ ] Ensure color contrast compliance
- [ ] Add focus indicators

### Deliverables
- Modern themed UI (light/dark)
- Custom title bar
- Sidebar navigation
- Dockable panels
- Batch configuration dialogs

### Testing Milestones
```bash
# Manual UI testing checklist
- [ ] Theme switching works
- [ ] All navigation items functional
- [ ] Drag-and-drop panels work
- [ ] Keyboard navigation complete
```

---

## Phase 4: Output System
**Goal**: Support 15+ export formats with full metadata

### 4.1 Output Architecture
- [ ] Define `Exporter` protocol
- [ ] Implement exporter registry
- [ ] Create format detection from extension
- [ ] Add format capability flags (cover, TOC, etc.)

### 4.2 Core Format Implementations
- [ ] **TXT**: Plain text with chapter headers
- [ ] **EPUB**: Full metadata, TOC, cover (ebooklib)
- [ ] **PDF**: HTML→PDF with bookmarks (WeasyPrint)
- [ ] **HTML**: Single-page bundled format

### 4.3 Extended Format Implementations
- [ ] **DOCX**: python-docx with styles
- [ ] **Markdown**: GFM compatible
- [ ] **JSON**: Structured data export
- [ ] **RTF**: Legacy word processor format

### 4.4 Calibre Integration (Optional Formats)
- [ ] Detect Calibre installation
- [ ] Implement `ebook-convert` wrapper
- [ ] **MOBI**: Kindle legacy format
- [ ] **AZW3**: Kindle KF8 format
- [ ] **FB2**: FictionBook format
- [ ] **LRF**: Sony Reader format

### 4.5 Metadata & Cover Handling
- [ ] Implement cover image downloading
- [ ] Add cover embedding to EPUB/PDF
- [ ] Create fallback cover generation
- [ ] Support author/series metadata

### 4.6 Table of Contents
- [ ] Generate TOC from chapter structure
- [ ] Support multi-level TOC (volumes)
- [ ] Embed navigation in EPUB
- [ ] Create PDF bookmarks

### 4.7 Volume Handling
- [ ] Support volume-wise export
- [ ] Add volume title pages
- [ ] Implement page breaks between volumes
- [ ] Option for single file vs. per-volume files

### 4.8 Global/Per-Job Format Selection
- [ ] Add global default format settings
- [ ] Implement per-job format override
- [ ] Create format preset system
- [ ] Add format recommendation based on use case

### 4.9 Interim Storage
- [ ] Store chapters as HTML files
- [ ] Create manifest with chapter metadata
- [ ] Support regeneration without re-download
- [ ] Add cleanup options

### Deliverables
- 15+ export formats
- Full TOC and metadata support
- Volume-wise export option
- Global and per-job settings

### Testing Milestones
```bash
pytest tests/test_exporters.py -v
# Expected: All format tests pass
# Validation: Open exported files in readers
```

---

## Phase 5: Integration & Polish
**Goal**: Full end-to-end workflow with quality-of-life features

### 5.1 End-to-End Pipeline
- [ ] Integrate crawler → translation → export flow
- [ ] Add one-click "Download & Translate" action
- [ ] Implement automatic format export on completion
- [ ] Create pipeline configuration presets

### 5.2 Library Management
- [ ] Add novel library database (SQLite)
- [ ] Implement series grouping
- [ ] Add reading progress tracking
- [ ] Create metadata editor

### 5.3 Search & Discovery
- [ ] Implement multi-site search
- [ ] Add search result aggregation
- [ ] Create search history
- [ ] Support search filters (genre, status)

### 5.4 Settings & Preferences
- [ ] Create comprehensive settings UI
- [ ] Add import/export settings
- [ ] Implement settings sync (optional)
- [ ] Add first-run setup wizard

### 5.5 Performance Optimization
- [ ] Profile CPU/memory usage
- [ ] Optimize large novel handling
- [ ] Add lazy loading for UI lists
- [ ] Implement caching strategies

### 5.6 Error Handling
- [ ] Create user-friendly error messages
- [ ] Add error recovery suggestions
- [ ] Implement automatic retry logic
- [ ] Create error reporting (optional)

### 5.7 Documentation
- [ ] Write user manual
- [ ] Create video tutorials
- [ ] Document API for extensions
- [ ] Add in-app help tooltips

### 5.8 Packaging & Distribution
- [ ] Create Windows installer (NSIS/WiX)
- [ ] Create macOS DMG
- [ ] Create Linux AppImage
- [ ] Set up auto-update mechanism

### Deliverables
- Complete end-to-end workflow
- Library management system
- Comprehensive documentation
- Platform installers

---

## Phase 6: Advanced Features (Future)
**Goal**: Advanced capabilities for power users

### 6.1 Plugin System
- [ ] Define plugin API
- [ ] Create plugin loader
- [ ] Add plugin marketplace UI
- [ ] Document plugin development

### 6.2 Web Interface
- [ ] Implement FastAPI backend
- [ ] Create React/Vue frontend
- [ ] Add remote access capability
- [ ] Support mobile-responsive design

### 6.3 Cloud Sync
- [ ] Add cloud storage integration (optional)
- [ ] Sync library across devices
- [ ] Share glossaries

### 6.4 AI Enhancements
- [ ] Add LLM-based translation polishing
- [ ] Implement AI glossary suggestions
- [ ] Create smart chapter detection

---

## Success Metrics

### Phase Completion Criteria

| Phase | Tests Pass | Coverage | Features Complete |
|-------|------------|----------|-------------------|
| 0 | Baseline | - | 100% |
| 1 | >95% | >80% | 7+ adapters |
| 2 | >95% | >85% | 4 providers |
| 3 | Manual ✓ | N/A | All views |
| 4 | >95% | >80% | 15+ formats |
| 5 | >95% | >85% | Full pipeline |

### Performance Targets
- Startup time: <3 seconds
- Chapter download: <500ms each (excluding network)
- Translation: >1000 chars/second (Argos)
- Export generation: <10 seconds for 1000-chapter novel

### Quality Targets
- Zero critical bugs at release
- All UI accessible via keyboard
- Light/dark themes fully functional
- Cross-platform consistency (Windows/macOS/Linux)

---

## Dependencies Between Phases

```
Phase 0 (Foundation)
    │
    ▼
Phase 1 (Crawler) ───────┐
    │                    │
    ▼                    │
Phase 2 (Translation) ◄──┘
    │
    ▼
Phase 3 (UI) ◄─────────────┐
    │                      │
    ▼                      │
Phase 4 (Output) ◄─────────┤
    │                      │
    ▼                      │
Phase 5 (Integration) ◄────┘
    │
    ▼
Phase 6 (Advanced) [Future]
```

**Note**: Phases 1-4 can be partially parallelized:
- Phase 1 & 2 are independent (can develop simultaneously)
- Phase 3 can start once basic models from Phase 1 & 2 exist
- Phase 4 depends on data structures from Phase 1

---

## Risk Mitigation

### Technical Risks
| Risk | Mitigation |
|------|------------|
| Site structure changes | Adapter versioning, community updates |
| API deprecation | Multiple provider options, offline default |
| Qt version issues | Pin PySide6 version, test upgrades |
| Performance with large novels | Lazy loading, chunked processing |

### Resource Risks
| Risk | Mitigation |
|------|------------|
| Development time | Prioritize MVP features |
| Testing coverage | Automated CI/CD pipeline |
| User adoption | Clear documentation, tutorials |

---

## Version Milestones

| Version | Phase | Key Features |
|---------|-------|--------------|
| 0.1.0 | 0 | Foundation complete |
| 0.2.0 | 1 | Crawler working (5 sites) |
| 0.3.0 | 2 | Translation pipeline complete |
| 0.4.0 | 3 | Modern UI (basic) |
| 0.5.0 | 4 | Output formats complete |
| 1.0.0 | 5 | Full release |
| 2.0.0 | 6 | Advanced features |
