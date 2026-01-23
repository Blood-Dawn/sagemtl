"""Settings view for SageMTL.

This module provides the settings view with:
- Organized preference panels
- Theme selection
- Provider configuration
- Storage paths
"""

from __future__ import annotations

from typing import Optional

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QComboBox,
        QCheckBox,
        QSpinBox,
        QGroupBox,
        QFormLayout,
        QPushButton,
        QScrollArea,
        QFrame,
        QFileDialog,
        QTabWidget,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from ..constants import Spacing, Icons, Typography
from ..theme import get_theme_manager, ThemeMode
from ..components.buttons import PrimaryButton, SecondaryButton


if HAS_PYSIDE6:
    class SettingsView(QWidget):
        """Settings view for application configuration.

        Features:
        - General settings (theme, language)
        - Translation settings (provider, API keys)
        - Storage settings (paths, cache)
        - Download settings (concurrency, retry)

        Usage:
            view = SettingsView()
            view.settings_changed.connect(on_settings_changed)
        """

        settings_changed = Signal(dict)
        reset_requested = Signal()

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._apply_theme()
            self._load_current_settings()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        def _setup_ui(self) -> None:
            """Set up the settings UI."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
            layout.setSpacing(Spacing.MD)

            # Header
            header = QLabel("Settings")
            header.setStyleSheet(f"""
                font-size: {Typography.SIZE_XXL}px;
                font-weight: {Typography.WEIGHT_BOLD};
            """)
            layout.addWidget(header)

            # Tabs
            tabs = QTabWidget()
            tabs.addTab(self._create_general_tab(), "General")
            tabs.addTab(self._create_translation_tab(), "Translation")
            tabs.addTab(self._create_storage_tab(), "Storage")
            tabs.addTab(self._create_download_tab(), "Download")
            tabs.addTab(self._create_about_tab(), "About")
            layout.addWidget(tabs, 1)

            # Action bar
            action_bar = self._create_action_bar()
            layout.addLayout(action_bar)

        def _create_general_tab(self) -> QWidget:
            """Create general settings tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setSpacing(Spacing.LG)

            # Appearance group
            appearance_group = QGroupBox("Appearance")
            appearance_layout = QFormLayout(appearance_group)
            appearance_layout.setSpacing(Spacing.MD)

            # Theme
            self._theme_combo = QComboBox()
            self._theme_combo.addItems(["System", "Light", "Dark"])
            self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
            appearance_layout.addRow("Theme:", self._theme_combo)

            # Language
            self._language_combo = QComboBox()
            self._language_combo.addItems(["English", "Simplified Chinese", "Japanese"])
            appearance_layout.addRow("Language:", self._language_combo)

            layout.addWidget(appearance_group)

            # Behavior group
            behavior_group = QGroupBox("Behavior")
            behavior_layout = QFormLayout(behavior_group)
            behavior_layout.setSpacing(Spacing.MD)

            # Start minimized
            self._start_minimized = QCheckBox()
            behavior_layout.addRow("Start minimized:", self._start_minimized)

            # Minimize to tray
            self._minimize_to_tray = QCheckBox()
            behavior_layout.addRow("Minimize to tray:", self._minimize_to_tray)

            # Check for updates
            self._check_updates = QCheckBox()
            self._check_updates.setChecked(True)
            behavior_layout.addRow("Check for updates:", self._check_updates)

            layout.addWidget(behavior_group)

            layout.addStretch()
            return widget

        def _create_translation_tab(self) -> QWidget:
            """Create translation settings tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setSpacing(Spacing.LG)

            # Default provider group
            provider_group = QGroupBox("Default Provider")
            provider_layout = QFormLayout(provider_group)
            provider_layout.setSpacing(Spacing.MD)

            self._default_provider = QComboBox()
            self._default_provider.addItems([
                "Argos (Offline)",
                "Google Translate",
                "DeepL",
                "Azure Translator",
            ])
            provider_layout.addRow("Provider:", self._default_provider)

            self._source_lang = QComboBox()
            self._source_lang.addItems([
                "Chinese (Simplified)",
                "Chinese (Traditional)",
                "Japanese",
                "Korean",
            ])
            provider_layout.addRow("Source Language:", self._source_lang)

            self._target_lang = QComboBox()
            self._target_lang.addItems([
                "English",
                "Spanish",
                "French",
                "German",
            ])
            provider_layout.addRow("Target Language:", self._target_lang)

            layout.addWidget(provider_group)

            # API Keys group
            api_group = QGroupBox("API Keys")
            api_layout = QFormLayout(api_group)
            api_layout.setSpacing(Spacing.MD)

            self._google_api_key = QLineEdit()
            self._google_api_key.setPlaceholderText("Enter Google Cloud API key")
            self._google_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            api_layout.addRow("Google API Key:", self._google_api_key)

            self._deepl_api_key = QLineEdit()
            self._deepl_api_key.setPlaceholderText("Enter DeepL API key")
            self._deepl_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            api_layout.addRow("DeepL API Key:", self._deepl_api_key)

            self._azure_api_key = QLineEdit()
            self._azure_api_key.setPlaceholderText("Enter Azure subscription key")
            self._azure_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            api_layout.addRow("Azure API Key:", self._azure_api_key)

            self._azure_region = QLineEdit()
            self._azure_region.setPlaceholderText("e.g., eastus")
            api_layout.addRow("Azure Region:", self._azure_region)

            layout.addWidget(api_group)

            # Glossary group
            glossary_group = QGroupBox("Glossary")
            glossary_layout = QFormLayout(glossary_group)
            glossary_layout.setSpacing(Spacing.MD)

            self._use_glossary = QCheckBox()
            self._use_glossary.setChecked(True)
            glossary_layout.addRow("Enable glossary:", self._use_glossary)

            self._auto_apply_glossary = QCheckBox()
            self._auto_apply_glossary.setChecked(True)
            glossary_layout.addRow("Auto-apply glossary:", self._auto_apply_glossary)

            layout.addWidget(glossary_group)

            layout.addStretch()
            return widget

        def _create_storage_tab(self) -> QWidget:
            """Create storage settings tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setSpacing(Spacing.LG)

            # Paths group
            paths_group = QGroupBox("Storage Paths")
            paths_layout = QFormLayout(paths_group)
            paths_layout.setSpacing(Spacing.MD)

            # Library path
            library_row = QHBoxLayout()
            self._library_path = QLineEdit()
            self._library_path.setPlaceholderText("Select library folder")
            library_row.addWidget(self._library_path)
            library_browse = QPushButton("Browse...")
            library_browse.clicked.connect(lambda: self._browse_folder(self._library_path))
            library_row.addWidget(library_browse)
            paths_layout.addRow("Library:", library_row)

            # Cache path
            cache_row = QHBoxLayout()
            self._cache_path = QLineEdit()
            self._cache_path.setPlaceholderText("Select cache folder")
            cache_row.addWidget(self._cache_path)
            cache_browse = QPushButton("Browse...")
            cache_browse.clicked.connect(lambda: self._browse_folder(self._cache_path))
            cache_row.addWidget(cache_browse)
            paths_layout.addRow("Cache:", cache_row)

            # Export path
            export_row = QHBoxLayout()
            self._export_path = QLineEdit()
            self._export_path.setPlaceholderText("Select export folder")
            export_row.addWidget(self._export_path)
            export_browse = QPushButton("Browse...")
            export_browse.clicked.connect(lambda: self._browse_folder(self._export_path))
            export_row.addWidget(export_browse)
            paths_layout.addRow("Export:", export_row)

            layout.addWidget(paths_group)

            # Cache group
            cache_group = QGroupBox("Cache Management")
            cache_layout = QFormLayout(cache_group)
            cache_layout.setSpacing(Spacing.MD)

            self._cache_size_label = QLabel("0 MB")
            cache_layout.addRow("Cache size:", self._cache_size_label)

            clear_cache_btn = SecondaryButton("Clear Cache")
            clear_cache_btn.clicked.connect(self._on_clear_cache)
            cache_layout.addRow("", clear_cache_btn)

            layout.addWidget(cache_group)

            layout.addStretch()
            return widget

        def _create_download_tab(self) -> QWidget:
            """Create download settings tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setSpacing(Spacing.LG)

            # Connection group
            connection_group = QGroupBox("Connection")
            connection_layout = QFormLayout(connection_group)
            connection_layout.setSpacing(Spacing.MD)

            self._concurrent_downloads = QSpinBox()
            self._concurrent_downloads.setRange(1, 10)
            self._concurrent_downloads.setValue(3)
            connection_layout.addRow("Concurrent downloads:", self._concurrent_downloads)

            self._request_delay = QSpinBox()
            self._request_delay.setRange(0, 5000)
            self._request_delay.setValue(500)
            self._request_delay.setSuffix(" ms")
            connection_layout.addRow("Request delay:", self._request_delay)

            self._timeout = QSpinBox()
            self._timeout.setRange(5, 120)
            self._timeout.setValue(30)
            self._timeout.setSuffix(" seconds")
            connection_layout.addRow("Timeout:", self._timeout)

            layout.addWidget(connection_group)

            # Retry group
            retry_group = QGroupBox("Retry Settings")
            retry_layout = QFormLayout(retry_group)
            retry_layout.setSpacing(Spacing.MD)

            self._max_retries = QSpinBox()
            self._max_retries.setRange(0, 10)
            self._max_retries.setValue(3)
            retry_layout.addRow("Max retries:", self._max_retries)

            self._retry_delay = QSpinBox()
            self._retry_delay.setRange(1000, 30000)
            self._retry_delay.setValue(5000)
            self._retry_delay.setSuffix(" ms")
            retry_layout.addRow("Retry delay:", self._retry_delay)

            layout.addWidget(retry_group)

            # Output group
            output_group = QGroupBox("Default Output")
            output_layout = QFormLayout(output_group)
            output_layout.setSpacing(Spacing.MD)

            self._default_format = QComboBox()
            self._default_format.addItems([
                "EPUB",
                "PDF",
                "TXT",
                "HTML",
                "DOCX",
                "Markdown",
            ])
            output_layout.addRow("Default format:", self._default_format)

            self._include_cover = QCheckBox()
            self._include_cover.setChecked(True)
            output_layout.addRow("Include cover:", self._include_cover)

            self._include_toc = QCheckBox()
            self._include_toc.setChecked(True)
            output_layout.addRow("Include TOC:", self._include_toc)

            layout.addWidget(output_group)

            layout.addStretch()
            return widget

        def _create_about_tab(self) -> QWidget:
            """Create about tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setSpacing(Spacing.LG)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Logo/title
            title = QLabel("SageMTL")
            title.setStyleSheet(f"""
                font-size: {Typography.SIZE_DISPLAY}px;
                font-weight: {Typography.WEIGHT_BOLD};
            """)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title)

            # Version
            version = QLabel("Version 0.4.0")
            version.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(version)

            # Description
            description = QLabel(
                "A modern web novel translation toolkit.\n"
                "Download, translate, and export novels from multiple sources."
            )
            description.setAlignment(Qt.AlignmentFlag.AlignCenter)
            description.setWordWrap(True)
            layout.addWidget(description)

            layout.addSpacing(Spacing.LG)

            # Links
            github_btn = SecondaryButton("GitHub Repository")
            github_btn.clicked.connect(
                lambda: self._open_url("https://github.com/blood-dawn/sagemtl")
            )
            layout.addWidget(github_btn, alignment=Qt.AlignmentFlag.AlignCenter)

            layout.addStretch()
            return widget

        def _create_action_bar(self) -> QHBoxLayout:
            """Create the action bar."""
            layout = QHBoxLayout()
            layout.setSpacing(Spacing.SM)

            # Reset button
            reset_btn = SecondaryButton("Reset to Defaults")
            reset_btn.clicked.connect(self._on_reset)
            layout.addWidget(reset_btn)

            layout.addStretch()

            # Save button
            save_btn = PrimaryButton("Save Settings", Icons.SAVE.value)
            save_btn.clicked.connect(self._on_save)
            layout.addWidget(save_btn)

            return layout

        def _browse_folder(self, line_edit: QLineEdit) -> None:
            """Open folder browser."""
            folder = QFileDialog.getExistingDirectory(
                self,
                "Select Folder",
                line_edit.text() or "",
            )
            if folder:
                line_edit.setText(folder)

        def _on_theme_changed(self, index: int) -> None:
            """Handle theme selection change."""
            modes = [ThemeMode.SYSTEM, ThemeMode.LIGHT, ThemeMode.DARK]
            if index < len(modes):
                self._theme_manager.set_theme_mode(modes[index])

        def _on_clear_cache(self) -> None:
            """Handle clear cache button."""
            # TODO: Implement cache clearing
            self._cache_size_label.setText("0 MB")

        def _on_reset(self) -> None:
            """Handle reset button."""
            self.reset_requested.emit()
            self._load_current_settings()

        def _on_save(self) -> None:
            """Handle save button."""
            settings = self._get_current_settings()
            self.settings_changed.emit(settings)

        def _load_current_settings(self) -> None:
            """Load current settings into UI."""
            # Set theme combo based on current mode
            mode = self._theme_manager.current_mode
            mode_index = {
                ThemeMode.SYSTEM: 0,
                ThemeMode.LIGHT: 1,
                ThemeMode.DARK: 2,
            }.get(mode, 0)
            self._theme_combo.setCurrentIndex(mode_index)

        def _get_current_settings(self) -> dict:
            """Get current settings from UI."""
            return {
                "theme": self._theme_combo.currentText().lower(),
                "language": self._language_combo.currentText(),
                "start_minimized": self._start_minimized.isChecked(),
                "minimize_to_tray": self._minimize_to_tray.isChecked(),
                "check_updates": self._check_updates.isChecked(),
                "default_provider": self._default_provider.currentIndex(),
                "source_lang": self._source_lang.currentText(),
                "target_lang": self._target_lang.currentText(),
                "google_api_key": self._google_api_key.text(),
                "deepl_api_key": self._deepl_api_key.text(),
                "azure_api_key": self._azure_api_key.text(),
                "azure_region": self._azure_region.text(),
                "use_glossary": self._use_glossary.isChecked(),
                "auto_apply_glossary": self._auto_apply_glossary.isChecked(),
                "library_path": self._library_path.text(),
                "cache_path": self._cache_path.text(),
                "export_path": self._export_path.text(),
                "concurrent_downloads": self._concurrent_downloads.value(),
                "request_delay": self._request_delay.value(),
                "timeout": self._timeout.value(),
                "max_retries": self._max_retries.value(),
                "retry_delay": self._retry_delay.value(),
                "default_format": self._default_format.currentText(),
                "include_cover": self._include_cover.isChecked(),
                "include_toc": self._include_toc.isChecked(),
            }

        def _open_url(self, url: str) -> None:
            """Open URL in browser."""
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(url))

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            self.setStyleSheet(f"""
                SettingsView {{
                    background-color: {colors.background};
                }}
                QLabel {{
                    color: {colors.text_primary};
                    background-color: transparent;
                }}
                QGroupBox {{
                    color: {colors.text_primary};
                    font-weight: {Typography.WEIGHT_SEMIBOLD};
                }}
            """)

else:
    class SettingsView:
        """Stub SettingsView when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")
