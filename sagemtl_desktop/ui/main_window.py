"""
Main application window.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QMenuBar, QMenu
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction

from .file_list_panel import FileListPanel
from .preview_panel import PreviewPanel
from .controls_panel import ControlsPanel
from .log_panel import LogPanel
from .dialogs import ErrorDialog, CrawlOptionsDialog, AboutDialog
from .export_dialog import ExportDialog

from ..core import (
    JobManager, Translator, GlossaryProcessor,
    Crawler, EPUBExtractor, Exporter,
    Job, JobType, JobStatus, ProcessingOptions,
    ImportManager, get_logger
)


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SageMTL Desktop - MTL Novel Processor")
        self.setMinimumSize(1200, 800)

        # Settings
        self.settings = QSettings("SageMTL", "SageMTL")

        # Core components
        self.job_manager = JobManager(self)
        self.translator = Translator()
        self.glossary = GlossaryProcessor()
        self.crawler = Crawler()
        self.epub_extractor = EPUBExtractor()
        self.exporter = Exporter()
        self.import_manager = ImportManager()
        self.logger = get_logger()

        # Processing options
        self.processing_options = ProcessingOptions()

        # UI components
        self._init_ui()
        self._connect_signals()
        self._load_settings()

        # Populate available languages
        self._populate_languages()

    def _init_ui(self):
        """Initialize UI"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Menu bar
        self._create_menu_bar()

        # Controls panel at top
        self.controls_panel = ControlsPanel()
        layout.addWidget(self.controls_panel)

        # Main content area
        main_splitter = QSplitter(Qt.Horizontal)

        # Left: File list
        self.file_list_panel = FileListPanel()
        self.file_list_panel.setMaximumWidth(300)
        main_splitter.addWidget(self.file_list_panel)

        # Right: Preview and log
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Preview panel
        self.preview_panel = PreviewPanel()
        right_layout.addWidget(self.preview_panel, stretch=3)

        # Log panel at bottom
        self.log_panel = LogPanel()
        right_layout.addWidget(self.log_panel, stretch=1)

        main_splitter.addWidget(right_widget)

        # Set splitter sizes (300px for file list, rest for preview)
        main_splitter.setSizes([300, 900])

        # Store splitter for persistence
        self.main_splitter = main_splitter

        layout.addWidget(main_splitter)

    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        import_action = QAction("&Import Files...", self)
        import_action.setShortcut("Ctrl+O")
        import_action.triggered.connect(self._on_import_files)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        export_action = QAction("&Export Results...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        clear_action = QAction("&Clear All Jobs", self)
        clear_action.triggered.connect(self._on_clear_jobs)
        edit_menu.addAction(clear_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        """Connect signals and slots"""
        # Controls panel
        self.controls_panel.import_files_clicked.connect(self._on_import_files)
        self.controls_panel.fetch_url_clicked.connect(self._on_fetch_url)
        self.controls_panel.load_glossary_clicked.connect(self._on_load_glossary)
        self.controls_panel.start_processing_clicked.connect(self._on_start_processing)
        self.controls_panel.export_clicked.connect(self._on_export)
        self.controls_panel.source_lang_changed.connect(self._on_source_lang_changed)
        self.controls_panel.target_lang_changed.connect(self._on_target_lang_changed)

        # File list panel
        self.file_list_panel.job_selected.connect(self._on_job_selected)
        self.file_list_panel.job_double_clicked.connect(self._on_job_double_clicked)

        # Job manager
        self.job_manager.job_added.connect(self._on_job_added)
        self.job_manager.job_updated.connect(self._on_job_updated)
        self.job_manager.job_removed.connect(self._on_job_removed)
        self.job_manager.progress_changed.connect(self._on_progress_changed)
        self.job_manager.log_emitted.connect(self._on_log)

    def _populate_languages(self):
        """Populate language dropdowns with available Argos models"""
        if self.translator.is_available():
            available = self.translator.get_available_languages()
            self.controls_panel.populate_languages(available)
        else:
            self.log_panel.add_log(
                "00:00:00", "system", "warn",
                "Argos Translate not available. Install with: pip install argostranslate"
            )

    def _load_settings(self):
        """Load saved settings"""
        # Restore window geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Restore splitter sizes
        splitter_sizes = self.settings.value("splitter_sizes")
        if splitter_sizes:
            try:
                sizes = [int(s) for s in splitter_sizes]
                self.main_splitter.setSizes(sizes)
            except:
                pass

        # Restore language settings
        source_lang = self.settings.value("source_lang", "auto")
        target_lang = self.settings.value("target_lang", "en")
        glossary_path = self.settings.value("glossary_path")

        # Update processing options
        self.processing_options.source_lang = source_lang
        self.processing_options.target_lang = target_lang

        if glossary_path:
            try:
                self.glossary.load_glossary(glossary_path)
                self.processing_options.glossary_path = glossary_path
            except Exception as e:
                print(f"Failed to load saved glossary: {e}")

    def _save_settings(self):
        """Save settings"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitter_sizes", self.main_splitter.sizes())
        self.settings.setValue("source_lang", self.processing_options.source_lang)
        self.settings.setValue("target_lang", self.processing_options.target_lang)
        if self.processing_options.glossary_path:
            self.settings.setValue("glossary_path", self.processing_options.glossary_path)

    def closeEvent(self, event):
        """Handle window close"""
        # Save settings
        self._save_settings()

        # Stop all jobs
        self.job_manager.stop_all_jobs()

        # Cleanup crawler
        self.crawler.cleanup()

        event.accept()

    # === Slot implementations ===

    def _on_import_files(self):
        """Handle import files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Files",
            "",
            "Supported Files (*.txt *.epub);;Text Files (*.txt);;EPUB Files (*.epub);;All Files (*)"
        )

        if not file_paths:
            return

        self.logger.info(
            f"Starting import of {len(file_paths)} file(s)",
            stage="import",
            file_count=len(file_paths)
        )

        for file_path in file_paths:
            # Read file content
            try:
                # Check for duplicate
                if file_path.endswith('.epub'):
                    # Extract EPUB
                    full_text, chapters = self.epub_extractor.extract(file_path)
                    original_text = full_text
                else:
                    # Read text file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_text = f.read()

                # Check for duplicate using ImportManager
                duplicate_job_id = self.import_manager.is_duplicate(original_text)
                if duplicate_job_id:
                    self.logger.warning(
                        f"Duplicate content detected: {file_path}",
                        stage="import",
                        file_path=file_path,
                        duplicate_of=duplicate_job_id
                    )
                    QMessageBox.information(
                        self,
                        "Duplicate Content",
                        f"File '{os.path.basename(file_path)}' has already been imported.\n"
                        f"Skipping duplicate."
                    )
                    continue

                # Create job
                import os
                job_id = self.job_manager.create_job(
                    JobType.IMPORT_FILE,
                    os.path.basename(file_path),
                    source_file=file_path
                )

                # Store original text
                job = self.job_manager.get_job(job_id)
                job.original_text = original_text
                self.job_manager.update_job(job)

                # Track content hash
                self.import_manager.track_content(original_text, job_id)

                self.logger.info(
                    f"Successfully imported: {os.path.basename(file_path)}",
                    stage="import",
                    job_id=job_id,
                    file_path=file_path,
                    content_length=len(original_text)
                )

            except Exception as e:
                self.logger.error(
                    f"Import failed: {file_path}",
                    stage="import",
                    file_path=file_path,
                    exc_info=e
                )
                QMessageBox.critical(
                    self,
                    "Import Error",
                    f"Failed to import {file_path}:\n{str(e)}"
                )

    def _on_fetch_url(self, url: str):
        """Handle fetch URL"""
        # Show crawl options dialog
        dialog = CrawlOptionsDialog(url, self)
        if dialog.exec():
            options = dialog.get_options()

            self.logger.info(
                f"Starting crawl from URL: {options['url']}",
                stage="crawl",
                url=options['url'],
                novel_name=options.get('novel_name'),
                start_chapter=options.get('start_chapter'),
                end_chapter=options.get('end_chapter')
            )

            # Create crawl job
            job_id = self.job_manager.create_job(
                JobType.CRAWL_URL,
                options.get('novel_name') or url,
                **options
            )

            # Start crawl worker
            def crawl_processor(job, progress_cb, log_cb):
                # Crawl with LNCrawl
                epub_path = self.crawler.crawl_novel(
                    url=options['url'],
                    novel_name=options.get('novel_name'),
                    start_chapter=options.get('start_chapter'),
                    end_chapter=options.get('end_chapter'),
                    progress_callback=progress_cb,
                    log_callback=log_cb
                )

                # Extract EPUB
                log_cb("info", "Extracting EPUB content...")
                full_text, chapters = self.epub_extractor.extract(epub_path)

                # Store in job
                job.original_text = full_text
                job.metadata['chapter_count'] = len(chapters)

                log_cb("info", f"Extracted {len(chapters)} chapters")

                # Log successful crawl
                self.logger.info(
                    f"Crawl completed: {options.get('novel_name', 'Unknown')}",
                    stage="crawl",
                    job_id=job_id,
                    chapter_count=len(chapters),
                    content_length=len(full_text)
                )

            self.job_manager.start_job(job_id, crawl_processor)

    def _on_load_glossary(self, path: str):
        """Handle load glossary"""
        try:
            result = self.glossary.load_glossary(path)
            self.processing_options.glossary_path = path

            entry_count = result['entries_loaded']

            self.log_panel.add_log(
                "system", "system", "info",
                f"Loaded glossary: {path}"
            )

            self.logger.info(
                f"Glossary loaded: {path}",
                stage="glossary",
                glossary_path=path,
                entry_count=entry_count,
                warnings=len(result['warnings'])
            )

            # Show warnings if any
            if result['warnings']:
                warning_msg = "Glossary loaded with warnings:\n\n"
                warning_msg += "\n".join(f"• {w}" for w in result['warnings'])
                warning_msg += f"\n\nLoaded {entry_count} entries successfully."

                QMessageBox.warning(
                    self,
                    "Glossary Warnings",
                    warning_msg
                )
            else:
                QMessageBox.information(
                    self,
                    "Glossary Loaded",
                    f"Successfully loaded {entry_count} glossary entries."
                )

        except Exception as e:
            self.logger.error(
                f"Failed to load glossary: {path}",
                stage="glossary",
                glossary_path=path,
                exc_info=e
            )
            QMessageBox.critical(
                self,
                "Glossary Error",
                f"Failed to load glossary:\n{str(e)}"
            )

    def _on_start_processing(self):
        """Handle start processing"""
        # Get all pending jobs
        jobs = [j for j in self.job_manager.get_all_jobs() if j.status == JobStatus.PENDING]

        if not jobs:
            QMessageBox.information(
                self,
                "No Jobs",
                "No pending jobs to process."
            )
            return

        self.logger.info(
            f"Starting batch processing of {len(jobs)} job(s)",
            stage="processing",
            job_count=len(jobs),
            source_lang=self.processing_options.source_lang,
            target_lang=self.processing_options.target_lang,
            glossary_loaded=self.glossary.is_loaded()
        )

        # Disable processing button
        self.controls_panel.set_processing_enabled(False)

        # Process each job
        for job in jobs:
            self._process_job(job.job_id)

    def _process_job(self, job_id: str):
        """Process a single job"""
        job = self.job_manager.get_job(job_id)

        self.logger.info(
            f"Starting translation job: {job.name}",
            stage="processing",
            job_id=job_id,
            content_length=len(job.original_text)
        )

        def translate_processor(job, progress_cb, log_cb):
            # Step 1: Apply glossary before
            if self.glossary.is_loaded():
                log_cb("info", "Applying glossary (before translation)...")
                text = self.glossary.apply_before(job.original_text)
            else:
                text = job.original_text

            # Step 2: Translate
            if self.translator.is_available():
                log_cb("info", "Translating...")
                translated = self.translator.translate(
                    text,
                    self.processing_options.source_lang,
                    self.processing_options.target_lang,
                    progress_callback=progress_cb,
                    log_callback=log_cb
                )
            else:
                log_cb("warn", "Translator not available, skipping translation")
                translated = text

            # Step 3: Apply glossary after
            if self.glossary.is_loaded():
                log_cb("info", "Applying glossary (after translation)...")
                cleaned = self.glossary.apply_after(translated)
            else:
                cleaned = translated

            # Store result
            job.cleaned_text = cleaned
            job.metadata['source_lang'] = self.processing_options.source_lang
            job.metadata['target_lang'] = self.processing_options.target_lang

            # Log completion
            self.logger.info(
                f"Translation job completed: {job.name}",
                stage="processing",
                job_id=job_id,
                result_length=len(cleaned)
            )

        self.job_manager.start_job(job_id, translate_processor)

    def _on_export(self):
        """Handle export"""
        # Get completed jobs
        completed_jobs = [
            j for j in self.job_manager.get_all_jobs()
            if j.status == JobStatus.COMPLETED and j.cleaned_text
        ]

        if not completed_jobs:
            QMessageBox.information(
                self,
                "No Results",
                "No completed jobs to export."
            )
            return

        # Show export dialog
        export_dialog = ExportDialog(self)
        if not export_dialog.exec():
            return  # User cancelled

        # Get selected format and options
        export_format = export_dialog.get_format()
        author = export_dialog.get_author()

        # Select output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )

        if output_dir:
            try:
                # Export with selected format
                if export_format == "epub":
                    exported = self.exporter.export_batch_with_format(
                        completed_jobs, output_dir, format="epub", author=author
                    )
                    format_name = "EPUB"
                else:
                    exported = self.exporter.export_batch(completed_jobs, output_dir)
                    format_name = "TXT"

                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Exported {len(exported)} {format_name} files to:\n{output_dir}"
                )

                # Log the export
                self.logger.info(
                    f"Exported {len(exported)} files as {format_name}",
                    stage="export",
                    file_count=len(exported),
                    format=export_format
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Error",
                    f"Failed to export files:\n{str(e)}"
                )
                self.logger.error(
                    f"Export failed: {str(e)}",
                    stage="export",
                    exc_info=e
                )

    def _on_source_lang_changed(self, lang_code: str):
        """Handle source language change"""
        self.processing_options.source_lang = lang_code

    def _on_target_lang_changed(self, lang_code: str):
        """Handle target language change"""
        self.processing_options.target_lang = lang_code

    def _on_job_selected(self, job_id: str):
        """Handle job selection"""
        job = self.job_manager.get_job(job_id)
        if job:
            self.preview_panel.set_text_pair(job.original_text, job.cleaned_text)

    def _on_job_double_clicked(self, job_id: str):
        """Handle job double click (show error if failed)"""
        job = self.job_manager.get_job(job_id)
        if job and job.status == JobStatus.FAILED:
            dialog = ErrorDialog(
                job.name,
                job.error_message or "Unknown error",
                job.error_traceback or "",
                self
            )
            dialog.exec()

            # Log the error view
            self.logger.info(
                f"User viewed error details for job: {job.name}",
                job_id=job_id,
                stage="ui"
            )

    def _on_job_added(self, job_id: str):
        """Handle job added"""
        job = self.job_manager.get_job(job_id)
        if job:
            self.file_list_panel.add_job(job)

    def _on_job_updated(self, job_id: str):
        """Handle job updated"""
        job = self.job_manager.get_job(job_id)
        if job:
            self.file_list_panel.update_job(job)

            # Re-enable processing button when all jobs are done
            stats = self.job_manager.get_stats()
            if stats['in_progress'] == 0:
                self.controls_panel.set_processing_enabled(True)

    def _on_job_removed(self, job_id: str):
        """Handle job removed"""
        self.file_list_panel.remove_job(job_id)

    def _on_progress_changed(self, job_id: str, progress: float):
        """Handle progress change"""
        # Already handled by job_updated
        pass

    def _on_log(self, timestamp: str, job_id: str, level: str, message: str):
        """Handle log message"""
        self.log_panel.add_log(timestamp, job_id, level, message)

    def _on_clear_jobs(self):
        """Handle clear all jobs"""
        reply = QMessageBox.question(
            self,
            "Clear Jobs",
            "Are you sure you want to clear all jobs?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            jobs = self.job_manager.get_all_jobs()
            job_count = len(jobs)

            self.logger.info(
                f"Clearing {job_count} job(s)",
                stage="ui",
                job_count=job_count
            )

            for job in jobs:
                self.job_manager.remove_job(job.job_id)

            # Clear ImportManager tracking as well
            self.import_manager = ImportManager()

            self.logger.info(
                "All jobs cleared",
                stage="ui"
            )

    def _on_about(self):
        """Handle about dialog"""
        dialog = AboutDialog(self)
        dialog.exec()
