"""Main views for SageMTL desktop application.

This module provides the main application views:
- LibraryView: Grid/list of novels with covers
- DownloadView: URL input, search, job queue
- TranslationView: Source/target comparison
- GlossaryView: Term editor with filtering
- SettingsView: Organized preference panels
"""

from .library import LibraryView
from .download import DownloadView
from .translation import TranslationView
from .glossary import GlossaryView
from .settings import SettingsView

__all__ = [
    "LibraryView",
    "DownloadView",
    "TranslationView",
    "GlossaryView",
    "SettingsView",
]
