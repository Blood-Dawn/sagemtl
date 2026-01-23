"""Main window for SageMTL desktop application.

This module provides the main application window with:
- Custom frameless title bar
- Sidebar navigation
- Stacked content views
- Toast notifications
"""

from __future__ import annotations

from typing import Optional

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QStackedWidget,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from .constants import Spacing, Icons
from .theme import get_theme_manager
from .components.titlebar import TitleBar
from .components.sidebar import Sidebar, SidebarItem
from .components.toast import ToastManager
from .views.library import LibraryView
from .views.download import DownloadView
from .views.translation import TranslationView
from .views.glossary import GlossaryView
from .views.settings import SettingsView


if HAS_PYSIDE6:
    class MainWindow(QMainWindow):
        """Main application window for SageMTL.

        Features:
        - Custom frameless title bar
        - Sidebar navigation
        - Multiple views (Library, Download, Translation, Glossary, Settings)
        - Toast notifications
        - Theme switching

        Usage:
            window = MainWindow()
            window.show()
        """

        def __init__(self):
            super().__init__()
            self._theme_manager = get_theme_manager()

            self._setup_window()
            self._setup_ui()
            self._connect_signals()
            self._apply_theme()

            # Initialize toast manager
            self._toast_manager = ToastManager(self)

            # Listen for theme changes
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        def _setup_window(self) -> None:
            """Configure window properties."""
            self.setWindowTitle("SageMTL")
            self.setMinimumSize(1200, 800)

            # Frameless window
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Window
            )

            # Enable transparency for rounded corners
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        def _setup_ui(self) -> None:
            """Set up the main UI."""
            # Central widget
            central = QWidget()
            self.setCentralWidget(central)

            # Main layout
            main_layout = QVBoxLayout(central)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            # Title bar
            self._title_bar = TitleBar()
            main_layout.addWidget(self._title_bar)

            # Body (sidebar + content)
            body_layout = QHBoxLayout()
            body_layout.setContentsMargins(0, 0, 0, 0)
            body_layout.setSpacing(0)

            # Sidebar
            self._sidebar = Sidebar()
            self._setup_navigation()
            body_layout.addWidget(self._sidebar)

            # Content stack
            self._content_stack = QStackedWidget()
            self._setup_views()
            body_layout.addWidget(self._content_stack, 1)

            main_layout.addLayout(body_layout, 1)

        def _setup_navigation(self) -> None:
            """Set up sidebar navigation items."""
            nav_items = [
                SidebarItem("library", "Library", Icons.LIBRARY.value, "View your novel library"),
                SidebarItem("download", "Download", Icons.DOWNLOAD.value, "Download novels"),
                SidebarItem("translation", "Translation", Icons.TRANSLATE.value, "Translate text"),
                SidebarItem("glossary", "Glossary", Icons.GLOSSARY.value, "Manage glossary terms"),
            ]

            for item in nav_items:
                self._sidebar.add_item(item)

            self._sidebar.add_spacer()
            self._sidebar.add_item(
                SidebarItem("settings", "Settings", Icons.SETTINGS.value, "Application settings")
            )

            # Set initial selection
            self._sidebar.set_active("library")

        def _setup_views(self) -> None:
            """Set up content views."""
            # Library view
            self._library_view = LibraryView()
            self._content_stack.addWidget(self._library_view)

            # Download view
            self._download_view = DownloadView()
            self._content_stack.addWidget(self._download_view)

            # Translation view
            self._translation_view = TranslationView()
            self._content_stack.addWidget(self._translation_view)

            # Glossary view
            self._glossary_view = GlossaryView()
            self._content_stack.addWidget(self._glossary_view)

            # Settings view
            self._settings_view = SettingsView()
            self._content_stack.addWidget(self._settings_view)

            # View index mapping
            self._view_indices = {
                "library": 0,
                "download": 1,
                "translation": 2,
                "glossary": 3,
                "settings": 4,
            }

        def _connect_signals(self) -> None:
            """Connect signals between components."""
            # Sidebar navigation
            self._sidebar.item_clicked.connect(self._on_nav_changed)

            # Library view
            self._library_view.novel_selected.connect(self._on_novel_selected)
            self._library_view.download_requested.connect(
                lambda: self._on_nav_changed("download")
            )

            # Download view
            self._download_view.download_started.connect(self._on_download_started)

            # Translation view
            self._translation_view.translation_requested.connect(self._on_translate)

            # Glossary view
            self._glossary_view.term_added.connect(self._on_term_added)

            # Settings view
            self._settings_view.settings_changed.connect(self._on_settings_changed)

        def _on_nav_changed(self, item_id: str) -> None:
            """Handle navigation change."""
            if item_id in self._view_indices:
                self._content_stack.setCurrentIndex(self._view_indices[item_id])
                self._sidebar.set_active(item_id)

        def _on_novel_selected(self, novel_id: str) -> None:
            """Handle novel selection."""
            # TODO: Open novel detail view
            self._toast_manager.show_info(f"Opening novel: {novel_id}")

        def _on_download_started(self, url: str) -> None:
            """Handle download start."""
            self._toast_manager.show_info(f"Starting download: {url}")
            # TODO: Integrate with crawler

        def _on_translate(self, text: str, source_lang: str, target_lang: str) -> None:
            """Handle translation request."""
            # TODO: Integrate with translation pipeline
            self._toast_manager.show_info("Translation started...")

        def _on_term_added(self, source: str, target: str, category: str) -> None:
            """Handle glossary term added."""
            self._toast_manager.show_success(f"Added term: {source} -> {target}")
            # TODO: Integrate with glossary DB

        def _on_settings_changed(self, settings: dict) -> None:
            """Handle settings change."""
            self._toast_manager.show_success("Settings saved")
            # TODO: Persist settings

        def _apply_theme(self) -> None:
            """Apply current theme."""
            colors = self._theme_manager.current_theme.colors
            stylesheet = self._theme_manager.generate_stylesheet()

            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {colors.background};
                }}
                {stylesheet}
            """)

        # --- Public API ---

        def show_toast_success(self, message: str, title: Optional[str] = None) -> None:
            """Show a success toast notification."""
            self._toast_manager.show_success(message, title)

        def show_toast_error(self, message: str, title: Optional[str] = None) -> None:
            """Show an error toast notification."""
            self._toast_manager.show_error(message, title)

        def show_toast_warning(self, message: str, title: Optional[str] = None) -> None:
            """Show a warning toast notification."""
            self._toast_manager.show_warning(message, title)

        def show_toast_info(self, message: str, title: Optional[str] = None) -> None:
            """Show an info toast notification."""
            self._toast_manager.show_info(message, title)

        def navigate_to(self, view_id: str) -> None:
            """Navigate to a specific view."""
            self._on_nav_changed(view_id)

        @property
        def library_view(self) -> LibraryView:
            """Get the library view."""
            return self._library_view

        @property
        def download_view(self) -> DownloadView:
            """Get the download view."""
            return self._download_view

        @property
        def translation_view(self) -> TranslationView:
            """Get the translation view."""
            return self._translation_view

        @property
        def glossary_view(self) -> GlossaryView:
            """Get the glossary view."""
            return self._glossary_view

        @property
        def settings_view(self) -> SettingsView:
            """Get the settings view."""
            return self._settings_view


    def run_app() -> int:
        """Run the SageMTL desktop application.

        Returns:
            Exit code from the application.
        """
        import sys
        from PySide6.QtWidgets import QApplication

        app = QApplication(sys.argv)
        app.setApplicationName("SageMTL")
        app.setOrganizationName("Blood-Dawn")

        # Apply initial theme
        theme_manager = get_theme_manager()
        theme_manager.set_theme_mode(theme_manager.current_mode)

        window = MainWindow()
        window.show()

        return app.exec()

else:
    class MainWindow:
        """Stub MainWindow when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")

    def run_app() -> int:
        """Stub run_app when PySide6 is not available."""
        raise ImportError("PySide6 is required for the desktop UI")
