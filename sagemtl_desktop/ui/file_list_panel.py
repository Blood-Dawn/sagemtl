"""
File/Job list panel widget.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QIcon

from ..core.models import Job, JobStatus


class FileListPanel(QWidget):
    """Widget displaying list of jobs/files with status indicators"""

    # Signals
    job_selected = Signal(str)  # job_id
    job_double_clicked = Signal(str)  # job_id

    # Status icons (using Unicode symbols)
    STATUS_ICONS = {
        JobStatus.PENDING: "⏳",      # Hourglass
        JobStatus.IN_PROGRESS: "⟳",   # Refresh/processing
        JobStatus.COMPLETED: "✓",     # Checkmark
        JobStatus.FAILED: "✗",        # X mark
    }

    # Status colors
    STATUS_COLORS = {
        JobStatus.PENDING: QColor(200, 200, 200),      # Gray
        JobStatus.IN_PROGRESS: QColor(100, 150, 255),  # Blue
        JobStatus.COMPLETED: QColor(100, 200, 100),    # Green
        JobStatus.FAILED: QColor(255, 100, 100),       # Red
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._jobs = {}  # job_id -> Job
        self._items = {}  # job_id -> QListWidgetItem
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("Files & Novels")
        header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        layout.addWidget(header)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_double_clicked)
        layout.addWidget(self.list_widget)

        # Stats footer
        self.stats_label = QLabel("0 files")
        self.stats_label.setStyleSheet("padding: 4px; color: gray;")
        layout.addWidget(self.stats_label)

    def add_job(self, job: Job):
        """
        Add job to list.

        Args:
            job: Job to add
        """
        self._jobs[job.job_id] = job

        # Create list item
        item = QListWidgetItem(self.list_widget)
        item.setText(self._format_job_text(job))
        item.setData(Qt.UserRole, job.job_id)

        # Set status color
        self._update_item_appearance(item, job)

        self._items[job.job_id] = item
        self._update_stats()

    def update_job(self, job: Job):
        """
        Update job in list.

        Args:
            job: Updated job
        """
        self._jobs[job.job_id] = job

        if job.job_id in self._items:
            item = self._items[job.job_id]
            item.setText(self._format_job_text(job))
            self._update_item_appearance(item, job)
            self._update_stats()

    def remove_job(self, job_id: str):
        """
        Remove job from list.

        Args:
            job_id: Job ID
        """
        if job_id in self._items:
            item = self._items[job_id]
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)
            del self._items[job_id]

        if job_id in self._jobs:
            del self._jobs[job_id]

        self._update_stats()

    def get_selected_job_id(self) -> str:
        """
        Get currently selected job ID.

        Returns:
            Job ID or None
        """
        current = self.list_widget.currentItem()
        if current:
            return current.data(Qt.UserRole)
        return None

    def clear(self):
        """Clear all jobs"""
        self.list_widget.clear()
        self._jobs.clear()
        self._items.clear()
        self._update_stats()

    def _format_job_text(self, job: Job) -> str:
        """Format job text for display"""
        icon = self.STATUS_ICONS.get(job.status, "")
        name = job.name

        # Add progress for in-progress jobs
        if job.status == JobStatus.IN_PROGRESS:
            return f"{icon} {name} ({job.progress:.0f}%)"
        else:
            return f"{icon} {name}"

    def _update_item_appearance(self, item: QListWidgetItem, job: Job):
        """Update item color and style based on job status"""
        color = self.STATUS_COLORS.get(job.status, QColor(0, 0, 0))

        # Set foreground color
        brush = QBrush(color)
        item.setForeground(brush)

        # Make failed jobs bold
        if job.status == JobStatus.FAILED:
            font = item.font()
            font.setBold(True)
            item.setFont(font)

    def _update_stats(self):
        """Update statistics footer"""
        total = len(self._jobs)
        completed = sum(1 for j in self._jobs.values() if j.status == JobStatus.COMPLETED)
        failed = sum(1 for j in self._jobs.values() if j.status == JobStatus.FAILED)
        in_progress = sum(1 for j in self._jobs.values() if j.status == JobStatus.IN_PROGRESS)

        stats_text = f"{total} files"
        if in_progress > 0:
            stats_text += f" • {in_progress} processing"
        if completed > 0:
            stats_text += f" • {completed} done"
        if failed > 0:
            stats_text += f" • {failed} failed"

        self.stats_label.setText(stats_text)

    def _on_selection_changed(self, current, previous):
        """Handle selection change"""
        if current:
            job_id = current.data(Qt.UserRole)
            self.job_selected.emit(job_id)

    def _on_double_clicked(self, item):
        """Handle double click"""
        job_id = item.data(Qt.UserRole)
        self.job_double_clicked.emit(job_id)
