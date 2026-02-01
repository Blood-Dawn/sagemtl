"""
Dialog windows for the application.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QDialogButtonBox,
    QFormLayout, QLineEdit, QSpinBox, QTableWidget,
    QTableWidgetItem, QAbstractItemView
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

        layout.addLayout(form)

        # Note
        note = QLabel(
            "Note: This will use lightnovel-crawler to download chapters from the novel site.\n"
            "All chapters will be automatically detected and downloaded.\n"
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
            "<li>Novel crawling with SageCrawler</li>"
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


class SearchResultsDialog(QDialog):
    """Dialog for displaying and selecting from novel search results"""

    def __init__(self, results, parent=None):
        """
        Initialize search results dialog.
        
        Args:
            results: List of dicts with keys: title, url, site
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Select Novel")
        self.setMinimumSize(700, 400)
        self.results = results
        self.selected_result = None
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"<b>Found {len(self.results)} results. Select one to download:</b>")
        layout.addWidget(header)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Title", "Site", "URL"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Populate table
        for row, result in enumerate(self.results):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(result.get('title', 'Unknown')))
            self.table.setItem(row, 1, QTableWidgetItem(result.get('site', 'Unknown')))
            self.table.setItem(row, 2, QTableWidgetItem(result.get('url', '')))
        
        # Auto-resize columns
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_ok(self):
        """Handle OK button"""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            error_dialog = QDialog(self)
            error_dialog.setWindowTitle("No Selection")
            error_layout = QVBoxLayout(error_dialog)
            error_layout.addWidget(QLabel("Please select a novel from the list."))
            error_dialog.exec()
            return
        
        # Get selected row
        row = selected_rows[0].row()
        self.selected_result = self.results[row]
        self.accept()

    def get_selected_result(self):
        """Get the selected result"""
        return self.selected_result

class SearchProgressDialog(QDialog):
    """Non-modal dialog showing search progress in real-time"""

    def __init__(self, novel_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Searching for Novel")
        self.setMinimumSize(600, 300)
        self.setModal(False)
        self.novel_name = novel_name
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"<b>Searching for: {self.novel_name}</b>")
        title.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title)

        # Instructions
        info = QLabel(
            "lncrawler is searching across hundreds of novel sites...\n"
            "This may take a few minutes. Results will appear below."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info)

        # Progress log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "background-color: #f0f0f0; font-family: monospace; font-size: 10px;"
        )
        layout.addWidget(self.log_text)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def add_log_line(self, message: str, level: str = "info"):
        """Add a line to the log"""
        # Format message with level prefix if error
        formatted_msg = f"[ERROR] {message}" if level == "error" else message
        
        current = self.log_text.toPlainText()
        if current:
            self.log_text.setPlainText(current + "\n" + formatted_msg)
        else:
            self.log_text.setPlainText(formatted_msg)
        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def clear_log(self):
        """Clear the log"""
        self.log_text.clear()


class DownloadProgressDialog(QDialog):
    """Non-modal dialog showing download progress in real-time"""

    def __init__(self, novel_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading Novel")
        self.setMinimumSize(600, 300)
        self.setModal(False)
        self.novel_title = novel_title
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"<b>Downloading: {self.novel_title}</b>")
        title.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title)

        # Status label
        self.status_label = QLabel("Initializing download...")
        self.status_label.setStyleSheet("color: #333;")
        layout.addWidget(self.status_label)

        # Progress log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "background-color: #f0f0f0; font-family: monospace; font-size: 10px;"
        )
        layout.addWidget(self.log_text)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def set_status(self, status: str):
        """Update status label"""
        self.status_label.setText(status)

    def add_log_line(self, message: str, level: str = "info"):
        """Add a line to the log"""
        # Format message with level prefix if error
        if level == "error":
            formatted_msg = f"[ERROR] {message}"
        else:
            formatted_msg = message
        
        current = self.log_text.toPlainText()
        if current:
            self.log_text.setPlainText(current + "\n" + formatted_msg)
        else:
            self.log_text.setPlainText(formatted_msg)
        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def clear_log(self):
        """Clear the log"""
        self.log_text.clear()