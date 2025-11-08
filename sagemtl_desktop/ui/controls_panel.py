"""
Controls and settings panel.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QLineEdit,
    QFileDialog, QToolBar
)
from PySide6.QtCore import Qt, Signal


class ControlsPanel(QWidget):
    """Widget containing all controls and settings"""

    # Signals
    import_files_clicked = Signal()
    fetch_url_clicked = Signal(str)  # url
    load_glossary_clicked = Signal(str)  # path
    start_processing_clicked = Signal()
    export_clicked = Signal()
    source_lang_changed = Signal(str)  # language code
    target_lang_changed = Signal(str)  # language code

    def __init__(self, parent=None):
        super().__init__(parent)
        self._glossary_path = None
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Toolbar with main actions
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Settings group
        settings_group = self._create_settings_group()
        layout.addWidget(settings_group)

        # URL fetch group
        url_group = self._create_url_fetch_group()
        layout.addWidget(url_group)

        layout.addStretch()

    def _create_toolbar(self) -> QToolBar:
        """Create toolbar with main action buttons"""
        toolbar = QToolBar()
        toolbar.setMovable(False)

        # Import Files button
        import_btn = QPushButton("📁 Import Files")
        import_btn.setToolTip("Import text or EPUB files")
        import_btn.clicked.connect(self.import_files_clicked.emit)
        toolbar.addWidget(import_btn)

        toolbar.addSeparator()

        # Load Glossary button
        glossary_btn = QPushButton("📋 Load Glossary")
        glossary_btn.setToolTip("Load CSV glossary file")
        glossary_btn.clicked.connect(self._on_load_glossary)
        toolbar.addWidget(glossary_btn)

        toolbar.addSeparator()

        # Start Processing button
        self.process_btn = QPushButton("▶ Start Processing")
        self.process_btn.setToolTip("Process all pending files")
        self.process_btn.setStyleSheet("font-weight: bold; padding: 6px 12px;")
        self.process_btn.clicked.connect(self.start_processing_clicked.emit)
        toolbar.addWidget(self.process_btn)

        toolbar.addSeparator()

        # Export button
        export_btn = QPushButton("💾 Export Results")
        export_btn.setToolTip("Export cleaned text files")
        export_btn.clicked.connect(self.export_clicked.emit)
        toolbar.addWidget(export_btn)

        return toolbar

    def _create_settings_group(self) -> QGroupBox:
        """Create language settings group"""
        group = QGroupBox("Translation Settings")
        layout = QHBoxLayout(group)

        # Source language
        layout.addWidget(QLabel("Source:"))

        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "Auto-detect",
            "Chinese (zh)",
            "Japanese (ja)",
            "Korean (ko)",
            "Spanish (es)",
            "French (fr)",
            "German (de)",
        ])
        self.source_combo.currentTextChanged.connect(self._on_source_changed)
        layout.addWidget(self.source_combo)

        layout.addSpacing(20)

        # Target language
        layout.addWidget(QLabel("Target:"))

        self.target_combo = QComboBox()
        self.target_combo.addItems([
            "English (en)",
            "Spanish (es)",
            "French (fr)",
            "German (de)",
            "Chinese (zh)",
            "Japanese (ja)",
        ])
        self.target_combo.currentTextChanged.connect(self._on_target_changed)
        layout.addWidget(self.target_combo)

        layout.addSpacing(20)

        # Glossary status
        self.glossary_label = QLabel("No glossary loaded")
        self.glossary_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.glossary_label)

        layout.addStretch()

        return group

    def _create_url_fetch_group(self) -> QGroupBox:
        """Create URL fetch group"""
        group = QGroupBox("Fetch Novel from URL")
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("URL:"))

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/novel/chapter-1")
        layout.addWidget(self.url_input)

        fetch_btn = QPushButton("Fetch")
        fetch_btn.clicked.connect(self._on_fetch_url)
        layout.addWidget(fetch_btn)

        return group

    def _on_load_glossary(self):
        """Handle glossary load button"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Glossary File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            self._glossary_path = file_path
            self.glossary_label.setText(f"Glossary: {file_path.split('/')[-1]}")
            self.glossary_label.setStyleSheet("color: green;")
            self.load_glossary_clicked.emit(file_path)

    def _on_fetch_url(self):
        """Handle fetch URL button"""
        url = self.url_input.text().strip()
        if url:
            self.fetch_url_clicked.emit(url)
            self.url_input.clear()

    def _on_source_changed(self, text: str):
        """Handle source language change"""
        # Extract language code from text (e.g., "Chinese (zh)" -> "zh")
        if "(" in text and ")" in text:
            code = text.split("(")[1].split(")")[0]
        elif text == "Auto-detect":
            code = "auto"
        else:
            code = "en"

        self.source_lang_changed.emit(code)

    def _on_target_changed(self, text: str):
        """Handle target language change"""
        # Extract language code from text
        if "(" in text and ")" in text:
            code = text.split("(")[1].split(")")[0]
        else:
            code = "en"

        self.target_lang_changed.emit(code)

    def set_processing_enabled(self, enabled: bool):
        """Enable/disable processing button"""
        self.process_btn.setEnabled(enabled)

        if not enabled:
            self.process_btn.setText("⏸ Processing...")
        else:
            self.process_btn.setText("▶ Start Processing")

    def populate_languages(self, available_languages: list):
        """
        Populate language dropdowns with available Argos models.

        Args:
            available_languages: List of (from_code, to_code, display_name) tuples
        """
        # Get unique source languages
        source_langs = set()
        target_langs = set()

        for from_code, to_code, display_name in available_languages:
            source_langs.add((from_code, display_name.split(" → ")[0]))
            target_langs.add((to_code, display_name.split(" → ")[1]))

        # Update source combo
        self.source_combo.clear()
        self.source_combo.addItem("Auto-detect")
        for code, name in sorted(source_langs):
            self.source_combo.addItem(f"{name} ({code})")

        # Update target combo
        self.target_combo.clear()
        for code, name in sorted(target_langs):
            self.target_combo.addItem(f"{name} ({code})")
