# SageMTL Desktop App Architecture (PySide6)

## Overview
This document describes the complete architecture for the rebuilt sageMTL Windows desktop application using PySide6 (Qt for Python). This replaces the previous web-based architecture.

## Technology Stack
- **Language:** Python 3.11+
- **UI Framework:** PySide6 (Qt6)
- **Translation Engine:** Argos Translate (offline models)
- **Crawler:** lightnovel-crawler (lncrawl) for novel downloading
- **Packaging:** PyInstaller (one-folder mode)
- **Platform:** Windows (primary), cross-platform capable

## Directory Structure

```
sagemtl/
├── sagemtl_desktop/          # New desktop app package
│   ├── __init__.py
│   ├── main.py               # Application entry point
│   │
│   ├── core/                 # Backend logic (no UI dependencies)
│   │   ├── __init__.py
│   │   ├── job_manager.py    # Job queue with threading
│   │   ├── translator.py     # Argos Translate wrapper
│   │   ├── glossary.py       # CSV glossary processor
│   │   ├── crawler.py        # (Removed) legacy SageCrawler wrapper
│   │   ├── epub_extractor.py # EPUB parsing and extraction
│   │   ├── exporter.py       # Export cleaned text
│   │   └── models.py         # Data models (Job, ProcessingOptions, etc.)
│   │
│   ├── ui/                   # PySide6 UI components
│   │   ├── __init__.py
│   │   ├── main_window.py    # Main application window
│   │   ├── file_list_panel.py    # File/novel list widget
│   │   ├── preview_panel.py      # Side-by-side text preview
│   │   ├── controls_panel.py     # Settings and controls
│   │   ├── log_panel.py          # Log viewer with error tracking
│   │   └── dialogs.py            # Dialogs (file picker, settings, etc.)
│   │
│   └── resources/            # Icons, styles, default glossaries
│       ├── icons/
│       ├── styles/
│       └── models/           # Pre-bundled Argos models
│
├── requirements.txt          # Python dependencies
├── requirements-desktop.txt  # Desktop-specific dependencies
├── pyinstaller-desktop.spec  # PyInstaller build configuration
└── README_DESKTOP.md         # Desktop app documentation
```

## Core Modules

### 1. Data Models (`core/models.py`)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime

class JobStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class JobType(Enum):
    IMPORT_FILE = "import_file"
    CRAWL_URL = "crawl_url"
    TRANSLATE = "translate"
    EXPORT = "export"

@dataclass
class Job:
    """Represents a processing job"""
    job_id: str
    job_type: JobType
    status: JobStatus
    name: str  # Filename or novel title
    created_at: datetime
    updated_at: datetime

    # Content
    original_text: str = ""
    cleaned_text: str = ""

    # Progress
    progress: float = 0.0  # 0-100

    # Error tracking
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProcessingOptions:
    """Options for text processing pipeline"""
    source_lang: str = "auto"  # Language code or "auto"
    target_lang: str = "en"    # English by default
    glossary_path: Optional[str] = None

    # Chunking options
    max_chunk_size: int = 500  # Max sentences per chunk

@dataclass
class GlossaryEntry:
    """Single glossary mapping"""
    source: str
    target: str
    case_sensitive: bool = True
    word_boundary: bool = False
```

### 2. Job Manager (`core/job_manager.py`)

**Responsibilities:**
- Manage job queue (create, update, delete)
- Run jobs in background threads
- Emit Qt signals for progress updates
- Handle job lifecycle (pending → running → done/failed)

**Key Classes:**

```python
from PySide6.QtCore import QObject, Signal, QThread, QMutex
from typing import List, Optional, Callable
import uuid
from .models import Job, JobStatus, JobType

class JobWorker(QThread):
    """Worker thread that processes a single job"""
    progress_updated = Signal(str, float)  # job_id, progress
    job_completed = Signal(str)            # job_id
    job_failed = Signal(str, str, str)     # job_id, error_msg, traceback
    log_message = Signal(str, str, str)    # job_id, level, message

    def __init__(self, job: Job, processor: Callable):
        super().__init__()
        self.job = job
        self.processor = processor

    def run(self):
        """Execute job in background thread"""
        try:
            # Call the processor (translator, crawler, etc.)
            self.processor(self.job, self.emit_progress, self.emit_log)
            self.job_completed.emit(self.job.job_id)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.job_failed.emit(self.job.job_id, str(e), tb)

    def emit_progress(self, progress: float):
        self.progress_updated.emit(self.job.job_id, progress)

    def emit_log(self, level: str, message: str):
        self.log_message.emit(self.job.job_id, level, message)

class JobManager(QObject):
    """Manages all jobs and worker threads"""
    job_added = Signal(str)         # job_id
    job_updated = Signal(str)       # job_id
    job_removed = Signal(str)       # job_id
    progress_changed = Signal(str, float)  # job_id, progress
    log_emitted = Signal(str, str, str)    # job_id, level, message

    def __init__(self):
        super().__init__()
        self._jobs: Dict[str, Job] = {}
        self._workers: Dict[str, JobWorker] = {}
        self._mutex = QMutex()

    def create_job(self, job_type: JobType, name: str, **metadata) -> str:
        """Create a new job and return its ID"""
        job = Job(
            job_id=str(uuid.uuid4()),
            job_type=job_type,
            status=JobStatus.PENDING,
            name=name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata
        )

        self._mutex.lock()
        self._jobs[job.job_id] = job
        self._mutex.unlock()

        self.job_added.emit(job.job_id)
        return job.job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> List[Job]:
        """Get all jobs"""
        return list(self._jobs.values())

    def start_job(self, job_id: str, processor: Callable):
        """Start processing a job in background thread"""
        job = self.get_job(job_id)
        if not job:
            return

        job.status = JobStatus.IN_PROGRESS
        job.updated_at = datetime.now()

        worker = JobWorker(job, processor)
        worker.progress_updated.connect(self._on_progress)
        worker.job_completed.connect(self._on_completed)
        worker.job_failed.connect(self._on_failed)
        worker.log_message.connect(self._on_log)

        self._workers[job_id] = worker
        worker.start()

        self.job_updated.emit(job_id)

    def _on_progress(self, job_id: str, progress: float):
        job = self.get_job(job_id)
        if job:
            job.progress = progress
            self.progress_changed.emit(job_id, progress)

    def _on_completed(self, job_id: str):
        job = self.get_job(job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            job.updated_at = datetime.now()
            self.job_updated.emit(job_id)

        # Cleanup worker
        if job_id in self._workers:
            self._workers[job_id].deleteLater()
            del self._workers[job_id]

    def _on_failed(self, job_id: str, error_msg: str, traceback: str):
        job = self.get_job(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = error_msg
            job.error_traceback = traceback
            job.updated_at = datetime.now()
            self.job_updated.emit(job_id)

        # Cleanup worker
        if job_id in self._workers:
            self._workers[job_id].deleteLater()
            del self._workers[job_id]

    def _on_log(self, job_id: str, level: str, message: str):
        self.log_emitted.emit(job_id, level, message)
```

### 3. Translator (`core/translator.py`)

**Responsibilities:**
- Load Argos Translate models
- Translate text in chunks
- Emit progress updates
- Handle language detection

```python
import argostranslate.package
import argostranslate.translate
from typing import Callable, List, Tuple
import re

class Translator:
    """Argos Translate wrapper for offline translation"""

    def __init__(self):
        self.installed_languages = {}
        self._load_installed_languages()

    def _load_installed_languages(self):
        """Load available Argos language packs"""
        argostranslate.package.update_package_index()
        installed = argostranslate.package.get_installed_packages()

        for pkg in installed:
            key = f"{pkg.from_code}→{pkg.to_code}"
            self.installed_languages[key] = pkg

    def get_available_languages(self) -> List[Tuple[str, str]]:
        """Get list of available (source, target) language pairs"""
        return [(pkg.from_code, pkg.to_code)
                for pkg in argostranslate.package.get_installed_packages()]

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        progress_callback: Optional[Callable[[float], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        Translate text from source to target language.

        Args:
            text: Input text
            source_lang: Source language code (e.g., 'zh', 'ja', 'ko')
            target_lang: Target language code (e.g., 'en')
            progress_callback: Function to call with progress (0-100)
            log_callback: Function to call with (level, message)

        Returns:
            Translated text
        """
        if log_callback:
            log_callback("info", f"Starting translation {source_lang}→{target_lang}")

        # Get translation model
        try:
            translation = argostranslate.translate.get_translation_from_codes(
                source_lang, target_lang
            )
        except Exception as e:
            if log_callback:
                log_callback("error", f"Translation model not found: {e}")
            raise ValueError(f"No translation model for {source_lang}→{target_lang}")

        # Split text into chunks (by sentences)
        chunks = self._split_into_sentences(text)
        total_chunks = len(chunks)

        if log_callback:
            log_callback("info", f"Split into {total_chunks} chunks")

        translated_chunks = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                translated_chunks.append(chunk)
                continue

            # Translate chunk
            try:
                translated = translation.translate(chunk)
                translated_chunks.append(translated)
            except Exception as e:
                if log_callback:
                    log_callback("warn", f"Failed to translate chunk {i+1}: {e}")
                translated_chunks.append(chunk)  # Keep original on error

            # Update progress
            if progress_callback:
                progress = ((i + 1) / total_chunks) * 100
                progress_callback(progress)

        result = " ".join(translated_chunks)

        if log_callback:
            log_callback("info", "Translation completed")

        return result

    def _split_into_sentences(self, text: str, max_length: int = 500) -> List[str]:
        """Split text into sentences for chunked processing"""
        # Simple sentence splitting (can be improved)
        sentences = re.split(r'([.!?。！？]\s*)', text)

        # Recombine sentence and punctuation
        chunks = []
        current_chunk = ""

        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]

            if len(current_chunk) + len(sentence) > max_length and current_chunk:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
```

### 4. Glossary Processor (`core/glossary.py`)

**Responsibilities:**
- Load CSV glossary
- Apply before/after translation
- Support case-sensitive and word-boundary matching

```python
import csv
import re
from typing import List, Optional
from pathlib import Path
from .models import GlossaryEntry

class GlossaryProcessor:
    """Processes text using user-provided glossary"""

    def __init__(self):
        self.entries: List[GlossaryEntry] = []
        self.glossary_path: Optional[Path] = None

    def load_glossary(self, path: str):
        """Load glossary from CSV file"""
        self.glossary_path = Path(path)
        self.entries = []

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = GlossaryEntry(
                    source=row['source'],
                    target=row['target'],
                    case_sensitive=row.get('case_sensitive', 'true').lower() == 'true',
                    word_boundary=row.get('word_boundary', 'false').lower() == 'true'
                )
                self.entries.append(entry)

        # Sort by length (longest first) to avoid partial replacements
        self.entries.sort(key=lambda e: len(e.source), reverse=True)

    def apply_before(self, text: str) -> str:
        """Apply glossary before translation"""
        if not self.entries:
            return text

        result = text
        for entry in self.entries:
            result = self._replace_term(result, entry)

        return result

    def apply_after(self, text: str) -> str:
        """Apply glossary after translation"""
        # Same logic for now, but could be different
        return self.apply_before(text)

    def _replace_term(self, text: str, entry: GlossaryEntry) -> str:
        """Replace a single glossary term"""
        flags = 0 if entry.case_sensitive else re.IGNORECASE

        if entry.word_boundary:
            # Use word boundaries
            pattern = r'\b' + re.escape(entry.source) + r'\b'
        else:
            pattern = re.escape(entry.source)

        return re.sub(pattern, entry.target, text, flags=flags)
```

### 5. Crawler (`core/crawler.py`)

**Responsibilities:**
- Use SageCrawler for novel downloading
- Automatic chapter pattern detection
- Extract chapters as text
- Return text to job manager

```python
from sagemtl.crawl.novel_crawler import NovelCrawler

class Crawler:
    """Wrapper for SageCrawler - built-in novel crawler"""

    def __init__(self):
        self.output_dir = Path(tempfile.mkdtemp(prefix="sagemtl_crawl_"))
        self.crawler = NovelCrawler()

    def crawl_novel(
        self,
        url: str,
        novel_name: str,
        start_chapter: Optional[int] = None,
        end_chapter: Optional[int] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        Crawl novel using SageCrawler.

        Args:
            url: Novel URL
            novel_name: Name for the novel
            start_chapter: Starting chapter (optional)
            end_chapter: Ending chapter (optional)
            progress_callback: Progress callback
            log_callback: Log callback

        Returns:
            Path to text file containing chapters
        """
        if log_callback:
            log_callback("info", f"Starting SageCrawler: {url}")

        # Use SageCrawler to fetch chapters
        novel_info = self.crawler.crawl_novel(
            start_url=url,
            start_chapter=start_chapter or 1,
            end_chapter=end_chapter or 999,
            dataset_name=novel_name or "novel"
        )

        if log_callback:
            log_callback("info", f"Found {len(novel_info.chapters)} chapters")

        # Save to dataset
        dataset_path = self.crawler.save_to_dataset(
            novel_info,
            self.output_dir,
            format="txt"
        )

        if log_callback:
            log_callback("info", f"Saved to: {dataset_path}")

        if progress_callback:
            progress_callback(100.0)

        return str(dataset_path)

    def cleanup(self):
        """Clean up temp directory"""
        if self.output_dir.exists():
            import shutil
            shutil.rmtree(self.output_dir)
```

### 6. EPUB Extractor (`core/epub_extractor.py`)

**Responsibilities:**
- Unzip EPUB
- Parse content.opf for reading order
- Extract chapter text
- Return concatenated text

```python
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple
from html.parser import HTMLParser
import io

class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML"""
    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data)

    def get_text(self):
        return ''.join(self.text_parts)

class EPUBExtractor:
    """Extract text from EPUB files"""

    def extract(self, epub_path: str) -> Tuple[str, List[str]]:
        """
        Extract chapters from EPUB.

        Args:
            epub_path: Path to EPUB file

        Returns:
            Tuple of (full_text, list_of_chapter_texts)
        """
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            # Find content.opf
            container_xml = zip_ref.read('META-INF/container.xml')
            container_tree = ET.fromstring(container_xml)

            # Get path to content.opf
            rootfile = container_tree.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
            opf_path = rootfile.get('full-path')

            # Parse content.opf
            opf_xml = zip_ref.read(opf_path)
            opf_tree = ET.fromstring(opf_xml)

            # Get reading order from spine
            spine_items = []
            spine = opf_tree.find('.//{http://www.idpf.org/2007/opf}spine')
            for itemref in spine.findall('{http://www.idpf.org/2007/opf}itemref'):
                idref = itemref.get('idref')
                spine_items.append(idref)

            # Get manifest (maps id to href)
            manifest = {}
            manifest_elem = opf_tree.find('.//{http://www.idpf.org/2007/opf}manifest')
            for item in manifest_elem.findall('{http://www.idpf.org/2007/opf}item'):
                item_id = item.get('id')
                href = item.get('href')
                manifest[item_id] = href

            # Extract chapters in order
            opf_dir = Path(opf_path).parent
            chapters = []

            for item_id in spine_items:
                if item_id not in manifest:
                    continue

                href = manifest[item_id]
                chapter_path = str(opf_dir / href)

                try:
                    chapter_html = zip_ref.read(chapter_path).decode('utf-8')
                    chapter_text = self._extract_text_from_html(chapter_html)
                    chapters.append(chapter_text)
                except Exception as e:
                    print(f"Failed to extract {chapter_path}: {e}")

            # Concatenate with chapter markers
            full_text = ""
            for i, chapter in enumerate(chapters, 1):
                full_text += f"\n\n=== Chapter {i} ===\n\n"
                full_text += chapter

            return full_text, chapters

    def _extract_text_from_html(self, html: str) -> str:
        """Extract plain text from HTML"""
        parser = HTMLTextExtractor()
        parser.feed(html)
        return parser.get_text().strip()
```

### 7. Exporter (`core/exporter.py`)

**Responsibilities:**
- Save cleaned text to disk
- Support batch export
- Handle file naming

```python
from pathlib import Path
from typing import List
from .models import Job

class Exporter:
    """Export cleaned/translated text to files"""

    def export_job(self, job: Job, output_dir: str) -> str:
        """
        Export a single job's cleaned text.

        Args:
            job: Job to export
            output_dir: Output directory

        Returns:
            Path to exported file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        base_name = Path(job.name).stem
        filename = f"{base_name}_cleaned.txt"
        file_path = output_path / filename

        # Write cleaned text
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(job.cleaned_text)

        return str(file_path)

    def export_batch(self, jobs: List[Job], output_dir: str) -> List[str]:
        """
        Export multiple jobs.

        Args:
            jobs: List of jobs to export
            output_dir: Output directory

        Returns:
            List of exported file paths
        """
        exported = []
        for job in jobs:
            if job.cleaned_text:
                path = self.export_job(job, output_dir)
                exported.append(path)

        return exported
```

## UI Components

### 1. Main Window (`ui/main_window.py`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  MenuBar: File | Edit | View | Tools | Help                │
├─────────────────────────────────────────────────────────────┤
│  ControlsPanel (Toolbar)                                    │
│  [Import] [Fetch URL] [Load Glossary] [Process] [Export]   │
│  Source: [Chinese ▼]  Target: [English ▼]                  │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│ FileListPanel│           PreviewPanel                       │
│              │  ┌─────────────┬─────────────┐              │
│  • file1.txt │  │  Original   │  Cleaned    │              │
│  ✓ file2.txt │  │             │             │              │
│  ✗ file3.txt │  │             │             │              │
│  ⟳ novel1    │  │             │             │              │
│              │  └─────────────┴─────────────┘              │
├──────────────┴──────────────────────────────────────────────┤
│  LogPanel                                                   │
│  [INFO] Started processing file1.txt                       │
│  [ERROR] Translation failed: ...                           │
└─────────────────────────────────────────────────────────────┘
```

### 2. Signals/Slots Architecture

**Data Flow:**
```
User Action (UI)
    ↓
    Signal emitted (e.g., processButton.clicked)
    ↓
    Slot in MainWindow (e.g., on_process_clicked)
    ↓
    Create job in JobManager
    ↓
    JobManager.start_job() → spawns worker thread
    ↓
    Worker emits progress/log signals
    ↓
    Slots in UI update widgets (progress bars, log panel, preview)
    ↓
    Worker completes → emits completion signal
    ↓
    UI updates file list status icon
```

## Packaging with PyInstaller

### PyInstaller Spec Structure

```python
# pyinstaller-desktop.spec

a = Analysis(
    ['sagemtl_desktop/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('sagemtl_desktop/resources', 'resources'),
        ('path/to/argos/models', 'argostranslate/models'),  # Bundle models
    ],
    hiddenimports=[
        'argostranslate',
        'argostranslate.package',
        'argostranslate.translate',
        'PySide6',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SageMTL',
    icon='sagemtl_desktop/resources/icons/app.ico',
    console=False,  # No console window
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='SageMTL'
)
```

### Bundled Argos Models

Pre-install these language packs:
- Chinese → English
- Japanese → English
- Korean → English
- English → Spanish (optional)

Bundle them in the `resources/models/` directory and ensure PyInstaller includes them.

## Key Features Implementation

### Progress Tracking
- Each worker thread emits progress signals (0-100)
- JobManager relays to UI
- UI updates progress bars in FileListPanel

### Error Handling
- All exceptions caught in worker threads
- Traceback stored in Job.error_traceback
- LogPanel displays with timestamp and job name
- Failed jobs show red icon in FileListPanel
- Clicking failed job shows error in preview

### Glossary Application
Pipeline for each job:
1. Read original text
2. GlossaryProcessor.apply_before(text)
3. Translator.translate(text)
4. GlossaryProcessor.apply_after(translated_text)
5. Store in Job.cleaned_text

### SageCrawler Integration
- Crawler uses built-in SageCrawler with automatic chapter detection
- Detects chapter patterns from URL structure
- Downloads chapters directly as text
- Text added as new job in FileListPanel

## Configuration

### Settings Storage
```python
# Use QSettings for persistent configuration
from PySide6.QtCore import QSettings

settings = QSettings("SageMTL", "SageMTL")
settings.setValue("source_lang", "zh")
settings.setValue("target_lang", "en")
settings.setValue("glossary_path", "path/to/glossary.csv")
```

## Development Workflow

1. Install dependencies:
   ```bash
   pip install -r requirements-desktop.txt
   ```

2. Run in development:
   ```bash
   python -m sagemtl_desktop.main
   ```

3. Build with PyInstaller:
   ```bash
   pyinstaller pyinstaller-desktop.spec
   ```

4. Distributable in `dist/SageMTL/`

## Testing Strategy

- Unit tests for each core module (translator, glossary, etc.)
- Integration tests for full pipeline
- UI tests with QTest
- Manual testing on Windows 10/11

## Future Enhancements

- Support for additional translation backends (MarianMT, etc.)
- EPUB output (rebuild translated EPUB)
- Batch glossary editing UI
- Translation memory/cache
- Multi-language UI (i18n with Qt Linguist)
