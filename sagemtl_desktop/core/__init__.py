"""
Core backend modules for SageMTL Desktop.

This package contains all backend logic without UI dependencies.
"""

from .models import Job, JobStatus, JobType, ProcessingOptions, GlossaryEntry
from .job_manager import JobManager
from .translator import Translator, MissingTranslatorError
from .glossary import GlossaryProcessor
from .epub_extractor import EPUBExtractor
from .epub_writer import EPUBWriter
from .exporter import Exporter
from .import_manager import ImportManager
from .structured_logger import StructuredLogger, get_logger
from .crawl_service import CrawlService
from .crawl_settings import CrawlSettings, DEFAULT_CRAWL_USER_AGENT
from .search_service import SearchService
from .app_settings import DesktopAppSettings, DesktopSettingsStore

__all__ = [
    "Job",
    "JobStatus",
    "JobType",
    "ProcessingOptions",
    "GlossaryEntry",
    "JobManager",
    "Translator",
    "MissingTranslatorError",
    "GlossaryProcessor",
    "EPUBExtractor",
    "EPUBWriter",
    "Exporter",
    "ImportManager",
    "StructuredLogger",
    "get_logger",
    "CrawlService",
    "CrawlSettings",
    "DEFAULT_CRAWL_USER_AGENT",
    "SearchService",
    "DesktopAppSettings",
    "DesktopSettingsStore",
]
