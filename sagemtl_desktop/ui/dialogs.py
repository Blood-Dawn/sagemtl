"""
Dialog windows for the application.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QDialogButtonBox,
    QFormLayout, QLineEdit, QSpinBox
)
from PySide6.QtCore import Qt


class ErrorDialog(QDialog):
    """Dialog for displaying detailed error information"""

    def __init__(self, job_name: str, error_message: str, traceback: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Error: {job_name}")
        self.setMinimumSize(600, 400)
        self._init_ui(job_name, error_message, traceback)

    def _init_ui(self, job_name: str, error_message: str, traceback: str):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"<b>Error processing: {job_name}</b>")
        layout.addWidget(header)

        # Error message
        error_label = QLabel("Error Message:")
        layout.addWidget(error_label)

        error_text = QLabel(error_message)
        error_text.setWordWrap(True)
        error_text.setStyleSheet("color: red; padding: 8px; background: #ffe6e6;")
        layout.addWidget(error_text)

        # Traceback
        traceback_label = QLabel("Detailed Traceback:")
        layout.addWidget(traceback_label)

        traceback_edit = QTextEdit()
        traceback_edit.setPlainText(traceback)
        traceback_edit.setReadOnly(True)
        traceback_edit.setStyleSheet("font-family: monospace; font-size: 10px;")
        layout.addWidget(traceback_edit)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


class CrawlOptionsDialog(QDialog):
    """Dialog for configuring novel crawl options"""

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crawl Novel Options")
        self.setMinimumWidth(500)
        self.url = url
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Form layout
        form = QFormLayout()

        # URL (read-only)
        self.url_edit = QLineEdit(self.url)
        self.url_edit.setReadOnly(True)
        form.addRow("URL:", self.url_edit)

        # Novel name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Novel (optional)")
        form.addRow("Novel Name:", self.name_edit)

        # Start chapter
        self.start_spin = QSpinBox()
        self.start_spin.setMinimum(1)
        self.start_spin.setMaximum(9999)
        self.start_spin.setValue(1)
        form.addRow("Start Chapter:", self.start_spin)

        # End chapter
        self.end_spin = QSpinBox()
        self.end_spin.setMinimum(1)
        self.end_spin.setMaximum(9999)
        self.end_spin.setValue(50)
        form.addRow("End Chapter:", self.end_spin)

        layout.addLayout(form)

        # Note
        note = QLabel(
            "Note: This will use LNCrawl to download chapters from the novel site.\n"
            "The process may take several minutes depending on the number of chapters."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-style: italic; padding: 8px;")
        layout.addWidget(note)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_options(self) -> dict:
        """
        Get crawl options.

        Returns:
            Dictionary with options
        """
        return {
            "url": self.url,
            "novel_name": self.name_edit.text().strip(),
            "start_chapter": self.start_spin.value(),
            "end_chapter": self.end_spin.value(),
        }


class AboutDialog(QDialog):
    """About dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About SageMTL")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h1>SageMTL Desktop</h1>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Version
        version = QLabel("<p>Version 2.0.0</p>")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        # Description
        desc = QLabel(
            "<p>A desktop application for processing bulk machine-translated (MTL) novel text.</p>"
            "<p>Built with PySide6 and Argos Translate for offline translation.</p>"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        # Features
        features = QLabel(
            "<h3>Features:</h3>"
            "<ul>"
            "<li>Offline translation with Argos Translate</li>"
            "<li>Novel crawling with LNCrawl</li>"
            "<li>Custom glossary support (CSV)</li>"
            "<li>EPUB extraction and export</li>"
            "<li>Side-by-side preview</li>"
            "</ul>"
        )
        layout.addWidget(features)

        # Credits
        credits = QLabel(
            "<p><small>Built by the SageMTL Team</small></p>"
        )
        credits.setAlignment(Qt.AlignCenter)
        credits.setStyleSheet("color: gray;")
        layout.addWidget(credits)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
