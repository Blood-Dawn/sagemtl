"""Download view for SageMTL.

This module provides the download view with:
- URL input for novel downloads
- Site search functionality
- Download job queue
- Progress tracking
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QComboBox,
        QPushButton,
        QScrollArea,
        QFrame,
        QProgressBar,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QSizePolicy,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from ..constants import Spacing, Icons, Typography
from ..theme import get_theme_manager
from ..components.buttons import PrimaryButton, SecondaryButton, IconButton


class JobStatus(str, Enum):
    """Download job status."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DownloadJob:
    """Download job information."""

    id: str
    url: str
    title: str
    status: JobStatus
    progress: float  # 0-100
    chapters_total: int
    chapters_downloaded: int
    error: Optional[str] = None


if HAS_PYSIDE6:
    class DownloadView(QWidget):
        """Download view for managing novel downloads.

        Features:
        - URL input with validation
        - Site search
        - Download queue management
        - Progress tracking

        Usage:
            download = DownloadView()
            download.download_started.connect(on_download)
            download.add_job(job)
        """

        download_started = Signal(str)  # Emits URL
        job_paused = Signal(str)  # Emits job ID
        job_resumed = Signal(str)  # Emits job ID
        job_cancelled = Signal(str)  # Emits job ID

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._jobs: List[DownloadJob] = []
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._apply_theme()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        def add_job(self, job: DownloadJob) -> None:
            """Add a download job to the queue."""
            self._jobs.append(job)
            self._refresh_queue()

        def update_job(self, job_id: str, **kwargs) -> None:
            """Update a job's properties."""
            for job in self._jobs:
                if job.id == job_id:
                    for key, value in kwargs.items():
                        if hasattr(job, key):
                            setattr(job, key, value)
                    break
            self._refresh_queue()

        def remove_job(self, job_id: str) -> None:
            """Remove a job from the queue."""
            self._jobs = [j for j in self._jobs if j.id != job_id]
            self._refresh_queue()

        def _setup_ui(self) -> None:
            """Set up the download UI."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
            layout.setSpacing(Spacing.LG)

            # Header
            header = QLabel("Download")
            header.setStyleSheet(f"""
                font-size: {Typography.SIZE_XXL}px;
                font-weight: {Typography.WEIGHT_BOLD};
            """)
            layout.addWidget(header)

            # URL input section
            url_section = self._create_url_section()
            layout.addWidget(url_section)

            # Search section
            search_section = self._create_search_section()
            layout.addWidget(search_section)

            # Queue section
            queue_section = self._create_queue_section()
            layout.addWidget(queue_section, 1)

        def _create_url_section(self) -> QFrame:
            """Create the URL input section."""
            frame = QFrame()
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
            layout.setSpacing(Spacing.SM)

            # Title
            title = QLabel("Download from URL")
            title.setStyleSheet(f"""
                font-size: {Typography.SIZE_LG}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            """)
            layout.addWidget(title)

            # URL input row
            input_row = QHBoxLayout()
            input_row.setSpacing(Spacing.SM)

            self._url_input = QLineEdit()
            self._url_input.setPlaceholderText("Enter novel URL (e.g., https://fanmtl.com/novel/...)")
            self._url_input.returnPressed.connect(self._on_download_clicked)
            input_row.addWidget(self._url_input, 1)

            download_btn = PrimaryButton("Download", Icons.DOWNLOAD.value)
            download_btn.clicked.connect(self._on_download_clicked)
            input_row.addWidget(download_btn)

            layout.addLayout(input_row)

            # Supported sites hint
            hint = QLabel("Supported: FanMTL, Wuxiaworld, Webnovel, NovelUpdates, RoyalRoad, ScribbleHub, LNMTL")
            hint.setStyleSheet(f"font-size: {Typography.SIZE_SM}px;")
            layout.addWidget(hint)

            return frame

        def _create_search_section(self) -> QFrame:
            """Create the search section."""
            frame = QFrame()
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
            layout.setSpacing(Spacing.SM)

            # Title
            title = QLabel("Search Novels")
            title.setStyleSheet(f"""
                font-size: {Typography.SIZE_LG}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            """)
            layout.addWidget(title)

            # Search row
            search_row = QHBoxLayout()
            search_row.setSpacing(Spacing.SM)

            # Site selector
            self._site_combo = QComboBox()
            self._site_combo.addItems([
                "All Sites",
                "FanMTL",
                "Wuxiaworld",
                "Webnovel",
                "NovelUpdates",
                "RoyalRoad",
                "ScribbleHub",
            ])
            self._site_combo.setMinimumWidth(150)
            search_row.addWidget(self._site_combo)

            # Search input
            self._search_input = QLineEdit()
            self._search_input.setPlaceholderText("Search for novels...")
            self._search_input.returnPressed.connect(self._on_search_clicked)
            search_row.addWidget(self._search_input, 1)

            # Search button
            search_btn = SecondaryButton("Search", Icons.SEARCH.value)
            search_btn.clicked.connect(self._on_search_clicked)
            search_row.addWidget(search_btn)

            layout.addLayout(search_row)

            return frame

        def _create_queue_section(self) -> QFrame:
            """Create the download queue section."""
            frame = QFrame()
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
            layout.setSpacing(Spacing.SM)

            # Header row
            header_row = QHBoxLayout()

            title = QLabel("Download Queue")
            title.setStyleSheet(f"""
                font-size: {Typography.SIZE_LG}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            """)
            header_row.addWidget(title)

            header_row.addStretch()

            # Clear completed button
            clear_btn = SecondaryButton("Clear Completed")
            clear_btn.clicked.connect(self._clear_completed)
            header_row.addWidget(clear_btn)

            layout.addLayout(header_row)

            # Queue table
            self._queue_table = QTableWidget()
            self._queue_table.setColumnCount(5)
            self._queue_table.setHorizontalHeaderLabels([
                "Title", "Progress", "Status", "Chapters", "Actions"
            ])
            self._queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self._queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self._queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self._queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            self._queue_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            self._queue_table.setColumnWidth(1, 150)
            self._queue_table.setColumnWidth(2, 100)
            self._queue_table.setColumnWidth(3, 100)
            self._queue_table.setColumnWidth(4, 100)
            self._queue_table.verticalHeader().setVisible(False)
            self._queue_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self._queue_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

            layout.addWidget(self._queue_table)

            return frame

        def _refresh_queue(self) -> None:
            """Refresh the queue table."""
            self._queue_table.setRowCount(len(self._jobs))

            for row, job in enumerate(self._jobs):
                # Title
                title_item = QTableWidgetItem(job.title)
                self._queue_table.setItem(row, 0, title_item)

                # Progress bar
                progress_bar = QProgressBar()
                progress_bar.setValue(int(job.progress))
                progress_bar.setTextVisible(True)
                progress_bar.setFormat(f"{job.progress:.1f}%")
                self._queue_table.setCellWidget(row, 1, progress_bar)

                # Status
                status_item = QTableWidgetItem(job.status.value.title())
                self._queue_table.setItem(row, 2, status_item)

                # Chapters
                chapters_text = f"{job.chapters_downloaded}/{job.chapters_total}"
                chapters_item = QTableWidgetItem(chapters_text)
                self._queue_table.setItem(row, 3, chapters_item)

                # Actions
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 4, 4, 4)
                actions_layout.setSpacing(4)

                if job.status == JobStatus.DOWNLOADING:
                    pause_btn = IconButton(Icons.PAUSE.value, size=24)
                    pause_btn.setToolTip("Pause")
                    pause_btn.clicked.connect(lambda j=job.id: self.job_paused.emit(j))
                    actions_layout.addWidget(pause_btn)
                elif job.status == JobStatus.PAUSED:
                    resume_btn = IconButton(Icons.PLAY.value, size=24)
                    resume_btn.setToolTip("Resume")
                    resume_btn.clicked.connect(lambda j=job.id: self.job_resumed.emit(j))
                    actions_layout.addWidget(resume_btn)

                if job.status != JobStatus.COMPLETED:
                    cancel_btn = IconButton(Icons.CLOSE.value, size=24)
                    cancel_btn.setToolTip("Cancel")
                    cancel_btn.clicked.connect(lambda j=job.id: self._on_cancel_job(j))
                    actions_layout.addWidget(cancel_btn)

                self._queue_table.setCellWidget(row, 4, actions_widget)

        def _on_download_clicked(self) -> None:
            """Handle download button click."""
            url = self._url_input.text().strip()
            if url:
                self.download_started.emit(url)
                self._url_input.clear()

        def _on_search_clicked(self) -> None:
            """Handle search button click."""
            query = self._search_input.text().strip()
            site = self._site_combo.currentText()
            if query:
                # TODO: Implement search functionality
                pass

        def _on_cancel_job(self, job_id: str) -> None:
            """Handle job cancellation."""
            self.job_cancelled.emit(job_id)
            self.remove_job(job_id)

        def _clear_completed(self) -> None:
            """Clear completed jobs from queue."""
            self._jobs = [j for j in self._jobs if j.status != JobStatus.COMPLETED]
            self._refresh_queue()

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            self.setStyleSheet(f"""
                DownloadView {{
                    background-color: {colors.background};
                }}
                QLabel {{
                    color: {colors.text_primary};
                    background-color: transparent;
                }}
                QFrame {{
                    background-color: {colors.surface};
                    border: 1px solid {colors.border};
                    border-radius: {Spacing.RADIUS_MD}px;
                }}
            """)

else:
    class DownloadView:
        """Stub DownloadView when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")
