"""
Data models for SageMTL Desktop application.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class JobStatus(Enum):
    """Status of a processing job"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(Enum):
    """Type of job"""
    IMPORT_FILE = "import_file"
    CRAWL_URL = "crawl_url"
    TRANSLATE = "translate"
    EXPORT = "export"
    # Manga module job types (spec section 11, item 4)
    MANGA_CRAWL = "manga_crawl"
    MANGA_TRANSLATE = "manga_translate"
    MANGA_EXPORT = "manga_export"


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

    def __str__(self):
        return f"Job({self.name}, {self.status.value}, {self.progress:.1f}%)"


@dataclass
class ProcessingOptions:
    """Options for text processing pipeline"""
    source_lang: str = "auto"  # Language code or "auto"
    target_lang: str = "en"    # English by default
    glossary_path: Optional[str] = None
    translation_backend: str = "argos"

    # Chunking options
    max_chunk_size: int = 900  # Max characters per chunk

    def __str__(self):
        return (
            f"ProcessingOptions({self.source_lang}→{self.target_lang}, "
            f"backend={self.translation_backend}, chunk={self.max_chunk_size})"
        )


@dataclass
class GlossaryEntry:
    """Single glossary mapping"""
    source: str
    target: str
    case_sensitive: bool = True
    word_boundary: bool = False
    notes: str = ""

    def __str__(self):
        flags = []
        if self.case_sensitive:
            flags.append("case")
        if self.word_boundary:
            flags.append("boundary")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        return f"{self.source} → {self.target}{flag_str}"
