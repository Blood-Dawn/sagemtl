"""
Core backend modules for SageMTL Desktop.

This package contains all backend logic without UI dependencies.
"""

from .models import Job, JobStatus, JobType, ProcessingOptions, GlossaryEntry
from .job_manager import JobManager
from .translator import Translator, MissingTranslatorError
from .glossary import GlossaryProcessor
from .crawler import Crawler
from .epub_extractor import EPUBExtractor
from .epub_writer import EPUBWriter
from .exporter import Exporter

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
    "Crawler",
    "EPUBExtractor",
    "EPUBWriter",
    "Exporter",
]
