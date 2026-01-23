"""Translation view for SageMTL.

This module provides the translation view with:
- Source/target text comparison
- Provider selection
- Glossary integration
- Real-time translation
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
        QTextEdit,
        QComboBox,
        QSplitter,
        QFrame,
        QCheckBox,
        QSpinBox,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from ..constants import Spacing, Icons, Typography
from ..theme import get_theme_manager
from ..components.buttons import PrimaryButton, SecondaryButton


if HAS_PYSIDE6:
    class TranslationView(QWidget):
        """Translation view for translating novel content.

        Features:
        - Side-by-side source/target view
        - Multiple translation providers
        - Glossary toggle
        - Real-time preview

        Usage:
            view = TranslationView()
            view.translation_requested.connect(on_translate)
        """

        translation_requested = Signal(str, str, str)  # text, source_lang, target_lang
        batch_translation_requested = Signal(str)  # novel_id

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._apply_theme()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        def set_source_text(self, text: str) -> None:
            """Set the source text."""
            self._source_text.setPlainText(text)

        def set_translated_text(self, text: str) -> None:
            """Set the translated text."""
            self._target_text.setPlainText(text)

        def get_source_text(self) -> str:
            """Get the current source text."""
            return self._source_text.toPlainText()

        def get_translated_text(self) -> str:
            """Get the current translated text."""
            return self._target_text.toPlainText()

        def _setup_ui(self) -> None:
            """Set up the translation UI."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
            layout.setSpacing(Spacing.MD)

            # Header
            header = QLabel("Translation")
            header.setStyleSheet(f"""
                font-size: {Typography.SIZE_XXL}px;
                font-weight: {Typography.WEIGHT_BOLD};
            """)
            layout.addWidget(header)

            # Settings bar
            settings_bar = self._create_settings_bar()
            layout.addLayout(settings_bar)

            # Main content (splitter)
            splitter = QSplitter(Qt.Orientation.Horizontal)

            # Source panel
            source_panel = self._create_text_panel("Source", is_source=True)
            splitter.addWidget(source_panel)

            # Target panel
            target_panel = self._create_text_panel("Translation", is_source=False)
            splitter.addWidget(target_panel)

            splitter.setSizes([500, 500])
            layout.addWidget(splitter, 1)

            # Action bar
            action_bar = self._create_action_bar()
            layout.addLayout(action_bar)

        def _create_settings_bar(self) -> QHBoxLayout:
            """Create the settings bar."""
            layout = QHBoxLayout()
            layout.setSpacing(Spacing.MD)

            # Provider selection
            provider_label = QLabel("Provider:")
            layout.addWidget(provider_label)

            self._provider_combo = QComboBox()
            self._provider_combo.addItems([
                "Argos (Offline)",
                "Google Translate",
                "DeepL",
                "Azure Translator",
            ])
            self._provider_combo.setMinimumWidth(150)
            layout.addWidget(self._provider_combo)

            layout.addSpacing(Spacing.MD)

            # Source language
            source_label = QLabel("From:")
            layout.addWidget(source_label)

            self._source_lang_combo = QComboBox()
            self._source_lang_combo.addItems([
                "Chinese (Simplified)",
                "Chinese (Traditional)",
                "Japanese",
                "Korean",
                "Auto-detect",
            ])
            layout.addWidget(self._source_lang_combo)

            # Target language
            target_label = QLabel("To:")
            layout.addWidget(target_label)

            self._target_lang_combo = QComboBox()
            self._target_lang_combo.addItems([
                "English",
                "Spanish",
                "French",
                "German",
                "Portuguese",
            ])
            layout.addWidget(self._target_lang_combo)

            layout.addStretch()

            # Glossary toggle
            self._glossary_check = QCheckBox("Use Glossary")
            self._glossary_check.setChecked(True)
            layout.addWidget(self._glossary_check)

            return layout

        def _create_text_panel(self, title: str, is_source: bool) -> QFrame:
            """Create a text panel (source or target)."""
            frame = QFrame()
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(Spacing.SM)

            # Panel header
            header_layout = QHBoxLayout()

            label = QLabel(title)
            label.setStyleSheet(f"""
                font-size: {Typography.SIZE_LG}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            """)
            header_layout.addWidget(label)

            header_layout.addStretch()

            # Character count
            char_count = QLabel("0 characters")
            char_count.setObjectName("char_count")
            char_count.setStyleSheet(f"font-size: {Typography.SIZE_SM}px;")
            header_layout.addWidget(char_count)

            layout.addLayout(header_layout)

            # Text area
            text_edit = QTextEdit()
            text_edit.setPlaceholderText(
                "Paste source text here..." if is_source
                else "Translation will appear here..."
            )

            if is_source:
                self._source_text = text_edit
                self._source_char_count = char_count
                text_edit.textChanged.connect(self._on_source_changed)
            else:
                self._target_text = text_edit
                self._target_char_count = char_count
                text_edit.setReadOnly(True)

            layout.addWidget(text_edit, 1)

            return frame

        def _create_action_bar(self) -> QHBoxLayout:
            """Create the action bar."""
            layout = QHBoxLayout()
            layout.setSpacing(Spacing.SM)

            # Clear button
            clear_btn = SecondaryButton("Clear")
            clear_btn.clicked.connect(self._on_clear)
            layout.addWidget(clear_btn)

            layout.addStretch()

            # Copy translation button
            copy_btn = SecondaryButton("Copy Translation", Icons.FILE.value)
            copy_btn.clicked.connect(self._on_copy)
            layout.addWidget(copy_btn)

            # Translate button
            translate_btn = PrimaryButton("Translate", Icons.TRANSLATE.value)
            translate_btn.clicked.connect(self._on_translate)
            layout.addWidget(translate_btn)

            return layout

        def _on_source_changed(self) -> None:
            """Handle source text change."""
            text = self._source_text.toPlainText()
            self._source_char_count.setText(f"{len(text)} characters")

        def _on_clear(self) -> None:
            """Clear both text areas."""
            self._source_text.clear()
            self._target_text.clear()

        def _on_copy(self) -> None:
            """Copy translation to clipboard."""
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self._target_text.toPlainText())

        def _on_translate(self) -> None:
            """Request translation."""
            text = self._source_text.toPlainText()
            if text.strip():
                # Map combo selections to language codes
                source_map = {
                    "Chinese (Simplified)": "zh",
                    "Chinese (Traditional)": "zh-TW",
                    "Japanese": "ja",
                    "Korean": "ko",
                    "Auto-detect": "auto",
                }
                target_map = {
                    "English": "en",
                    "Spanish": "es",
                    "French": "fr",
                    "German": "de",
                    "Portuguese": "pt",
                }

                source_lang = source_map.get(
                    self._source_lang_combo.currentText(), "zh"
                )
                target_lang = target_map.get(
                    self._target_lang_combo.currentText(), "en"
                )

                self.translation_requested.emit(text, source_lang, target_lang)

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            self.setStyleSheet(f"""
                TranslationView {{
                    background-color: {colors.background};
                }}
                QLabel {{
                    color: {colors.text_primary};
                    background-color: transparent;
                }}
                QFrame {{
                    background-color: transparent;
                    border: none;
                }}
                QTextEdit {{
                    background-color: {colors.surface};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border};
                    border-radius: {Spacing.RADIUS_MD}px;
                    padding: {Spacing.SM}px;
                    font-family: {Typography.FONT_FAMILY};
                    font-size: {Typography.SIZE_MD}px;
                    line-height: {Typography.LINE_HEIGHT_RELAXED};
                }}
                QTextEdit:focus {{
                    border-color: {colors.accent};
                }}
            """)

else:
    class TranslationView:
        """Stub TranslationView when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")
