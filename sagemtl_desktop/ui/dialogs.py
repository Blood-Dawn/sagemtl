"""
Dialog windows for the application.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QDialogButtonBox,
    QFormLayout, QLineEdit, QSpinBox, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QFrame,
    QRadioButton, QButtonGroup, QCheckBox, QDoubleSpinBox,
    QHeaderView, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

from sagemtl_desktop.core.crawl_settings import CrawlSettings


def _fit_dialog_to_screen(
    dialog: QDialog,
    width_ratio: float,
    height_ratio: float,
    min_width: int,
    min_height: int
):
    """Resize a dialog to fit the current screen and keep it maximizable."""
    dialog.setWindowFlag(Qt.WindowMinMaxButtonsHint, True)
    dialog.setSizeGripEnabled(True)

    screen = dialog.screen() or QApplication.primaryScreen()
    if not screen:
        dialog.resize(min_width, min_height)
        return

    geometry = screen.availableGeometry()
    width = max(min_width, int(geometry.width() * width_ratio))
    height = max(min_height, int(geometry.height() * height_ratio))
    dialog.resize(min(width, geometry.width()), min(height, geometry.height()))


class ErrorDialog(QDialog):
    """Dialog for displaying detailed error information"""

    def __init__(
        self,
        job_name: str,
        error_message: str,
        traceback: str,
        recovery_hints: list[str] | None = None,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Error: {job_name}")
        self.setMinimumSize(600, 400)
        self._init_ui(job_name, error_message, traceback, recovery_hints or [])

    def _init_ui(self, job_name: str, error_message: str, traceback: str, recovery_hints: list[str]):
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

        if recovery_hints:
            hints_label = QLabel("Suggested Recovery Steps:")
            layout.addWidget(hints_label)

            hints_text = QLabel("\n".join(f"- {hint}" for hint in recovery_hints))
            hints_text.setWordWrap(True)
            hints_text.setStyleSheet("padding: 8px; background: #eef7ff; color: #1e3a5f;")
            layout.addWidget(hints_text)

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

    def __init__(
        self,
        url: str,
        initial_settings: CrawlSettings | None = None,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Crawl Novel Options")
        self.setMinimumWidth(560)
        _fit_dialog_to_screen(self, width_ratio=0.55, height_ratio=0.70, min_width=560, min_height=520)
        self.url = url
        self.initial_settings = (initial_settings or CrawlSettings()).normalize()
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

        # Crawl policy controls
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setDecimals(2)
        self.delay_spin.setMinimum(0.0)
        self.delay_spin.setMaximum(10.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setValue(self.initial_settings.request_delay_seconds)
        self.delay_spin.setSuffix(" s")
        self.delay_spin.setToolTip(
            "Delay between HTTP requests.\n"
            "Higher values reduce rate-limit/anti-bot risk but slow crawling."
        )
        form.addRow("Request Delay:", self.delay_spin)

        self.retries_spin = QSpinBox()
        self.retries_spin.setMinimum(0)
        self.retries_spin.setMaximum(10)
        self.retries_spin.setValue(self.initial_settings.max_retries)
        self.retries_spin.setToolTip(
            "Number of retry attempts per failed request."
        )
        form.addRow("Retries:", self.retries_spin)

        self.workers_spin = QSpinBox()
        self.workers_spin.setMinimum(1)
        self.workers_spin.setMaximum(16)
        self.workers_spin.setValue(self.initial_settings.chapter_download_workers)
        self.workers_spin.setToolTip(
            "Concurrent chapter downloads (generic crawler path).\n"
            "Higher values are faster, but can trigger rate limits."
        )
        form.addRow("Download Workers:", self.workers_spin)

        self.user_agent_edit = QLineEdit(self.initial_settings.user_agent)
        self.user_agent_edit.setPlaceholderText("User agent for crawl requests")
        self.user_agent_edit.setToolTip(
            "HTTP User-Agent header used for crawling requests."
        )
        form.addRow("User-Agent:", self.user_agent_edit)

        self.robots_override_check = QCheckBox("Ignore robots.txt restrictions")
        self.robots_override_check.setChecked(self.initial_settings.ignore_robots_txt)
        self.robots_override_check.setToolTip(
            "Bypass robots.txt policy checks for this site."
        )
        form.addRow("", self.robots_override_check)

        self.resume_check = QCheckBox("Resume existing novel by source URL when available")
        self.resume_check.setChecked(self.initial_settings.resume_existing)
        self.resume_check.setToolTip(
            "Merge into an existing library novel with the same source URL."
        )
        form.addRow("", self.resume_check)

        self.auto_export_epub_check = QCheckBox("Auto-export crawled chapters directly to EPUB")
        self.auto_export_epub_check.setChecked(self.initial_settings.auto_export_epub)
        self.auto_export_epub_check.setToolTip(
            "Automatically write EPUB output after crawl completes."
        )
        form.addRow("", self.auto_export_epub_check)

        layout.addLayout(form)

        # Note
        note = QLabel(
            "What each option does:\n"
            "- Request Delay: pause between requests to avoid rate limits.\n"
            "- Retries: retry attempts for transient failures/timeouts.\n"
            "- Download Workers: parallel chapter fetch count.\n"
            "- Ignore robots.txt: bypass robots policy checks.\n"
            "- Resume existing novel: merge by source URL instead of duplicating.\n"
            "- Auto-export EPUB: write EPUB automatically after crawl.\n\n"
            "Settings are saved per-site and reused for future crawls on the same domain."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; padding: 8px;")
        layout.addWidget(note)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Help
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.helpRequested.connect(self._show_help)
        layout.addWidget(button_box)

    def _show_help(self):
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Crawl Option Help")
        _fit_dialog_to_screen(help_dialog, width_ratio=0.60, height_ratio=0.60, min_width=680, min_height=500)
        layout = QVBoxLayout(help_dialog)

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml(
            "<h3>Crawl Option Guide</h3>"
            "<p><b>Request Delay</b>: Adds a pause between requests. Increase this if a site blocks or times out.</p>"
            "<p><b>Retries</b>: Number of extra attempts when a request fails.</p>"
            "<p><b>Download Workers</b>: Parallel chapter requests. More workers are faster but can trip anti-bot limits.</p>"
            "<p><b>User-Agent</b>: HTTP client identity string.</p>"
            "<p><b>Ignore robots.txt restrictions</b>: Overrides robots policy checks (use carefully).</p>"
            "<p><b>Resume existing novel by source URL</b>: Reuses existing novel entry and appends missing chapters.</p>"
            "<p><b>Auto-export crawled chapters directly to EPUB</b>: Writes EPUB automatically after crawl.</p>"
            "<p><b>Flow</b>: Search URL/name -> discover chapters -> review chapter count/list -> choose selection -> download.</p>"
        )
        layout.addWidget(help_text)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(help_dialog.accept)
        layout.addWidget(close_btn)

        help_dialog.exec()

    def get_options(self) -> dict:
        """
        Get crawl options.

        Returns:
            Dictionary with options
        """
        return {
            "url": self.url,
            "novel_name": self.name_edit.text().strip(),
            "crawl_settings": CrawlSettings(
                request_delay_seconds=self.delay_spin.value(),
                user_agent=self.user_agent_edit.text().strip(),
                max_retries=self.retries_spin.value(),
                ignore_robots_txt=self.robots_override_check.isChecked(),
                chapter_download_workers=self.workers_spin.value(),
                resume_existing=self.resume_check.isChecked(),
                auto_export_epub=self.auto_export_epub_check.isChecked(),
                epub_output_dir=self.initial_settings.epub_output_dir,
            ).normalize().to_dict(),
        }


class BatchCrawlDialog(QDialog):
    """Dialog for batch crawling URLs from a list/queue input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Crawl URLs")
        self.setMinimumSize(700, 420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        help_text = QLabel(
            "Paste one URL per line (or comma/semicolon separated). "
            "Batch crawl runs as a queued background job."
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        self.urls_input = QTextEdit()
        self.urls_input.setPlaceholderText(
            "https://example.com/novel-1\nhttps://example.com/novel-2"
        )
        layout.addWidget(self.urls_input)

        form = QFormLayout()

        self.max_chapters_spin = QSpinBox()
        self.max_chapters_spin.setMinimum(0)
        self.max_chapters_spin.setMaximum(5000)
        self.max_chapters_spin.setValue(0)
        self.max_chapters_spin.setSpecialValueText("All chapters")
        form.addRow("Per-URL Chapter Cap:", self.max_chapters_spin)

        layout.addLayout(form)

        note = QLabel(
            "Tip: Use 0 for full novel crawl. Invalid lines are ignored automatically."
        )
        note.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(note)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_options(self) -> dict:
        return {
            "raw_urls": self.urls_input.toPlainText(),
            "max_chapters": self.max_chapters_spin.value(),
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


class HelpGuideDialog(QDialog):
    """Detailed usage guide dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SageMTL Help Guide")
        _fit_dialog_to_screen(self, width_ratio=0.78, height_ratio=0.82, min_width=900, min_height=680)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("<h2>SageMTL Workflow and Option Guide</h2>")
        layout.addWidget(header)

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml(
            "<h3>1) Search and Crawl Workflow</h3>"
            "<ul>"
            "<li>Enter a novel name to search supported sources, or paste a direct URL.</li>"
            "<li>Search results are grouped by novel title first. Open a novel to view all source sites.</li>"
            "<li>The source-site list auto-prefetches chapter counts for top rows in the background.</li>"
            "<li>Crawl starts with chapter discovery, then chapter selection (all / first N / custom range).</li>"
            "</ul>"
            "<h3>2) Crawl Option Meanings</h3>"
            "<ul>"
            "<li><b>Request Delay</b>: pause between requests; higher values are safer for strict sites.</li>"
            "<li><b>Retries</b>: additional attempts after transient failures/timeouts.</li>"
            "<li><b>Download Workers</b>: parallel chapter download count.</li>"
            "<li><b>User-Agent</b>: request identity string.</li>"
            "<li><b>Ignore robots.txt restrictions</b>: bypass robots policy checks.</li>"
            "<li><b>Resume existing novel by source URL</b>: merge new chapters into existing entry.</li>"
            "<li><b>Auto-export crawled chapters directly to EPUB</b>: export EPUB automatically after crawl.</li>"
            "</ul>"
            "<h3>3) Glossary Behavior</h3>"
            "<ul>"
            "<li>Global terms apply to all novels.</li>"
            "<li>Novel terms apply only to that novel and take precedence.</li>"
            "<li>Glossary terms are applied before and after translation jobs.</li>"
            "</ul>"
            "<h3>4) Search Progress Window</h3>"
            "<ul>"
            "<li>You can hide the search progress window while search continues in the background.</li>"
            "<li>Reopen it from <b>View -> Show Active Search Progress</b>.</li>"
            "</ul>"
            "<h3>5) Novel Rename Behavior</h3>"
            "<ul>"
            "<li>Manual renames are persistent and remain locked across resume crawls for the same URL.</li>"
            "</ul>"
        )
        layout.addWidget(help_text)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class SearchNovelGroupsDialog(QDialog):
    """First-step dialog for grouped novel search results."""

    def __init__(self, groups, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Novel")
        _fit_dialog_to_screen(self, width_ratio=0.74, height_ratio=0.70, min_width=860, min_height=520)
        self.groups = groups or []
        self.selected_group = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel(
            f"<b>Found {len(self.groups)} unique novels. Select one to view available sources:</b>"
        )
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Novel", "Sites", "Known Chapters"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemDoubleClicked.connect(lambda *_: self._on_ok())

        for row, group in enumerate(self.groups):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(group.get("title", "Unknown")))

            site_count_item = QTableWidgetItem(str(group.get("site_count", 0)))
            site_count_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, site_count_item)

            chapter_summary_item = QTableWidgetItem(
                str(group.get("chapter_count_summary", "Unknown"))
            )
            chapter_summary_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, chapter_summary_item)

        header_ctrl = self.table.horizontalHeader()
        header_ctrl.setSectionResizeMode(0, QHeaderView.Stretch)
        header_ctrl.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_ctrl.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        tip_label = QLabel(
            "Tip: The next screen shows site URLs for the selected novel and auto-checks chapter counts."
        )
        tip_label.setStyleSheet("color: gray;")
        layout.addWidget(tip_label)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        open_sites_btn = button_box.button(QDialogButtonBox.Ok)
        if open_sites_btn:
            open_sites_btn.setText("View Sources")
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_ok(self):
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            error_dialog = QDialog(self)
            error_dialog.setWindowTitle("No Selection")
            error_layout = QVBoxLayout(error_dialog)
            error_layout.addWidget(QLabel("Please select a novel from the list."))
            error_dialog.exec()
            return

        row = selected_rows[0].row()
        self.selected_group = self.groups[row]
        self.accept()

    def get_selected_group(self):
        return self.selected_group


class ChapterCountWorker(QThread):
    """Background worker for chapter count discovery on a selected search result."""

    finished_count = Signal(int, object)  # row index, chapter count or None
    failed_count = Signal(int, str)       # row index, error message

    def __init__(self, row: int, result: dict, resolver, parent=None):
        super().__init__(parent)
        self.row = row
        self.result = result
        self.resolver = resolver

    def run(self):
        try:
            count = self.resolver(self.result)
            self.finished_count.emit(self.row, count)
        except Exception as exc:
            self.failed_count.emit(self.row, str(exc))


class SearchResultsDialog(QDialog):
    """Dialog for displaying and selecting from novel search results"""

    def __init__(
        self,
        results,
        parent=None,
        chapter_count_resolver=None,
        novel_title: str | None = None,
        auto_prefetch_rows: list[int] | None = None,
    ):
        """
        Initialize search results dialog.
        
        Args:
            results: List of dicts with keys: title, url, site, optional chapter_count
            parent: Parent widget
            chapter_count_resolver: Optional callable(result_dict) -> int|None
            novel_title: Optional selected grouped novel title for header text
            auto_prefetch_rows: Optional ordered row indexes to prefetch in background
        """
        super().__init__(parent)
        self.setWindowTitle("Select Source")
        _fit_dialog_to_screen(self, width_ratio=0.80, height_ratio=0.75, min_width=900, min_height=560)
        self.results = results
        self.novel_title = (novel_title or "").strip()
        self.selected_result = None
        self.chapter_count_resolver = chapter_count_resolver
        self._count_worker = None
        self._count_mode = "manual"
        self._prefetch_queue = list(auto_prefetch_rows or [])
        self._prefetch_total = len(self._prefetch_queue)
        self._prefetch_done = 0
        self._init_ui()
        if self._prefetch_queue and callable(self.chapter_count_resolver):
            QTimer.singleShot(0, self._start_next_prefetch)

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        if self.novel_title:
            header_text = (
                f"<b>Found {len(self.results)} sources for '{self.novel_title}'. "
                "Select one to download:</b>"
            )
        else:
            header_text = f"<b>Found {len(self.results)} sources. Select one to download:</b>"
        header = QLabel(header_text)
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Title", "Site", "URL", "Chapters"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.ElideMiddle)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.itemDoubleClicked.connect(lambda *_: self._on_ok())

        for row, result in enumerate(self.results):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(result.get('title', 'Unknown')))
            self.table.setItem(row, 1, QTableWidgetItem(result.get('site', 'Unknown')))

            url_value = result.get('url', '')
            url_item = QTableWidgetItem(url_value)
            url_item.setToolTip(url_value)
            self.table.setItem(row, 2, url_item)

            chapter_count = result.get('chapter_count')
            chapter_label = str(chapter_count) if isinstance(chapter_count, int) and chapter_count >= 0 else "Unknown"
            chapters_item = QTableWidgetItem(chapter_label)
            chapters_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, chapters_item)

        header_ctrl = self.table.horizontalHeader()
        header_ctrl.setSectionResizeMode(0, QHeaderView.Stretch)
        header_ctrl.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_ctrl.setSectionResizeMode(2, QHeaderView.Stretch)
        header_ctrl.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        actions_row = QHBoxLayout()
        self.chapter_count_status = QLabel(
            "Tip: Select a source and click 'Check Chapters' to preview chapter count."
        )
        self.chapter_count_status.setStyleSheet("color: gray;")
        actions_row.addWidget(self.chapter_count_status, stretch=1)

        self.check_chapters_btn = QPushButton("Check Chapters")
        self.check_chapters_btn.setEnabled(callable(self.chapter_count_resolver))
        self.check_chapters_btn.clicked.connect(self._on_check_chapters)
        actions_row.addWidget(self.check_chapters_btn)
        layout.addLayout(actions_row)

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

        row = selected_rows[0].row()
        self.selected_result = self.results[row]
        self.accept()

    def _on_check_chapters(self):
        """Resolve chapter count for currently selected source URL."""
        if not callable(self.chapter_count_resolver):
            return
        if self._count_worker and self._count_worker.isRunning():
            return

        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            self.chapter_count_status.setText("Select a source row first.")
            return

        row = selected_rows[0].row()
        if row in self._prefetch_queue:
            self._prefetch_queue = [idx for idx in self._prefetch_queue if idx != row]
        self._start_count_worker(row, mode="manual", status_text="Checking chapter count...")

    def _start_count_worker(self, row: int, mode: str, status_text: str):
        self._count_mode = mode
        self.check_chapters_btn.setEnabled(False)
        self.chapter_count_status.setText(status_text)

        self._count_worker = ChapterCountWorker(
            row=row,
            result=self.results[row],
            resolver=self.chapter_count_resolver,
            parent=self
        )
        self._count_worker.finished_count.connect(self._on_chapter_count_ready)
        self._count_worker.failed_count.connect(self._on_chapter_count_failed)
        self._count_worker.start()

    def _start_next_prefetch(self):
        if not callable(self.chapter_count_resolver):
            self._prefetch_queue = []
            self._prefetch_total = 0
            return
        if self._count_worker and self._count_worker.isRunning():
            return
        if not self._prefetch_queue:
            if self._prefetch_total > 0:
                self.chapter_count_status.setText("Auto chapter-count prefetch complete.")
            self.check_chapters_btn.setEnabled(callable(self.chapter_count_resolver))
            return

        next_row = self._prefetch_queue.pop(0)
        progress_text = (
            f"Prefetching chapter counts ({self._prefetch_done + 1}/{self._prefetch_total})..."
        )
        self._start_count_worker(next_row, mode="auto", status_text=progress_text)

    def _on_chapter_count_ready(self, row: int, chapter_count):
        mode = self._count_mode

        if 0 <= row < len(self.results):
            self.results[row]['chapter_count'] = chapter_count

        label = str(chapter_count) if isinstance(chapter_count, int) and chapter_count >= 0 else "Unknown"
        item = self.table.item(row, 3)
        if item is None:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item)
        item.setText(label)

        self._count_worker = None
        if mode == "auto":
            self._prefetch_done += 1
            self._start_next_prefetch()
            return

        self.chapter_count_status.setText(f"Chapter count updated: {label}")
        self.check_chapters_btn.setEnabled(callable(self.chapter_count_resolver))
        if self._prefetch_queue:
            self._start_next_prefetch()

    def _on_chapter_count_failed(self, row: int, error_text: str):
        mode = self._count_mode
        del row
        self._count_worker = None
        if mode == "auto":
            self._prefetch_done += 1
            self.chapter_count_status.setText(f"Prefetch skipped one source: {error_text}")
            self._start_next_prefetch()
            return

        self.chapter_count_status.setText(f"Could not check chapter count: {error_text}")
        self.check_chapters_btn.setEnabled(callable(self.chapter_count_resolver))
        if self._prefetch_queue:
            self._start_next_prefetch()

    def get_selected_result(self):
        """Get the selected result"""
        return self.selected_result

class SearchProgressDialog(QDialog):
    """Non-modal dialog showing search progress in real-time"""

    def __init__(self, novel_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Searching for Novel")
        _fit_dialog_to_screen(self, width_ratio=0.68, height_ratio=0.65, min_width=700, min_height=450)
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
            "This may take a few minutes. Results will appear below.\n"
            "You can hide this window and reopen it from View > Show Active Search Progress."
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

        # Hide button
        close_btn = QPushButton("Hide")
        close_btn.clicked.connect(self.hide)
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
        _fit_dialog_to_screen(self, width_ratio=0.65, height_ratio=0.60, min_width=700, min_height=360)
        self.setModal(False)
        self.novel_title = novel_title
        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"<b>{self.novel_title}</b>")
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
        _fit_dialog_to_screen(self, width_ratio=0.72, height_ratio=0.74, min_width=760, min_height=520)
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
