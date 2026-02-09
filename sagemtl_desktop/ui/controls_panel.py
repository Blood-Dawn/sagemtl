"""
Controls and settings panel - simplified to just URL fetch.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout,
    QPushButton, QLabel, QLineEdit
)
from PySide6.QtCore import Signal


class ControlsPanel(QWidget):
    """Widget containing URL fetch control - compact toolbar style"""

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
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # URL label
        url_label = QLabel("URL or Name:")
        layout.addWidget(url_label)

        # URL input - stretches to fill available space
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/novel or search for novel name")
        self.url_input.returnPressed.connect(self._on_fetch_url)
        self.url_input.setMinimumWidth(400)
        layout.addWidget(self.url_input, stretch=1)

        # Fetch button
        fetch_btn = QPushButton("🔍 Fetch")
        fetch_btn.clicked.connect(self._on_fetch_url)
        fetch_btn.setMinimumWidth(80)
        layout.addWidget(fetch_btn)

    def _on_fetch_url(self):
        """Handle fetch URL button"""
        url = self.url_input.text().strip()
        if url:
            self.fetch_url_clicked.emit(url)
            self.url_input.clear()

    def set_processing_enabled(self, enabled: bool):
        """Enable/disable processing - placeholder for compatibility"""
        pass

    def populate_languages(self, available_languages: list):
        """Placeholder for compatibility"""
        pass
