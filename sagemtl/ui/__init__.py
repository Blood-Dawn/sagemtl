"""Modern PySide6-based desktop UI for SageMTL.

This module provides a modern, themeable desktop interface with:
- Light/dark theme support with system detection
- Custom frameless title bar
- Sidebar navigation (Fluent-style)
- Dockable panels
- Toast notifications
"""

from .theme import ThemeManager, Theme, ThemeColors, ThemeMode, get_theme_manager
from .constants import Spacing, Typography, Icons

# Conditional imports for PySide6-dependent components
try:
    from .main_window import MainWindow, run_app
    from .components import (
        TitleBar,
        Sidebar,
        SidebarItem,
        ToastManager,
        Toast,
        ToastType,
        Card,
        NovelCard,
        IconButton,
        PrimaryButton,
        SecondaryButton,
    )
    from .views import (
        LibraryView,
        DownloadView,
        TranslationView,
        GlossaryView,
        SettingsView,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False
    MainWindow = None
    run_app = None

__all__ = [
    # Theme
    "ThemeManager",
    "Theme",
    "ThemeColors",
    "ThemeMode",
    "get_theme_manager",
    # Constants
    "Spacing",
    "Typography",
    "Icons",
    # Main window
    "MainWindow",
    "run_app",
    # Components
    "TitleBar",
    "Sidebar",
    "SidebarItem",
    "ToastManager",
    "Toast",
    "ToastType",
    "Card",
    "NovelCard",
    "IconButton",
    "PrimaryButton",
    "SecondaryButton",
    # Views
    "LibraryView",
    "DownloadView",
    "TranslationView",
    "GlossaryView",
    "SettingsView",
    # Feature flag
    "HAS_PYSIDE6",
]
