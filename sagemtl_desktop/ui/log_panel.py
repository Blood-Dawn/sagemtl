"""
Log panel with error tracking and filtering.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QPushButton, QComboBox
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat, QBrush


class LogPanel(QWidget):
    """Widget displaying log messages with filtering and error tracking"""

    # Signals
    log_entry_clicked = Signal(str)  # job_id

    # Log level colors
    LEVEL_COLORS = {
        "info": QColor(200, 200, 200),
        "warn": QColor(255, 200, 100),
        "error": QColor(255, 100, 100),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_entries = []  # List of (timestamp, job_id, level, message)
        self._filter_level = "all"
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with controls
        header_layout = QHBoxLayout()

        header_label = QLabel("Log")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        # Filter dropdown
        filter_label = QLabel("Filter:")
        header_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Info", "Warnings", "Errors"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.filter_combo)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        header_layout.addWidget(clear_btn)

        layout.addLayout(header_layout)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_text)

    def add_log(self, timestamp: str, job_id: str, level: str, message: str):
        """
        Add log entry.

        Args:
            timestamp: Timestamp string (HH:MM:SS)
            job_id: Associated job ID
            level: Log level (info, warn, error)
            message: Log message
        """
        # Store entry
        self._log_entries.append((timestamp, job_id, level, message))

        # Apply filter
        if not self._should_show_level(level):
            return

        # Format message
        formatted = self._format_log_entry(timestamp, job_id, level, message)

        # Get color
        color = self.LEVEL_COLORS.get(level, QColor(255, 255, 255))

        # Append with color
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)

        char_format = QTextCharFormat()
        char_format.setForeground(QBrush(color))

        cursor.insertText(formatted + "\n", char_format)

        # Auto-scroll to bottom
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()

    def clear(self):
        """Clear all log entries"""
        self._log_entries.clear()
        self.log_text.clear()

    def _format_log_entry(self, timestamp: str, job_id: str, level: str, message: str) -> str:
        """Format log entry for display"""
        level_str = level.upper().ljust(5)
        # Truncate job_id to first 8 chars
        job_str = job_id[:8] if job_id else "--------"
        return f"[{timestamp}] [{level_str}] [{job_str}] {message}"

    def _should_show_level(self, level: str) -> bool:
        """Check if log level should be shown based on filter"""
        if self._filter_level == "all":
            return True
        return level.lower() == self._filter_level

    def _on_filter_changed(self, text: str):
        """Handle filter change"""
        self._filter_level = text.lower()
        self._refresh_display()

    def _refresh_display(self):
        """Refresh display with current filter"""
        self.log_text.clear()

        for timestamp, job_id, level, message in self._log_entries:
            if self._should_show_level(level):
                formatted = self._format_log_entry(timestamp, job_id, level, message)
                color = self.LEVEL_COLORS.get(level, QColor(255, 255, 255))

                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.End)

                char_format = QTextCharFormat()
                char_format.setForeground(QBrush(color))

                cursor.insertText(formatted + "\n", char_format)

        # Scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()

    def get_error_logs(self) -> list:
        """
        Get all error log entries.

        Returns:
            List of error log tuples
        """
        return [entry for entry in self._log_entries if entry[2] == "error"]
