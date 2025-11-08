"""
Side-by-side text preview panel.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QSplitter
)
from PySide6.QtCore import Qt


class PreviewPanel(QWidget):
    """Widget displaying original and cleaned text side-by-side"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("Preview")
        header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        layout.addWidget(header)

        # Splitter for side-by-side views
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Original text
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(4, 4, 4, 4)

        left_label = QLabel("Original Text")
        left_label.setStyleSheet("font-weight: bold; color: #666;")
        left_layout.addWidget(left_label)

        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setPlaceholderText("Original text will appear here...")
        left_layout.addWidget(self.original_text)

        splitter.addWidget(left_container)

        # Right panel - Cleaned/Translated text
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(4, 4, 4, 4)

        right_label = QLabel("Cleaned/Translated Text")
        right_label.setStyleSheet("font-weight: bold; color: #666;")
        right_layout.addWidget(right_label)

        self.cleaned_text = QTextEdit()
        self.cleaned_text.setReadOnly(True)
        self.cleaned_text.setPlaceholderText("Cleaned text will appear here...")
        right_layout.addWidget(self.cleaned_text)

        splitter.addWidget(right_container)

        # Equal split
        splitter.setSizes([500, 500])

        layout.addWidget(splitter)

    def set_original_text(self, text: str):
        """
        Set original text.

        Args:
            text: Original text
        """
        self.original_text.setPlainText(text)

    def set_cleaned_text(self, text: str):
        """
        Set cleaned/translated text.

        Args:
            text: Cleaned text
        """
        self.cleaned_text.setPlainText(text)

    def clear(self):
        """Clear both text areas"""
        self.original_text.clear()
        self.cleaned_text.clear()

    def set_text_pair(self, original: str, cleaned: str):
        """
        Set both text areas at once.

        Args:
            original: Original text
            cleaned: Cleaned text
        """
        self.set_original_text(original)
        self.set_cleaned_text(cleaned)
