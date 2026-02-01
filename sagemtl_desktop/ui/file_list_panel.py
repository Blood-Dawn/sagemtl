"""
File/Job list panel widget with novel folder support.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QSplitter, QFrame, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QIcon, QFont, QAction

from ..core.models import Job, JobStatus


class FileListPanel(QWidget):
    """Widget displaying list of jobs/files and saved novels with status indicators"""

    # Signals
    job_selected = Signal(str)  # job_id
    job_double_clicked = Signal(str)  # job_id
    novel_selected = Signal(str)  # novel_id
    chapter_selected = Signal(str, str)  # novel_id, chapter_id
    novel_delete_requested = Signal(str)  # novel_id

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
        self._novels = {}  # novel_id -> SavedNovel
        self._novel_items = {}  # novel_id -> QTreeWidgetItem
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === NOVEL LIBRARY SECTION ===
        library_frame = QFrame()
        library_layout = QVBoxLayout(library_frame)
        library_layout.setContentsMargins(0, 0, 0, 0)
        
        library_header = QLabel("📚 Novel Library")
        library_header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px; background-color: #2d2d2d;")
        library_layout.addWidget(library_header)
        
        # Tree widget for novels with chapters
        self.novel_tree = QTreeWidget()
        self.novel_tree.setHeaderHidden(True)
        self.novel_tree.setAlternatingRowColors(True)
        self.novel_tree.setIndentation(20)
        self.novel_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.novel_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.novel_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.novel_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.novel_tree.setStyleSheet("""
            QTreeWidget {
                border: none;
                background-color: #1e1e1e;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:hover {
                background-color: #333333;
            }
            QTreeWidget::item:selected {
                background-color: #0d6efd;
            }
        """)
        library_layout.addWidget(self.novel_tree)
        
        # Novel stats
        self.novel_stats_label = QLabel("0 novels saved")
        self.novel_stats_label.setStyleSheet("padding: 4px; color: gray; font-size: 11px;")
        library_layout.addWidget(self.novel_stats_label)
        
        layout.addWidget(library_frame, stretch=2)
        
        # === SEPARATOR ===
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #444;")
        layout.addWidget(separator)
        
        # === ACTIVE JOBS SECTION ===
        jobs_frame = QFrame()
        jobs_layout = QVBoxLayout(jobs_frame)
        jobs_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("📁 Files & Active Jobs")
        header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px; background-color: #2d2d2d;")
        jobs_layout.addWidget(header)

        # List widget for active jobs
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_double_clicked)
        jobs_layout.addWidget(self.list_widget)

        # Stats footer
        self.stats_label = QLabel("0 files")
        self.stats_label.setStyleSheet("padding: 4px; color: gray; font-size: 11px;")
        jobs_layout.addWidget(self.stats_label)
        
        layout.addWidget(jobs_frame, stretch=1)

    # === NOVEL LIBRARY METHODS ===
    
    def add_novel(self, novel):
        """
        Add a saved novel to the library tree.

        Args:
            novel: SavedNovel object
        """
        self._novels[novel.novel_id] = novel

        # Create tree item for novel
        novel_item = QTreeWidgetItem(self.novel_tree)
        novel_item.setText(0, f"📖 {novel.title}")
        novel_item.setData(0, Qt.UserRole, {'type': 'novel', 'novel_id': novel.novel_id})
        
        # Style the novel title
        font = novel_item.font(0)
        font.setBold(True)
        novel_item.setFont(0, font)
        novel_item.setForeground(0, QBrush(QColor(200, 200, 255)))
        
        # Add tooltip with info
        tooltip = f"{novel.title}\nBy: {novel.author}\nChapters: {len(novel.chapters)}\nSource: {novel.source_url}"
        novel_item.setToolTip(0, tooltip)

        # Add chapters as children
        for chapter in novel.chapters:
            chapter_item = QTreeWidgetItem(novel_item)
            chapter_item.setText(0, f"  📄 {chapter.title}")
            chapter_item.setData(0, Qt.UserRole, {
                'type': 'chapter',
                'novel_id': novel.novel_id,
                'chapter_id': chapter.chapter_id
            })
            chapter_item.setForeground(0, QBrush(QColor(180, 180, 180)))

        self._novel_items[novel.novel_id] = novel_item
        self._update_novel_stats()

    def update_novel(self, novel):
        """Update a novel in the tree"""
        if novel.novel_id in self._novel_items:
            # Remove old item and re-add
            self.remove_novel(novel.novel_id)
        self.add_novel(novel)

    def remove_novel(self, novel_id: str):
        """Remove a novel from the tree"""
        if novel_id in self._novel_items:
            item = self._novel_items[novel_id]
            index = self.novel_tree.indexOfTopLevelItem(item)
            if index >= 0:
                self.novel_tree.takeTopLevelItem(index)
            del self._novel_items[novel_id]
        
        if novel_id in self._novels:
            del self._novels[novel_id]
        
        self._update_novel_stats()

    def clear_novels(self):
        """Clear all novels from the tree"""
        self.novel_tree.clear()
        self._novels.clear()
        self._novel_items.clear()
        self._update_novel_stats()

    def load_novels(self, novels):
        """
        Load multiple novels into the tree.

        Args:
            novels: List of SavedNovel objects
        """
        self.clear_novels()
        for novel in novels:
            self.add_novel(novel)

    def _update_novel_stats(self):
        """Update novel statistics label"""
        count = len(self._novels)
        total_chapters = sum(len(n.chapters) for n in self._novels.values())
        if count == 0:
            self.novel_stats_label.setText("No novels saved")
        elif count == 1:
            self.novel_stats_label.setText(f"1 novel • {total_chapters} chapters")
        else:
            self.novel_stats_label.setText(f"{count} novels • {total_chapters} chapters")

    def _on_tree_item_clicked(self, item, column):
        """Handle tree item click"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        if data['type'] == 'novel':
            self.novel_selected.emit(data['novel_id'])
        elif data['type'] == 'chapter':
            self.chapter_selected.emit(data['novel_id'], data['chapter_id'])

    def _on_tree_item_double_clicked(self, item, column):
        """Handle tree item double click - expand/collapse or select chapter"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        if data['type'] == 'novel':
            # Toggle expand/collapse
            item.setExpanded(not item.isExpanded())
        elif data['type'] == 'chapter':
            # Emit chapter selection for preview
            self.chapter_selected.emit(data['novel_id'], data['chapter_id'])

    def _on_tree_context_menu(self, position):
        """Handle right-click context menu on novel tree"""
        item = self.novel_tree.itemAt(position)
        if not item:
            return
        
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        menu = QMenu(self)
        
        if data['type'] == 'novel':
            novel_id = data['novel_id']
            novel = self._novels.get(novel_id)
            
            # Delete novel action
            delete_action = QAction("🗑️ Delete Novel", self)
            delete_action.triggered.connect(lambda: self._confirm_delete_novel(novel_id))
            menu.addAction(delete_action)
            
            # Show chapter count info
            if novel:
                menu.addSeparator()
                info_action = QAction(f"📊 {len(novel.chapters)} chapters", self)
                info_action.setEnabled(False)
                menu.addAction(info_action)
        
        elif data['type'] == 'chapter':
            # Could add chapter-specific actions here in the future
            novel_id = data['novel_id']
            chapter_id = data['chapter_id']
            
            view_action = QAction("👁️ View Chapter", self)
            view_action.triggered.connect(lambda: self.chapter_selected.emit(novel_id, chapter_id))
            menu.addAction(view_action)
        
        menu.exec_(self.novel_tree.mapToGlobal(position))

    def _confirm_delete_novel(self, novel_id: str):
        """Show confirmation dialog before deleting a novel"""
        novel = self._novels.get(novel_id)
        if not novel:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Novel",
            f"Are you sure you want to delete '{novel.title}'?\n\n"
            f"This will remove {len(novel.chapters)} chapters from your library.\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.novel_delete_requested.emit(novel_id)

    # === JOB MANAGEMENT METHODS (existing functionality) ===

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
