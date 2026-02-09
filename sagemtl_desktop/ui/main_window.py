"""
Main application window.
"""

import contextlib

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QFileDialog, QMessageBox, QDialog, QTextEdit
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction

from .file_list_panel import FileListPanel
from .preview_panel import PreviewPanel
from .controls_panel import ControlsPanel
from .log_panel import LogPanel
from .url_history_panel import URLHistoryPanel
from .dialogs import (
    ErrorDialog, AboutDialog, SearchResultsDialog,
    SearchProgressDialog, DownloadProgressDialog, ChapterSelectionDialog
)
from .export_dialog import ExportDialog
from .glossary_editor import GlossaryEditorDialog, QuickTermDialog
from .translation_viewer import TranslationViewerWindow

from ..core import (
    JobManager, Translator, GlossaryProcessor,
    EPUBExtractor, Exporter,
    JobType, JobStatus, ProcessingOptions,
    ImportManager, CrawlService, get_logger
)
from ..core.novel_library import NovelLibrary
from ..core.glossary_manager import GlossaryManager

# New crawler wrappers
from ..core.lightnovel_crawler_wrapper import (
    LightNovelCrawlerWrapper,
    LIGHTNOVEL_CRAWLER_AVAILABLE
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
        self.epub_extractor = EPUBExtractor()
        self.exporter = Exporter()
        self.import_manager = ImportManager()
        self.crawl_service = CrawlService()
        self.logger = get_logger()
        
        # Novel library for persistent storage
        self.novel_library = NovelLibrary()
        
        # Advanced glossary manager (global + per-novel)
        self.glossary_manager = GlossaryManager()
        self._current_novel_id = None  # Track currently selected novel for glossary

        # Initialize lightnovel-crawler (required)
        self.lightnovel_crawler = None
        if LIGHTNOVEL_CRAWLER_AVAILABLE:
            try:
                self.lightnovel_crawler = LightNovelCrawlerWrapper()
            except ImportError:
                self.lightnovel_crawler = None
        if self.lightnovel_crawler is None:
            QMessageBox.critical(
                self,
                "LightNovel-Crawler Missing",
                "lightnovel-crawler is required. Please install it via pip:\n\n    pip install lightnovel-crawler"
            )

        # Processing options
        self.processing_options = ProcessingOptions()

        # UI components
        self._init_ui()
        self._connect_signals()
        self._load_settings()

        # Populate available languages
        self._populate_languages()

    def _init_ui(self):
        """Initialize UI - Modern layout with URL history"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Menu bar
        self._create_menu_bar()

        # Main content area - horizontal splitter
        main_splitter = QSplitter(Qt.Horizontal)

        # Left: Novel library panel
        self.file_list_panel = FileListPanel()
        self.file_list_panel.setMinimumWidth(200)
        self.file_list_panel.setMaximumWidth(400)
        main_splitter.addWidget(self.file_list_panel)

        # Center: URL History and fetch panel
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        # URL History panel (includes fetch input)
        self.url_history_panel = URLHistoryPanel()
        center_layout.addWidget(self.url_history_panel)
        
        # Log panel at bottom (collapsible)
        self.log_panel = LogPanel()
        self.log_panel.setMinimumHeight(50)
        self.log_panel.setMaximumHeight(200)
        center_layout.addWidget(self.log_panel)
        
        main_splitter.addWidget(center_widget)

        # Hidden preview panel (kept for compatibility, used by translation viewer)
        self.preview_panel = PreviewPanel()
        self.preview_panel.hide()
        
        # Hidden controls panel (kept for compatibility)
        self.controls_panel = ControlsPanel()
        self.controls_panel.hide()
        
        # Store splitters
        self.main_splitter = main_splitter
        self.right_splitter = main_splitter  # Compatibility

        # Set splitter sizes (300px for library, rest for center)
        main_splitter.setSizes([300, 900])

        layout.addWidget(main_splitter)

    def _create_menu_bar(self):
        """Create menu bar with all actions organized"""
        menubar = self.menuBar()

        # ===== File menu =====
        file_menu = menubar.addMenu("&File")

        import_action = QAction("📁 &Import Files...", self)
        import_action.setShortcut("Ctrl+O")
        import_action.triggered.connect(self._on_import_files)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        export_action = QAction("💾 &Export Results...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        export_novel_action = QAction("📚 Export &Novel as EPUB...", self)
        export_novel_action.setShortcut("Ctrl+Shift+E")
        export_novel_action.triggered.connect(self._on_export_novel)
        file_menu.addAction(export_novel_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # ===== Edit menu =====
        edit_menu = menubar.addMenu("&Edit")

        clear_action = QAction("🗑️ &Clear All Jobs", self)
        clear_action.triggered.connect(self._on_clear_jobs)
        edit_menu.addAction(clear_action)

        # ===== Glossary menu =====
        glossary_menu = menubar.addMenu("&Glossary")

        glossary_manager_action = QAction("📋 &Glossary Manager...", self)
        glossary_manager_action.setShortcut("Ctrl+G")
        glossary_manager_action.triggered.connect(self._on_open_glossary_manager)
        glossary_menu.addAction(glossary_manager_action)

        glossary_menu.addSeparator()

        load_glossary_action = QAction("📥 &Load Glossary CSV...", self)
        load_glossary_action.triggered.connect(self._on_load_glossary_menu)
        glossary_menu.addAction(load_glossary_action)

        import_glossary_action = QAction("📥 Import to Global...", self)
        import_glossary_action.triggered.connect(self._on_import_glossary_csv)
        glossary_menu.addAction(import_glossary_action)

        export_glossary_action = QAction("📤 Export Glossary CSV...", self)
        export_glossary_action.triggered.connect(self._on_export_glossary_csv)
        glossary_menu.addAction(export_glossary_action)

        glossary_menu.addSeparator()

        apply_glossary_action = QAction("✨ &Apply Glossary to Current Chapter", self)
        apply_glossary_action.setShortcut("Ctrl+Shift+G")
        apply_glossary_action.triggered.connect(self._on_apply_glossary_to_current)
        glossary_menu.addAction(apply_glossary_action)

        apply_all_glossary_action = QAction("✨ Apply Glossary to All Chapters", self)
        apply_all_glossary_action.triggered.connect(self._on_apply_glossary_to_all)
        glossary_menu.addAction(apply_all_glossary_action)

        # ===== Translation menu =====
        translation_menu = menubar.addMenu("&Translation")

        process_action = QAction("▶ &Start Processing", self)
        process_action.setShortcut("Ctrl+P")
        process_action.triggered.connect(self._on_start_processing)
        translation_menu.addAction(process_action)

        translation_menu.addSeparator()

        # Language settings submenu
        lang_submenu = translation_menu.addMenu("🌐 Language Settings")
        
        self.source_auto_action = QAction("Source: Auto-detect", self)
        self.source_auto_action.setCheckable(True)
        self.source_auto_action.setChecked(True)
        lang_submenu.addAction(self.source_auto_action)
        
        lang_submenu.addSeparator()
        
        source_zh_action = QAction("Source: Chinese", self)
        source_zh_action.triggered.connect(lambda: self._set_source_lang("zh"))
        lang_submenu.addAction(source_zh_action)
        
        source_ja_action = QAction("Source: Japanese", self)
        source_ja_action.triggered.connect(lambda: self._set_source_lang("ja"))
        lang_submenu.addAction(source_ja_action)
        
        source_ko_action = QAction("Source: Korean", self)
        source_ko_action.triggered.connect(lambda: self._set_source_lang("ko"))
        lang_submenu.addAction(source_ko_action)

        # ===== View menu =====
        view_menu = menubar.addMenu("&View")

        self.toggle_log_action = QAction("📋 Show &Log Panel", self)
        self.toggle_log_action.setCheckable(True)
        self.toggle_log_action.setChecked(True)
        self.toggle_log_action.setShortcut("Ctrl+L")
        self.toggle_log_action.triggered.connect(self._toggle_log_panel)
        view_menu.addAction(self.toggle_log_action)

        view_menu.addSeparator()

        expand_preview_action = QAction("🔍 Maximize Preview", self)
        expand_preview_action.setShortcut("Ctrl+M")
        expand_preview_action.triggered.connect(self._maximize_preview)
        view_menu.addAction(expand_preview_action)

        view_menu.addSeparator()

        translation_viewer_action = QAction("🌐 Open &Translation Viewer...", self)
        translation_viewer_action.setShortcut("Ctrl+T")
        translation_viewer_action.triggered.connect(self._on_open_translation_viewer)
        view_menu.addAction(translation_viewer_action)

        # ===== Help menu =====
        help_menu = menubar.addMenu("&Help")

        supported_sites_action = QAction("🌐 &View Supported Sites...", self)
        supported_sites_action.triggered.connect(self._on_supported_sites)
        help_menu.addAction(supported_sites_action)

        help_menu.addSeparator()

        about_action = QAction("ℹ️ &About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        """Connect signals and slots"""
        # URL History panel - fetch URL
        self.url_history_panel.fetch_url_clicked.connect(self._on_fetch_url)
        
        # Keep controls panel connection for compatibility
        self.controls_panel.fetch_url_clicked.connect(self._on_fetch_url)

        # File list panel
        self.file_list_panel.job_selected.connect(self._on_job_selected)
        self.file_list_panel.job_double_clicked.connect(self._on_job_double_clicked)
        
        # Novel library selections
        self.file_list_panel.novel_selected.connect(self._on_novel_selected)
        self.file_list_panel.chapter_selected.connect(self._on_chapter_selected)
        self.file_list_panel.novel_delete_requested.connect(self._on_novel_delete)
        self.file_list_panel.novel_rename_requested.connect(self._on_novel_rename)
        self.file_list_panel.novel_export_requested.connect(self._on_export_novel_by_id)

        # Job manager
        self.job_manager.job_added.connect(self._on_job_added)
        self.job_manager.job_updated.connect(self._on_job_updated)
        self.job_manager.job_removed.connect(self._on_job_removed)
        self.job_manager.progress_changed.connect(self._on_progress_changed)
        self.job_manager.log_emitted.connect(self._on_log)
        
        # Preview panel - glossary integration (hidden but still connected)
        self.preview_panel.add_to_glossary_requested.connect(self.add_quick_glossary_term)

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
        if geometry := self.settings.value("geometry"):
            self.restoreGeometry(geometry)

        # Restore splitter sizes
        if splitter_sizes := self.settings.value("splitter_sizes"):
            with contextlib.suppress(Exception):
                sizes = [int(s) for s in splitter_sizes]
                self.main_splitter.setSizes(sizes)

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

        # Load saved novels from library
        self._refresh_novel_library()

    def _refresh_novel_library(self):
        """Refresh the novel library display in the file list panel"""
        novels = self.novel_library.get_all_novels()
        self.file_list_panel.load_novels(novels)

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

        # No legacy crawler to clean up

        event.accept()

    # === Slot implementations ===

    def _on_import_files(self):
        """Handle import files - adds to Novel Library"""
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

        imported_count = 0
        for file_path in file_paths:
            try:
                import os
                filename = os.path.basename(file_path)
                name_without_ext = os.path.splitext(filename)[0]
                
                if file_path.endswith('.epub'):
                    # Extract EPUB and add to novel library
                    full_text, chapters = self.epub_extractor.extract(file_path)
                    
                    # Check for duplicate
                    if duplicate_job_id := self.import_manager.is_duplicate(full_text):
                        self.logger.warning(
                            f"Duplicate content detected: {file_path}",
                            stage="import",
                            file_path=file_path,
                            duplicate_of=duplicate_job_id
                        )
                        continue
                    
                    # Create chapter data for novel library
                    chapter_list = []
                    for idx, ch in enumerate(chapters):
                        chapter_list.append({
                            'title': ch.get('title', f'Chapter {idx + 1}'),
                            'content': ch.get('content', ''),
                            'chapter_number': idx + 1,
                            'url': ''
                        })
                    
                    # Add to novel library
                    novel = self.novel_library.add_novel(
                        title=name_without_ext,
                        author="Unknown",
                        source_url=f"file://{file_path}",
                        chapters=chapter_list
                    )
                    
                    # Register to prevent duplicates
                    self.import_manager.register_import(novel.novel_id, full_text)
                    
                    # Refresh the novel library display
                    self._refresh_novel_library()
                    
                    self.logger.info(
                        f"Imported EPUB as novel: {novel.title} ({len(chapter_list)} chapters)",
                        stage="import",
                        novel_id=novel.novel_id
                    )
                    imported_count += 1
                    
                else:
                    # Read text file and add as single-chapter novel
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_text = f.read()

                    # Check for duplicate
                    if duplicate_job_id := self.import_manager.is_duplicate(original_text):
                        self.logger.warning(
                            f"Duplicate content detected: {file_path}",
                            stage="import",
                            file_path=file_path,
                            duplicate_of=duplicate_job_id
                        )
                        continue

                    # Add as novel with single chapter
                    novel = self.novel_library.add_novel(
                        title=name_without_ext,
                        author="Unknown",
                        source_url=f"file://{file_path}",
                        chapters=[{
                            'title': name_without_ext,
                            'content': original_text,
                            'chapter_number': 1,
                            'url': ''
                        }]
                    )
                    
                    # Register to prevent duplicates
                    self.import_manager.register_import(novel.novel_id, original_text)
                    
                    # Refresh the novel library display
                    self._refresh_novel_library()
                    
                    self.logger.info(
                        f"Imported text file as novel: {novel.title}",
                        stage="import",
                        novel_id=novel.novel_id
                    )
                    imported_count += 1

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
        
        if imported_count > 0:
            QMessageBox.information(
                self,
                "Import Complete",
                f"Successfully imported {imported_count} file(s) to Novel Library."
            )

    def get_selected_crawler(self):
        """
        Get the currently selected crawler instance.

        Returns:
            CrawlerInterface: LightNovelCrawler
        """
        if not self.lightnovel_crawler:
            raise RuntimeError("lightnovel-crawler is not available")
        return self.lightnovel_crawler

    def _on_supported_sites(self):
        """Show a dialog listing supported sites from lightnovel-crawler."""
        try:
            crawler = self.get_selected_crawler()
        except Exception:
            QMessageBox.critical(
                self,
                "Crawler Missing",
                "lightnovel-crawler is required. Please install it via pip:\n\n    pip install lightnovel-crawler",
            )
            return

        sites = crawler.get_supported_sites() if crawler else []
        if not sites:
            QMessageBox.information(
                self,
                "Supported Sites",
                "No sites available. Ensure lightnovel-crawler is installed.",
            )
            return

        # Build text listing
        text = "\n".join(sites[:300])  # cap to first ~300 entries for dialog

        dlg = QDialog(self)
        dlg.setWindowTitle("Supported Sites (lightnovel-crawler)")
        dlg.resize(600, 500)
        editor = QTextEdit(dlg)
        editor.setReadOnly(True)
        editor.setPlainText(text)

        layout = QVBoxLayout(dlg)
        layout.addWidget(editor)
        dlg.setLayout(layout)
        dlg.exec()

    def _on_fetch_url(self, url: str):
        """Handle fetch URL or novel name"""
        # Get selected crawler
        selected_crawler = self.get_selected_crawler()
        
        # Check if input is a URL or novel name
        if selected_crawler.is_url(url):
            # It's a URL - proceed with direct crawl
            self._crawl_url(url, selected_crawler)
        else:
            # It's a novel name - show search results
            self._search_and_crawl_novel(url, selected_crawler)

    def _search_and_crawl_novel(self, novel_name: str, selected_crawler):
        """Search for novel by name and let user select"""
        import asyncio
        
        self.logger.info(
            f"Searching for novel: {novel_name}",
            stage="crawl_search"
        )
        
        # Create and show search progress dialog (non-modal)
        search_dialog = SearchProgressDialog(f"Searching for: {novel_name}", self)
        search_dialog.show()
        
        # Search results storage
        search_results = {'results': None, 'error': None}
        
        # Search in background thread
        def search_processor(job, progress_cb, log_cb):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Define progress callback
                def progress_wrapper(current, total, message):
                    if total > 0:
                        progress = (current / total) * 100
                        progress_cb(progress)
                    log_cb("info", message)
                
                # Run search
                results = loop.run_until_complete(
                    selected_crawler.search_novel_by_name(novel_name, progress_wrapper)
                )
                
                # Store results in job for retrieval
                job.metadata['search_results'] = results
                job.metadata['search_query'] = novel_name
                
                msg = f"Found {len(results)} results"
                log_cb("info", msg)
                search_results['results'] = results
            except Exception as e:
                err_msg = f"Search failed: {str(e)}"
                log_cb("error", err_msg)
                job.error = str(e)
                search_results['error'] = str(e)
            finally:
                loop.close()
        
        # Create temporary search job
        job_id = self.job_manager.create_job(
            JobType.CRAWL_URL,
            f"Search: {novel_name}"
        )
        
        # Connect job manager's log signal to update search dialog
        def on_search_log(timestamp, log_job_id, level, message):
            if log_job_id == job_id:
                search_dialog.add_log_line(message, level=level)
                # Try to parse progress from message (e.g., "Searching across 376 sites...")
                if "across" in message and "sites" in message:
                    import re
                    if match := re.search(r'(\d+)\s*sites', message):
                        total_sites = int(match.group(1))
                        search_dialog.set_progress(0, total_sites)
        
        self.job_manager.log_emitted.connect(on_search_log)
        
        # Store context for later
        self._pending_search = {
            'results': search_results,
            'crawler': selected_crawler,
            'novel_name': novel_name,
            'job_id': job_id,
            'search_dialog': search_dialog,
            'log_handler': on_search_log
        }
        
        # Connect to job completion to handle results
        def on_job_completed(completed_job_id):
            if completed_job_id != job_id:
                return
            
            # Check if job is completed
            job = self.job_manager.get_job(completed_job_id)
            if not job or job.status != JobStatus.COMPLETED:
                return
            
            # Disconnect after handling
            with contextlib.suppress(Exception):
                self.job_manager.job_updated.disconnect(on_job_completed)
                self.job_manager.log_emitted.disconnect(on_search_log)
            
            # Close search dialog and show results
            search_dialog.close()
            self._on_search_completed()
        
        # Connect signal
        self.job_manager.job_updated.connect(on_job_completed)
        
        # Start search
        self.job_manager.start_job(job_id, search_processor)

    def _on_search_completed(self):
        """Handle search completion"""
        if not hasattr(self, '_pending_search'):
            return
        
        ctx = self._pending_search
        search_results = ctx['results']
        
        # Check for errors
        if search_results['error']:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Search Error",
                f"Search failed:\n{search_results['error']}"
            )
            del self._pending_search
            return
        
        results = search_results['results']
        if not results:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No Results",
                f"No novels found matching '{ctx['novel_name']}'"
            )
            del self._pending_search
            return
        
        # Show search results dialog
        dialog = SearchResultsDialog(results, self)
        if dialog.exec():
            if selected := dialog.get_selected_result():
                # Crawl the selected URL
                self._crawl_url(selected['url'], ctx['crawler'], selected['title'])
        
        del self._pending_search

    def _crawl_url(self, url: str, selected_crawler, novel_title: str = None):
        """Crawl a novel from a direct URL - two phase: discover then download"""
        # Show crawl options dialog
        from sagemtl_desktop.ui.dialogs import CrawlOptionsDialog
        dialog = CrawlOptionsDialog(url, self)
        if dialog.exec():
            options = dialog.get_options()
            if not options.get('novel_name') and novel_title:
                options['novel_name'] = novel_title

            # Add URL to history with title if known
            self.url_history_panel.add_to_history(url, novel_title or "")

            self.logger.info(
                f"Starting chapter discovery from URL: {options['url']}",
                stage="crawl",
                url=options['url'],
                novel_name=options.get('novel_name')
            )

            # Phase 1: Discover chapters first
            # Show a discovery progress dialog
            discovery_dialog = DownloadProgressDialog(
                f"Discovering chapters: {options.get('novel_name', url)}", 
                self
            )
            discovery_dialog.show()
            
            # Use QThread for discovery to keep UI responsive
            from PySide6.QtCore import QThread, Signal as QtSignal
            import asyncio
             
            class DiscoveryWorker(QThread):
                finished = QtSignal(str, str, list)  # title, author, chapters
                error = QtSignal(str)
                progress = QtSignal(str)
                
                def __init__(self, crawler, crawl_service, url):
                    super().__init__()
                    self.crawler = crawler
                    self.crawl_service = crawl_service
                    self.url = url
                
                def run(self):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        def progress_cb(current, total, message):
                            self.progress.emit(message)

                        title, author, chapters = loop.run_until_complete(
                            self.crawl_service.discover_chapters(
                                self.crawler,
                                self.url,
                                progress_callback=progress_cb
                            )
                        )
                        self.finished.emit(title, author or "Unknown", chapters)
                    except Exception as e:
                        self.error.emit(str(e))
                    finally:
                        loop.close()
            
            # Store state for the callback
            discovery_state = {'worker': None, 'chapters': [], 'title': '', 'author': ''}
            
            def on_discovery_progress(message):
                discovery_dialog.add_log_line(message)
            
            def on_discovery_error(error_msg):
                discovery_dialog.add_log_line(f"Error: {error_msg}", level="error")
                discovery_dialog.set_status("Discovery failed")
                QMessageBox.critical(self, "Discovery Failed", f"Failed to discover chapters:\n\n{error_msg}")
                discovery_dialog.close()
            
            def on_discovery_complete(title, author, chapters):
                discovery_dialog.close()
                
                if not chapters:
                    QMessageBox.warning(self, "No Chapters Found", 
                        "No chapters were found at this URL.\n\nThe site may have an unusual structure or may be blocking automated access.")
                    return
                
                # Store for later
                discovery_state['title'] = title
                discovery_state['author'] = author
                discovery_state['chapters'] = chapters
                
                # Phase 2: Show chapter selection dialog
                selection_dialog = ChapterSelectionDialog(title, chapters, self)
                if selection_dialog.exec():
                    selected_chapters = selection_dialog.get_selected_chapters()
                    if selected_chapters:
                        # Proceed with download
                        self._download_selected_chapters(
                            url, title, author, 
                            chapters,
                            selected_chapters,
                            options,
                            selected_crawler
                        )
            
            # Start discovery worker
            worker = DiscoveryWorker(selected_crawler, self.crawl_service, url)
            discovery_state['worker'] = worker
            worker.progress.connect(on_discovery_progress)
            worker.error.connect(on_discovery_error)
            worker.finished.connect(on_discovery_complete)
            worker.start()

    def _download_selected_chapters(
        self,
        url: str,
        title: str,
        author: str,
        discovered_chapters: list,
        selected_chapters: list,
        options: dict,
        selected_crawler
    ):
        """Download the selected chapters after user confirmation"""
        self.logger.info(
            f"Starting download of {len(selected_chapters)} chapters: {title}",
            stage="crawl",
            url=url
        )
        
        # Create crawl job
        job_id = self.job_manager.create_job(
            JobType.CRAWL_URL,
            options.get('novel_name') or title,
            **options
        )

        # Create and show download progress dialog (non-modal)
        download_dialog = DownloadProgressDialog(
            f"Downloading: {title} ({len(selected_chapters)} chapters)", 
            self
        )
        download_dialog.show()
        
        # Track chapter rendering for status updates
        rendering_state = {
            'chapters_rendered': 0,
            'total_chapters': len(selected_chapters),
            'latest_status': "Preparing download..."
        }

        # Start crawl worker with async support
        def crawl_processor(job, progress_cb, log_cb):
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                log_cb("info", f"Downloading {len(selected_chapters)} chapters...")

                def progress_wrapper(current, total, message):
                    rendering_state['latest_status'] = message
                    if total > 0:
                        progress = (current / total) * 100
                        progress_cb(progress)
                    log_cb("info", message)

                novel_data = loop.run_until_complete(
                    self.crawl_service.download_selected_chapters(
                        crawler=selected_crawler,
                        url=url,
                        title=title,
                        author=author,
                        discovered_chapters=discovered_chapters,
                        selected_chapters=selected_chapters,
                        progress_callback=progress_wrapper
                    )
                )

                if not novel_data.chapters:
                    raise RuntimeError("Crawler returned no chapter content")

                rendering_state['chapters_rendered'] = len(novel_data.chapters)
                rendering_state['total_chapters'] = len(novel_data.chapters)

                # Convert chapters to text format
                log_cb("info", f"Processing {len(novel_data.chapters)} chapters...")
                full_text = self.crawl_service.build_full_text(novel_data)

                # Store in job
                job.original_text = full_text
                job.metadata['chapter_count'] = len(novel_data.chapters)
                job.metadata['novel_title'] = novel_data.title
                job.metadata['author'] = novel_data.author

                log_cb("info", f"Crawl completed: {len(novel_data.chapters)} chapters")

                # Save novel to persistent library
                saved_novel = self.novel_library.add_novel_from_crawled(novel_data, url)
                job.metadata['saved_novel_title'] = saved_novel.title
                log_cb("info", f"Novel saved to library: {saved_novel.title}")

                # Log successful crawl
                self.logger.info(
                    f"Crawl completed: {saved_novel.title}",
                    stage="crawl",
                    job_id=job_id,
                    chapter_count=len(novel_data.chapters),
                    content_length=len(full_text)
                )
            except Exception as e:
                err_msg = f"Crawl failed: {str(e)}"
                log_cb("error", err_msg)
                raise
            finally:
                loop.close()

        # Connect job manager's log signal to update download dialog
        def on_download_log(timestamp, log_job_id, level, message):
            if log_job_id == job_id:
                download_dialog.add_log_line(message, level=level)
                # Update status based on rendering progress
                if rendering_state['total_chapters'] > 0:
                    status_msg = rendering_state.get('latest_status') or (
                        f"Downloading: {rendering_state['chapters_rendered']}/"
                        f"{rendering_state['total_chapters']} chapters"
                    )
                    download_dialog.set_status(status_msg)
        
        self.job_manager.log_emitted.connect(on_download_log)

        # Connect to job completion to close download dialog
        def on_download_completed(completed_job_id):
            if completed_job_id != job_id:
                return
            
            # Check if job is completed
            job = self.job_manager.get_job(completed_job_id)
            if not job or job.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
                return
            
            with contextlib.suppress(Exception):
                self.job_manager.job_updated.disconnect(on_download_completed)
                self.job_manager.log_emitted.disconnect(on_download_log)
            
            if job.status == JobStatus.COMPLETED:
                # Update final status
                if rendering_state['total_chapters'] > 0:
                    download_dialog.set_status(
                        f"Completed: {rendering_state['total_chapters']} chapters downloaded"
                    )

                # Refresh novel library in UI
                self._refresh_novel_library()

                # Update URL history with resolved title from saved novel.
                if saved_title := job.metadata.get('saved_novel_title'):
                    self.url_history_panel.update_history_title(url, saved_title)
            else:
                download_dialog.set_status("Download failed")
                QMessageBox.critical(
                    self,
                    "Download Failed",
                    job.error_message or "Crawler job failed."
                )
            
            # Close download dialog
            download_dialog.close()
        
        self.job_manager.job_updated.connect(on_download_completed)
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
                warning_msg = "Glossary loaded with warnings:\n\n" + "\n".join(f"• {w}" for w in result['warnings'])
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

    def _on_load_glossary_menu(self):
        """Handle load glossary from menu"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Glossary File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self._on_load_glossary(file_path)

    def _set_source_lang(self, lang_code: str):
        """Set source language"""
        self.processing_options.source_lang = lang_code
        self.logger.info(f"Source language set to: {lang_code}", stage="settings")

    def _toggle_log_panel(self, checked: bool):
        """Toggle visibility of log panel"""
        if checked:
            self.log_panel.show()
            # Restore previous size
            self.right_splitter.setSizes([600, 150])
        else:
            self.log_panel.hide()
            # Give all space to preview
            self.right_splitter.setSizes([750, 0])

    def _maximize_preview(self):
        """Maximize preview by hiding log and minimizing file list"""
        self.log_panel.hide()
        self.toggle_log_action.setChecked(False)
        self.main_splitter.setSizes([200, 1000])

    def _on_open_translation_viewer(self):
        """Open the Translation Viewer window"""
        # Get current novel info if available
        novel_id = self._current_novel_id
        novel_title = self._get_current_novel_title() if novel_id else "Untitled"
        
        # Get current text from preview if any
        original_text = self.preview_panel.original_text.toPlainText()
        translated_text = self.preview_panel.cleaned_text.toPlainText()
        
        # Create and show the translation viewer
        viewer = TranslationViewerWindow(
            glossary_manager=self.glossary_manager,
            translator=self.translator if hasattr(self, 'translator') else None,
            novel_id=novel_id,
            novel_title=novel_title,
            parent=self
        )
        
        # Pre-populate with current text if any
        if original_text or translated_text:
            viewer.set_text(original_text, translated_text)
        
        viewer.show()

    def _on_apply_glossary_to_current(self):
        """Apply glossary to currently displayed chapter"""
        if not self._current_novel_id:
            QMessageBox.information(self, "No Chapter", "Please select a chapter first.")
            return
        
        # Get combined glossary (global + novel-specific)
        global_terms = self.glossary_manager.get_global_terms()
        novel_terms = self.glossary_manager.get_novel_terms(self._current_novel_id) if self._current_novel_id else []
        combined = novel_terms + global_terms  # Novel terms take precedence
        
        if not combined:
            QMessageBox.information(self, "No Glossary", 
                "No glossary terms found. Add terms via the Glossary menu or right-click on text.")
            return
        
        # Get current chapter from the selected item
        chapter_item = self.file_list_panel.novel_tree.currentItem()
        if not chapter_item or not chapter_item.parent():
            QMessageBox.information(self, "No Chapter", "Please select a chapter first.")
            return
        
        # Get chapter data
        chapter_idx = chapter_item.data(0, Qt.UserRole + 1)
        novel = self.novel_library.get_novel(self._current_novel_id)
        
        if not novel or chapter_idx is None or chapter_idx >= len(novel.chapters):
            return
        
        chapter = novel.chapters[chapter_idx]
        original_content = chapter.content
        
        # Apply glossary
        cleaned_content = self._apply_glossary_replacements(original_content, combined)
        
        # Update the display
        self.preview_panel.set_cleaned_text(f"✨ Cleaned:\n\n{cleaned_content}")
        
        # Count replacements
        replacement_count = sum(term.source in original_content for term in combined)
        
        self.logger.info(
            f"Applied {len(combined)} glossary terms ({replacement_count} replacements) to chapter",
            stage="glossary"
        )
        
        QMessageBox.information(self, "Glossary Applied", 
            f"Applied {len(combined)} glossary terms.\n{replacement_count} replacements made.")

    def _on_apply_glossary_to_all(self):
        """Apply glossary to all chapters of current novel"""
        if not self._current_novel_id:
            QMessageBox.information(self, "No Novel", "Please select a novel first.")
            return
        
        novel = self.novel_library.get_novel(self._current_novel_id)
        if not novel:
            return
        
        # Get combined glossary
        global_terms = self.glossary_manager.get_global_terms()
        novel_terms = self.glossary_manager.get_novel_terms(self._current_novel_id) if self._current_novel_id else []
        combined = novel_terms + global_terms  # Novel terms take precedence
        
        if not combined:
            QMessageBox.information(self, "No Glossary", 
                "No glossary terms found. Add terms via the Glossary menu or right-click on text.")
            return
        
        # Confirm
        reply = QMessageBox.question(
            self, "Apply to All",
            f"Apply {len(combined)} glossary terms to all {len(novel.chapters)} chapters?\n\n"
            "This will update the cleaned text for each chapter.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Apply to all chapters
        total_replacements = 0
        for chapter in novel.chapters:
            original = chapter.content
            cleaned = self._apply_glossary_replacements(original, combined)
            chapter.cleaned_content = cleaned
            total_replacements += sum(term.source in original for term in combined)

        self.novel_library.update_novel(novel)
        
        self.logger.info(
            f"Applied glossary to {len(novel.chapters)} chapters ({total_replacements} replacements)",
            stage="glossary"
        )
        
        QMessageBox.information(self, "Complete", 
            f"Applied glossary to {len(novel.chapters)} chapters.\n"
            f"Total replacements: {total_replacements}")

    def _apply_glossary_replacements(self, text: str, terms: list) -> str:
        """Apply glossary term replacements to text"""
        import re
        result = text
        for term in terms:
            if term.word_boundary:
                # Use word boundary regex
                pattern = r'\b' + re.escape(term.source) + r'\b'
                result = re.sub(pattern, term.target, result, flags=0 if term.case_sensitive else re.IGNORECASE)
            elif term.case_sensitive:
                result = result.replace(term.source, term.target)
            else:
                # Case-insensitive replace
                pattern = re.escape(term.source)
                result = re.sub(pattern, term.target, result, flags=re.IGNORECASE)
        return result

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
        if output_dir := QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        ):
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

    def _on_export_novel(self):
        """Export currently selected novel as EPUB"""
        if not self._current_novel_id:
            QMessageBox.information(self, "No Novel", "Please select a novel first.")
            return
        self._on_export_novel_by_id(self._current_novel_id)

    def _on_export_novel_by_id(self, novel_id: str):
        """Export a specific novel to multiple formats"""
        novel = self.novel_library.get_novel(novel_id)
        if not novel:
            QMessageBox.warning(self, "Error", "Could not find novel.")
            return
        
        if not novel.chapters:
            QMessageBox.information(self, "No Chapters", "This novel has no chapters to export.")
            return
        
        # Ask for output directory
        from PySide6.QtWidgets import QFileDialog
        import os
        
        # Default to Documents/Webnovels
        default_dir = os.path.join(os.path.expanduser("~"), "Documents", "Webnovels")
        
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            default_dir,
            QFileDialog.ShowDirsOnly
        )
        
        if not output_dir:
            return  # Cancelled
        
        try:
            from sagemtl_desktop.core.novel_exporter import NovelExporter
            
            # Create exporter
            exporter = NovelExporter(output_dir)
            
            # Export all formats
            results = exporter.export_novel(
                novel,
                formats=['epub', 'json', 'text', 'web', 'archive', 'meta'],
                use_translated=True
            )
            
            # Build summary
            summary_lines = [f"Successfully exported '{novel.title}':\n"]
            for format_name, path in results.items():
                if path:
                    summary_lines.append(f"  • {format_name}: ✓")
            
            summary_lines.append(f"\nExported to: {output_dir}")
            summary_lines.append(f"Chapters: {len(novel.chapters)}")
            
            QMessageBox.information(
                self,
                "Export Complete",
                "\n".join(summary_lines)
            )
            
            self.logger.info(
                f"Exported novel (multi-format): {novel.title}",
                stage="export",
                chapter_count=len(novel.chapters),
                output_dir=output_dir
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export novel:\n{str(e)}"
            )
            self.logger.error(
                f"Novel export failed: {str(e)}",
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
        if job := self.job_manager.get_job(job_id):
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

    def _on_novel_selected(self, novel_id: str):
        """Handle novel folder selection - show novel info in preview"""
        # Track current novel for glossary operations
        self._current_novel_id = novel_id
        
        if novel := self.novel_library.get_novel(novel_id):
            # Load novel-specific glossary
            self.glossary_manager.set_active_novel(novel_id, novel.title)
            
            # Show novel summary in preview
            info_text = f"📖 {novel.title}\n"
            if novel.author:
                info_text += f"✍️ Author: {novel.author}\n"
            info_text += f"📚 Chapters: {len(novel.chapters)}\n"
            info_text += f"🔗 Source: {novel.source_url}\n\n"
            
            # Show glossary stats
            novel_terms = self.glossary_manager.get_novel_terms(novel_id)
            global_terms = self.glossary_manager.get_global_terms()
            info_text += f"📋 Novel glossary: {len(novel_terms)} terms\n"
            info_text += f"🌐 Global glossary: {len(global_terms)} terms\n\n"
            
            info_text += "Double-click a chapter to view its content.\n"
            info_text += "Press Ctrl+G to open the Glossary Manager."
            
            self.preview_panel.set_original_text(info_text)
            self.preview_panel.set_cleaned_text("")

    def _on_chapter_selected(self, novel_id: str, chapter_id: str):
        """Handle chapter selection - open in Translation Viewer"""
        try:
            if novel := self.novel_library.get_novel(novel_id):
                for chapter in novel.chapters:
                    if chapter.chapter_id == chapter_id:
                        # Track current novel for glossary
                        self._current_novel_id = novel_id
                        
                        # Get chapter content
                        original = chapter.content or ""
                        translated = chapter.translated_content or ""
                        cleaned = chapter.cleaned_content or ""
                        
                        # Open Translation Viewer with chapter content
                        viewer = TranslationViewerWindow(
                            glossary_manager=self.glossary_manager,
                            translator=self.translator if hasattr(self, 'translator') else None,
                            novel_id=novel_id,
                            novel_title=f"{novel.title} - {chapter.title}",
                            parent=self
                        )
                        
                        # Set the text content
                        display_original = f"{chapter.title}\n{'=' * 40}\n\n{original}"
                        display_translated = translated or cleaned or ""
                        viewer.set_text(display_original, display_translated)
                        
                        viewer.show()
                        break
        except Exception as e:
            self.logger.error(f"Error opening chapter viewer: {e}")

    def _on_novel_delete(self, novel_id: str):
        """Handle novel deletion request"""
        if novel := self.novel_library.get_novel(novel_id):
            # Remove from library
            self.novel_library.remove_novel(novel_id)
            
            # Remove from UI
            self.file_list_panel.remove_novel(novel_id)
            
            # Clear preview if it was showing this novel
            self.preview_panel.set_original_text("")
            self.preview_panel.set_cleaned_text("")
            
            # Log the deletion
            self.log_panel.add_log(
                "system", "system", "info",
                f"Deleted novel: {novel.title}"
            )

    def _on_novel_rename(self, novel_id: str, new_name: str):
        """Handle novel rename request"""
        if novel := self.novel_library.get_novel(novel_id):
            old_name = novel.title
            novel.title = new_name
            self.novel_library.update_novel(novel)  # Proper persistence with timestamp
            
            # Update UI
            self.file_list_panel.update_novel_title(novel_id, new_name)
            
            # Refresh the library display to ensure it persists
            self._refresh_novel_library()
            
            # Log the rename
            self.log_panel.add_log(
                "system", "system", "info",
                f"Renamed novel: '{old_name}' → '{new_name}'"
            )

    def _on_job_added(self, job_id: str):
        """Handle job added"""
        if job := self.job_manager.get_job(job_id):
            self.file_list_panel.add_job(job)

    def _on_job_updated(self, job_id: str):
        """Handle job updated"""
        if job := self.job_manager.get_job(job_id):
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
        # Handle special preview_update log level
        if level == "preview_update":
            # Update preview panel with live content
            self.preview_panel.set_original_text(message)
        else:
            # Normal log message
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

    # ==================== Glossary Manager Methods ====================
    
    def _on_open_glossary_manager(self):
        """Open the glossary manager dialog"""
        dialog = GlossaryEditorDialog(
            self.glossary_manager,
            novel_id=self._current_novel_id,
            novel_title=self._get_current_novel_title(),
            parent=self
        )
        dialog.glossary_updated.connect(self._on_glossary_updated)
        dialog.exec()
    
    def _get_current_novel_title(self) -> str:
        """Get the title of the currently selected novel"""
        if self._current_novel_id and (novel := self.novel_library.get_novel(self._current_novel_id)):
            return novel.title
        return "Current Novel"
    
    def _on_glossary_updated(self):
        """Handle glossary updates - reapply to current preview if needed"""
        self.logger.info("Glossary updated", stage="glossary")
        # Could trigger reprocessing here if desired
    
    def _on_import_glossary_csv(self):
        """Import glossary from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Glossary CSV", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Ask where to import
        from PySide6.QtWidgets import QInputDialog
        items = ["Global Glossary"]
        if self._current_novel_id:
            items.append(f"Novel: {self._get_current_novel_title()}")
        
        choice, ok = QInputDialog.getItem(
            self, "Import Destination", 
            "Import terms to:", items, 0, False
        )
        
        if not ok:
            return
        
        target = "global" if choice == "Global Glossary" else "novel"
        novel_id = self._current_novel_id if target == "novel" else None
        
        result = self.glossary_manager.import_from_csv(file_path, target, novel_id)
        
        if result['success']:
            msg = f"Imported {result['terms_added']} terms"
            if result['terms_skipped']:
                msg += f"\nSkipped {result['terms_skipped']} duplicates"
            if result.get('errors'):
                msg += "\n\nWarnings:\n" + "\n".join(result['errors'][:5])
            QMessageBox.information(self, "Import Complete", msg)
            self.logger.info(f"Imported {result['terms_added']} glossary terms from {file_path}", stage="glossary")
        else:
            QMessageBox.critical(self, "Import Failed", result.get('error', 'Unknown error'))
    
    def _on_export_glossary_csv(self):
        """Export glossary to CSV file"""
        from PySide6.QtWidgets import QInputDialog
        
        items = ["Global Glossary", "All (Global + Novel)"]
        if self._current_novel_id:
            items.insert(1, f"Novel: {self._get_current_novel_title()}")
        
        choice, ok = QInputDialog.getItem(
            self, "Export Source",
            "Export terms from:", items, 0, False
        )
        
        if not ok:
            return
        
        if choice == "Global Glossary":
            source = "global"
            default_name = "global_glossary.csv"
        elif choice.startswith("Novel:"):
            source = "novel"
            default_name = f"{self._current_novel_id}_glossary.csv"
        else:
            source = "all"
            default_name = "all_glossary.csv"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Glossary CSV", default_name,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        result = self.glossary_manager.export_to_csv(
            file_path, source, 
            self._current_novel_id if source in ["novel", "all"] else None
        )
        
        if result['success']:
            QMessageBox.information(self, "Export Complete",
                f"Exported {result['terms_exported']} terms to:\n{file_path}")
            self.logger.info(f"Exported {result['terms_exported']} glossary terms to {file_path}", stage="glossary")
        else:
            QMessageBox.critical(self, "Export Failed", result.get('error', 'Unknown error'))
    
    def add_quick_glossary_term(self, selected_text: str):
        """
        Add a glossary term from selected text (called from preview panel context menu).
        
        Args:
            selected_text: Text selected by user
        """
        dialog = QuickTermDialog(
            selected_text,
            glossary_type="novel" if self._current_novel_id else "global",
            parent=self
        )
        
        if dialog.exec():
            term = dialog.get_term()
            
            if dialog.is_global():
                if self.glossary_manager.add_global_term(term):
                    self.logger.info(f"Added global term: {term.source} → {term.target}", stage="glossary")
                    QMessageBox.information(self, "Added", f"Added to global glossary:\n{term.source} → {term.target}")
                else:
                    QMessageBox.warning(self, "Duplicate", "Term already exists in global glossary.")
            elif self._current_novel_id:
                if self.glossary_manager.add_novel_term(self._current_novel_id, term):
                    self.logger.info(f"Added novel term: {term.source} → {term.target}", stage="glossary")
                    QMessageBox.information(self, "Added", f"Added to novel glossary:\n{term.source} → {term.target}")
                else:
                    QMessageBox.warning(self, "Duplicate", "Term already exists in novel glossary.")
            elif self.glossary_manager.add_global_term(term):
                # No novel selected, add to global
                self.logger.info(f"Added global term: {term.source} → {term.target}", stage="glossary")
                QMessageBox.information(self, "Added", f"Added to global glossary:\n{term.source} → {term.target}")
            else:
                QMessageBox.warning(self, "Duplicate", "Term already exists.")
