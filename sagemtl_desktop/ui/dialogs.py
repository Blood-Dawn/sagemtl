"""
Dialog windows for the application.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QDialogButtonBox,
    QFormLayout, QLineEdit, QSpinBox, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QFrame,
    QRadioButton, QButtonGroup
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
            "Note: SageMTL first discovers chapters, then lets you choose all, first N, or a custom range.\n"
            "Downloads use the crawler wrapper with generic fallback for unsupported sites.\n"
            "The process may take several minutes depending on chapter count and site speed."
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
            "<li>Novel crawling with lightnovel-crawler and generic fallback</li>"
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
        self.setMinimumSize(650, 400)
        self.setModal(False)
        self.novel_name = novel_name
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Title - dark theme
        title = QLabel(f"<b>Searching for: {self.novel_name}</b>")
        title.setStyleSheet("font-size: 14px; margin-bottom: 10px; color: #e0e0e0;")
        layout.addWidget(title)

        # Instructions - dark theme
        info = QLabel(
            "lncrawler is searching across hundreds of novel sites...\n"
            "This may take a few minutes. Results will appear below."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #a0a0a0; margin-bottom: 10px;")
        layout.addWidget(info)

        # Progress bar
        from PySide6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate by default
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                background-color: #2d2d2d;
                height: 20px;
                text-align: center;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Progress log - dark theme for readability
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; border: 1px solid #3c3c3c; padding: 8px;"
        )
        layout.addWidget(self.log_text)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def set_progress(self, current: int, total: int):
        """Set progress bar values"""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate

    def add_log_line(self, message: str, level: str = "info"):
        """Add a line to the log"""
        # Format message with color based on level
        if level == "error":
            formatted_msg = f'<span style="color: #f44747;">[ERROR] {message}</span>'
        elif level == "warning":
            formatted_msg = f'<span style="color: #ffcc00;">{message}</span>'
        else:
            formatted_msg = f'<span style="color: #d4d4d4;">{message}</span>'
        
        self.log_text.append(formatted_msg)
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
        title.setStyleSheet("font-size: 14px; margin-bottom: 10px; color: #e0e0e0;")
        layout.addWidget(title)

        # Status label
        self.status_label = QLabel("Initializing download...")
        self.status_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Progress log - dark theme for readability
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; border: 1px solid #3c3c3c; padding: 8px;"
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


class ChapterSelectionDialog(QDialog):
    """Dialog for selecting which chapters to download after discovery"""

    def __init__(self, novel_title: str, chapters: list, parent=None):
        """
        Initialize chapter selection dialog.
        
        Args:
            novel_title: Title of the novel
            chapters: List of (url, title) tuples for discovered chapters
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Select Chapters to Download")
        self.setMinimumSize(600, 450)
        self.setModal(True)
        self.novel_title = novel_title
        self.chapters = chapters
        self.selected_range = None
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Title and info
        title_label = QLabel(f"<b>📖 {self.novel_title}</b>")
        title_label.setStyleSheet("font-size: 16px; margin-bottom: 10px; color: #e0e0e0;")
        layout.addWidget(title_label)

        info_label = QLabel(f"Found <b>{len(self.chapters)}</b> chapters available for download.")
        info_label.setStyleSheet("font-size: 13px; color: #b0b0b0; margin-bottom: 15px;")
        layout.addWidget(info_label)

        # Chapter preview list (scrollable, shows first/last few)
        preview_frame = QFrame()
        preview_frame.setStyleSheet("background-color: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 4px;")
        preview_layout = QVBoxLayout(preview_frame)
        
        preview_label = QLabel("Chapter Preview:")
        preview_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")
        preview_layout.addWidget(preview_label)
        
        # Show first 5 and last 5 chapters
        preview_text = ""
        if len(self.chapters) <= 10:
            for i, (url, title) in enumerate(self.chapters):
                preview_text += f"{i+1}. {title}\n"
        else:
            for i, (url, title) in enumerate(self.chapters[:5]):
                preview_text += f"{i+1}. {title}\n"
            preview_text += f"\n... ({len(self.chapters) - 10} more chapters) ...\n\n"
            for i, (url, title) in enumerate(self.chapters[-5:], len(self.chapters) - 4):
                preview_text += f"{i}. {title}\n"
        
        preview_text_widget = QTextEdit()
        preview_text_widget.setReadOnly(True)
        preview_text_widget.setPlainText(preview_text)
        preview_text_widget.setMaximumHeight(150)
        preview_text_widget.setStyleSheet(
            "background-color: #2d2d2d; color: #d4d4d4; font-family: 'Consolas', monospace; font-size: 11px; border: none;"
        )
        preview_layout.addWidget(preview_text_widget)
        
        layout.addWidget(preview_frame)

        # Selection options
        options_frame = QFrame()
        options_frame.setStyleSheet("background-color: #252525; border: 1px solid #3c3c3c; border-radius: 4px; padding: 10px;")
        options_layout = QVBoxLayout(options_frame)
        
        options_label = QLabel("Select chapters to download:")
        options_label.setStyleSheet("font-weight: bold; color: #e0e0e0; margin-bottom: 10px;")
        options_layout.addWidget(options_label)

        # Radio buttons for selection mode
        self.button_group = QButtonGroup(self)
        
        # Option 1: Download all
        self.all_radio = QRadioButton(f"Download all {len(self.chapters)} chapters")
        self.all_radio.setChecked(True)
        self.all_radio.setStyleSheet("color: #e0e0e0;")
        self.button_group.addButton(self.all_radio)
        options_layout.addWidget(self.all_radio)
        
        # Option 2: Download first N
        first_n_layout = QHBoxLayout()
        self.first_n_radio = QRadioButton("Download first")
        self.first_n_radio.setStyleSheet("color: #e0e0e0;")
        self.button_group.addButton(self.first_n_radio)
        first_n_layout.addWidget(self.first_n_radio)
        
        self.first_n_spin = QSpinBox()
        self.first_n_spin.setMinimum(1)
        self.first_n_spin.setMaximum(len(self.chapters))
        self.first_n_spin.setValue(min(50, len(self.chapters)))
        self.first_n_spin.setStyleSheet("background-color: #3c3c3c; color: #e0e0e0; padding: 4px;")
        first_n_layout.addWidget(self.first_n_spin)
        
        first_n_label = QLabel("chapters")
        first_n_label.setStyleSheet("color: #e0e0e0;")
        first_n_layout.addWidget(first_n_label)
        first_n_layout.addStretch()
        options_layout.addLayout(first_n_layout)
        
        # Option 3: Custom range
        range_layout = QHBoxLayout()
        self.range_radio = QRadioButton("Download from chapter")
        self.range_radio.setStyleSheet("color: #e0e0e0;")
        self.button_group.addButton(self.range_radio)
        range_layout.addWidget(self.range_radio)
        
        self.range_start_spin = QSpinBox()
        self.range_start_spin.setMinimum(1)
        self.range_start_spin.setMaximum(len(self.chapters))
        self.range_start_spin.setValue(1)
        self.range_start_spin.setStyleSheet("background-color: #3c3c3c; color: #e0e0e0; padding: 4px;")
        range_layout.addWidget(self.range_start_spin)
        
        to_label = QLabel("to")
        to_label.setStyleSheet("color: #e0e0e0;")
        range_layout.addWidget(to_label)
        
        self.range_end_spin = QSpinBox()
        self.range_end_spin.setMinimum(1)
        self.range_end_spin.setMaximum(len(self.chapters))
        self.range_end_spin.setValue(len(self.chapters))
        self.range_end_spin.setStyleSheet("background-color: #3c3c3c; color: #e0e0e0; padding: 4px;")
        range_layout.addWidget(self.range_end_spin)
        range_layout.addStretch()
        options_layout.addLayout(range_layout)
        
        layout.addWidget(options_frame)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("padding: 8px 20px;")
        button_layout.addWidget(cancel_btn)
        
        download_btn = QPushButton("📥 Download Selected")
        download_btn.clicked.connect(self._on_download)
        download_btn.setStyleSheet("padding: 8px 20px; background-color: #0d6efd; color: white; font-weight: bold;")
        button_layout.addWidget(download_btn)
        
        layout.addLayout(button_layout)

    def _on_download(self):
        """Handle download button click"""
        if self.all_radio.isChecked():
            self.selected_range = (0, len(self.chapters))
        elif self.first_n_radio.isChecked():
            self.selected_range = (0, self.first_n_spin.value())
        elif self.range_radio.isChecked():
            start = self.range_start_spin.value() - 1  # Convert to 0-indexed
            end = self.range_end_spin.value()
            self.selected_range = (start, end)
        
        self.accept()

    def get_selected_chapters(self):
        """
        Get the selected chapter range.
        
        Returns:
            List of (url, title) tuples for selected chapters, or None if cancelled
        """
        if self.selected_range is None:
            return None
        
        start, end = self.selected_range
        return self.chapters[start:end]
