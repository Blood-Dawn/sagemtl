"""
Main application window.
"""

import contextlib

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QFileDialog, QMessageBox, QDialog, QTextEdit,
    QStackedWidget
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QActionGroup

from .file_list_panel import FileListPanel
from .preview_panel import PreviewPanel
from .controls_panel import ControlsPanel
from .log_panel import LogPanel
from .url_history_panel import URLHistoryPanel
from .dialogs import (
    ErrorDialog, AboutDialog, SearchResultsDialog, SearchNovelGroupsDialog,
    SearchProgressDialog, DownloadProgressDialog, ChapterSelectionDialog,
    CrawlOptionsDialog, BatchCrawlDialog, HelpGuideDialog
)
from .export_dialog import ExportDialog
from .glossary_editor import GlossaryEditorDialog, QuickTermDialog
from .translation_viewer import TranslationViewerWindow
from .error_hints import build_actionable_error_text, get_error_recovery_hints
from .i18n import tr as ui_tr

from ..core import (
    JobManager, Translator, GlossaryProcessor,
    EPUBExtractor, Exporter,
    JobType, JobStatus, ProcessingOptions,
    ImportManager, CrawlService, CrawlSettings, SearchService,
    DesktopAppSettings, DesktopSettingsStore, get_logger
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
        self.desktop_settings_store = DesktopSettingsStore()
        self.desktop_settings = self.desktop_settings_store.load()
        self.ui_language = self.desktop_settings.ui_language

        # Core components
        self.job_manager = JobManager(self)
        self.translator = Translator()
        self.glossary = GlossaryProcessor()
        self.epub_extractor = EPUBExtractor()
        self.exporter = Exporter()
        self.import_manager = ImportManager()
        self.crawl_service = CrawlService()
        self.search_service = SearchService()
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

        # Processing options (shared settings model with CLI/TUI)
        self.processing_options = ProcessingOptions(
            source_lang=self.desktop_settings.source_lang,
            target_lang=self.desktop_settings.target_lang,
            glossary_path=self.desktop_settings.glossary_path,
            translation_backend=self.desktop_settings.translation_backend,
            max_chunk_size=self.desktop_settings.max_chunk_size,
        )
        self.translator.set_active_backend(self.processing_options.translation_backend)

        # UI components
        self._init_ui()
        self._connect_signals()
        self._load_settings()

        # Populate available languages
        self._populate_languages()

    def _tr(self, key: str, **kwargs) -> str:
        """Translate a UI string key for the active interface language."""
        return ui_tr(self.ui_language, key, **kwargs)

    # ===== Manga mode =====

    def _create_manga_menu(self):
        """Add the Manga menu (mode switch + crawl/translate/export actions)."""
        manga_menu = self.menuBar().addMenu(self._tr("menu.manga"))

        switch_action = QAction(self._tr("mode.manga"), self)
        switch_action.triggered.connect(self._switch_to_manga_mode)
        manga_menu.addAction(switch_action)

        novels_action = QAction(self._tr("mode.novels"), self)
        novels_action.triggered.connect(self._switch_to_novel_mode)
        manga_menu.addAction(novels_action)

        manga_menu.addSeparator()
        for key, handler in (
            ("action.manga_add_url", self._manga_add_series),
            ("action.manga_translate", self._manga_translate_chapter),
            ("action.manga_open_reader", self._switch_to_manga_mode),
            ("action.manga_studio", self._manga_open_studio),
            ("action.manga_export", self._manga_export_chapter),
        ):
            action = QAction(self._tr(key), self)
            action.triggered.connect(handler)
            manga_menu.addAction(action)

    def _ensure_manga_view(self):
        """Lazily build the manga workspace (keeps startup and the novel path light)."""
        if self._manga_view is None:
            from ..core.manga.library import MangaLibrary
            from .manga.manga_view import MangaView

            library = MangaLibrary()
            store = self.desktop_settings_store
            self._manga_view = MangaView(
                self.job_manager,
                library,
                lambda: store.load_manga(),
                glossary=self.glossary_manager,
                language=self.ui_language,
            )
            self._mode_stack.addWidget(self._manga_view)
        return self._manga_view

    def _switch_to_manga_mode(self):
        view = self._ensure_manga_view()
        view.refresh_series()
        self._mode_stack.setCurrentWidget(view)

    def _switch_to_novel_mode(self):
        self._mode_stack.setCurrentWidget(self._novel_container)

    def _manga_add_series(self):
        self._switch_to_manga_mode()
        self._manga_view.add_series_by_url()

    def _manga_translate_chapter(self):
        self._switch_to_manga_mode()
        self._manga_view.translate_selected_chapter()

    def _manga_export_chapter(self):
        self._switch_to_manga_mode()
        self._manga_view.export_selected_chapter()

    def _manga_open_studio(self):
        self._switch_to_manga_mode()
        self._manga_view.open_studio()

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

        # Novels/Manga mode switch: wrap the novel content in a stacked widget so
        # the manga workspace can be swapped in without disturbing the novel UI.
        # The manga view is created lazily on first use (keeps startup light).
        self._novel_container = central_widget
        self._mode_stack = QStackedWidget()
        self._mode_stack.addWidget(central_widget)  # index 0 = Novels
        self._manga_view = None
        self.setCentralWidget(self._mode_stack)

        # Manga menu (added after the standard menus are built).
        self._create_manga_menu()

    def _create_menu_bar(self):
        """Create menu bar with all actions organized"""
        menubar = self.menuBar()

        # ===== File menu =====
        file_menu = menubar.addMenu(self._tr("menu.file"))

        import_action = QAction(self._tr("action.import_files"), self)
        import_action.setShortcut("Ctrl+O")
        import_action.triggered.connect(self._on_import_files)
        file_menu.addAction(import_action)

        batch_crawl_action = QAction(self._tr("action.batch_crawl_urls"), self)
        batch_crawl_action.setShortcut("Ctrl+Shift+U")
        batch_crawl_action.triggered.connect(self._on_batch_crawl_urls)
        file_menu.addAction(batch_crawl_action)

        file_menu.addSeparator()

        export_action = QAction(self._tr("action.export_results"), self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        export_novel_action = QAction(self._tr("action.export_novel_epub"), self)
        export_novel_action.setShortcut("Ctrl+Shift+E")
        export_novel_action.triggered.connect(self._on_export_novel)
        file_menu.addAction(export_novel_action)

        file_menu.addSeparator()

        quit_action = QAction(self._tr("action.quit"), self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # ===== Edit menu =====
        edit_menu = menubar.addMenu(self._tr("menu.edit"))

        clear_action = QAction(self._tr("action.clear_jobs"), self)
        clear_action.triggered.connect(self._on_clear_jobs)
        edit_menu.addAction(clear_action)

        # ===== Glossary menu =====
        glossary_menu = menubar.addMenu(self._tr("menu.glossary"))

        glossary_manager_action = QAction(self._tr("action.glossary_manager"), self)
        glossary_manager_action.setShortcut("Ctrl+G")
        glossary_manager_action.triggered.connect(self._on_open_glossary_manager)
        glossary_menu.addAction(glossary_manager_action)

        glossary_menu.addSeparator()

        load_glossary_action = QAction(self._tr("action.load_glossary_csv"), self)
        load_glossary_action.triggered.connect(self._on_load_glossary_menu)
        glossary_menu.addAction(load_glossary_action)

        import_glossary_action = QAction(self._tr("action.import_to_global"), self)
        import_glossary_action.triggered.connect(self._on_import_glossary_csv)
        glossary_menu.addAction(import_glossary_action)

        export_glossary_action = QAction(self._tr("action.export_glossary_csv"), self)
        export_glossary_action.triggered.connect(self._on_export_glossary_csv)
        glossary_menu.addAction(export_glossary_action)

        glossary_menu.addSeparator()

        apply_glossary_action = QAction(self._tr("action.apply_glossary_current"), self)
        apply_glossary_action.setShortcut("Ctrl+Shift+G")
        apply_glossary_action.triggered.connect(self._on_apply_glossary_to_current)
        glossary_menu.addAction(apply_glossary_action)

        apply_all_glossary_action = QAction(self._tr("action.apply_glossary_all"), self)
        apply_all_glossary_action.triggered.connect(self._on_apply_glossary_to_all)
        glossary_menu.addAction(apply_all_glossary_action)

        # ===== Translation menu =====
        translation_menu = menubar.addMenu(self._tr("menu.translation"))

        process_action = QAction(self._tr("action.start_processing"), self)
        process_action.setShortcut("Ctrl+P")
        process_action.triggered.connect(self._on_start_processing)
        translation_menu.addAction(process_action)

        translation_menu.addSeparator()

        # Translation backend submenu
        backend_submenu = translation_menu.addMenu(self._tr("submenu.translation_backend"))
        self.translation_backend_action_group = QActionGroup(self)
        self.translation_backend_action_group.setExclusive(True)
        self.translation_backend_actions = {}
        for backend in self.translator.get_supported_backends():
            action = QAction(backend["label"], self)
            action.setCheckable(True)
            action.setEnabled(bool(backend["available"]))
            action.setToolTip(str(backend.get("hint", "")))
            action.triggered.connect(
                lambda checked=False, backend_name=backend["name"]: self._set_translation_backend(backend_name)
            )
            backend_submenu.addAction(action)
            self.translation_backend_action_group.addAction(action)
            self.translation_backend_actions[backend["name"]] = action

        chunk_submenu = translation_menu.addMenu(self._tr("submenu.chunk_size"))
        self.chunk_size_action_group = QActionGroup(self)
        self.chunk_size_action_group.setExclusive(True)
        self.chunk_size_actions = {}
        for size, label in (
            (500, "Small (500 chars)"),
            (900, "Balanced (900 chars)"),
            (1400, "Large (1400 chars)"),
            (2000, "XL (2000 chars)"),
        ):
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked=False, chunk_size=size: self._set_translation_chunk_size(chunk_size)
            )
            chunk_submenu.addAction(action)
            self.chunk_size_action_group.addAction(action)
            self.chunk_size_actions[size] = action

        # Language settings submenu
        lang_submenu = translation_menu.addMenu(self._tr("submenu.language_settings"))

        self.source_auto_action = QAction(self._tr("action.source_auto"), self)
        self.source_auto_action.setCheckable(True)
        self.source_auto_action.setChecked(True)
        self.source_auto_action.triggered.connect(lambda checked=False: self._set_source_lang("auto"))
        lang_submenu.addAction(self.source_auto_action)
        
        lang_submenu.addSeparator()
        
        source_zh_action = QAction(self._tr("action.source_chinese"), self)
        source_zh_action.triggered.connect(lambda: self._set_source_lang("zh"))
        lang_submenu.addAction(source_zh_action)

        source_ja_action = QAction(self._tr("action.source_japanese"), self)
        source_ja_action.triggered.connect(lambda: self._set_source_lang("ja"))
        lang_submenu.addAction(source_ja_action)

        source_ko_action = QAction(self._tr("action.source_korean"), self)
        source_ko_action.triggered.connect(lambda: self._set_source_lang("ko"))
        lang_submenu.addAction(source_ko_action)

        # ===== View menu =====
        view_menu = menubar.addMenu(self._tr("menu.view"))

        self.toggle_log_action = QAction(self._tr("action.show_log_panel"), self)
        self.toggle_log_action.setCheckable(True)
        self.toggle_log_action.setChecked(True)
        self.toggle_log_action.setShortcut("Ctrl+L")
        self.toggle_log_action.triggered.connect(self._toggle_log_panel)
        view_menu.addAction(self.toggle_log_action)

        view_menu.addSeparator()

        expand_preview_action = QAction(self._tr("action.maximize_preview"), self)
        expand_preview_action.setShortcut("Ctrl+M")
        expand_preview_action.triggered.connect(self._maximize_preview)
        view_menu.addAction(expand_preview_action)

        view_menu.addSeparator()

        translation_viewer_action = QAction(self._tr("action.open_translation_viewer"), self)
        translation_viewer_action.setShortcut("Ctrl+T")
        translation_viewer_action.triggered.connect(self._on_open_translation_viewer)
        view_menu.addAction(translation_viewer_action)

        self.show_active_search_action = QAction(self._tr("action.show_active_search_progress"), self)
        self.show_active_search_action.setEnabled(False)
        self.show_active_search_action.triggered.connect(self._on_show_active_search_progress)
        view_menu.addAction(self.show_active_search_action)

        view_menu.addSeparator()

        ui_lang_menu = view_menu.addMenu(self._tr("submenu.ui_language"))
        self.ui_language_action_group = QActionGroup(self)
        self.ui_language_action_group.setExclusive(True)
        self.ui_language_actions = {}
        for lang_code, label_key in (("en", "action.ui_lang_english"), ("es", "action.ui_lang_spanish")):
            action = QAction(self._tr(label_key), self)
            action.setCheckable(True)
            action.setChecked(lang_code == self.ui_language)
            action.triggered.connect(
                lambda checked=False, language=lang_code: self._set_ui_language(language)
            )
            ui_lang_menu.addAction(action)
            self.ui_language_action_group.addAction(action)
            self.ui_language_actions[lang_code] = action

        # ===== Help menu =====
        help_menu = menubar.addMenu(self._tr("menu.help"))

        help_guide_action = QAction(self._tr("action.open_help_guide"), self)
        help_guide_action.setShortcut("F1")
        help_guide_action.triggered.connect(self._on_help_guide)
        help_menu.addAction(help_guide_action)

        help_menu.addSeparator()

        supported_sites_action = QAction(self._tr("action.view_supported_sites"), self)
        supported_sites_action.triggered.connect(self._on_supported_sites)
        help_menu.addAction(supported_sites_action)

        help_menu.addSeparator()

        about_action = QAction(self._tr("action.about"), self)
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
        if self.translator.is_available("argos"):
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

        # Restore shared desktop/CLI config values.
        self.desktop_settings = self.desktop_settings_store.load()
        self.ui_language = self.desktop_settings.ui_language
        self.processing_options.source_lang = self.desktop_settings.source_lang
        self.processing_options.target_lang = self.desktop_settings.target_lang
        self.processing_options.max_chunk_size = self.desktop_settings.max_chunk_size
        self.processing_options.translation_backend = self.desktop_settings.translation_backend
        self.processing_options.glossary_path = self.desktop_settings.glossary_path

        active_backend = self.processing_options.translation_backend
        if not self.translator.is_available(active_backend):
            active_backend = "argos" if self.translator.is_available("argos") else "echo"
            self.processing_options.translation_backend = active_backend
        self.translator.set_active_backend(active_backend)
        self._sync_translation_backend_actions()
        self._sync_chunk_size_actions()
        self._sync_ui_language_actions()

        if self.processing_options.glossary_path:
            try:
                self.glossary.load_glossary(self.processing_options.glossary_path)
            except Exception as e:
                print(f"Failed to load saved glossary: {e}")
                self.processing_options.glossary_path = None

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
        self.desktop_settings = self.desktop_settings_store.save(
            DesktopAppSettings(
                source_lang=self.processing_options.source_lang,
                target_lang=self.processing_options.target_lang,
                glossary_path=self.processing_options.glossary_path,
                translation_backend=self.processing_options.translation_backend,
                max_chunk_size=self.processing_options.max_chunk_size,
                ui_language=self.ui_language,
            )
        )

    def _show_actionable_error(self, title: str, context: str, error_message: str):
        """Show a critical error dialog with recovery hints."""
        message = build_actionable_error_text(error_message, context=context)
        QMessageBox.critical(self, title, message)

    def _get_crawl_profile(self, url: str) -> CrawlSettings:
        """Load site-specific crawl settings for a URL."""
        return self.crawl_service.get_site_profile(self.settings, url)

    def _save_crawl_profile(self, url: str, crawl_settings: CrawlSettings):
        """Persist site-specific crawl settings for a URL."""
        self.crawl_service.save_site_profile(self.settings, url, crawl_settings)

    def _build_crawl_wrapper(self, crawl_settings: CrawlSettings) -> LightNovelCrawlerWrapper:
        """Create a per-run wrapper configured for current crawl settings."""
        return LightNovelCrawlerWrapper(
            chapter_download_workers=crawl_settings.chapter_download_workers,
            crawl_settings=crawl_settings
        )

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
        # Allow quick batch input via multiline/comma-separated URL paste.
        batch_urls = self.crawl_service.normalize_batch_urls(url)
        if len(batch_urls) > 1:
            self._start_batch_crawl_job(batch_urls, max_chapters=0)
            return

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
        self.logger.info(
            f"Searching for novel: {novel_name}",
            stage="crawl_search"
        )
        
        # Create and show search progress dialog (non-modal)
        search_dialog = SearchProgressDialog(novel_name, self)
        search_dialog.show()
        search_dialog.set_progress(0, 100)
        self._set_active_search_action_state(True)
        
        # Search results storage
        search_results = {'results': None, 'error': None}
        
        # Search in background thread
        def search_processor(job, progress_cb, log_cb):
            try:
                # Define progress callback
                def progress_wrapper(current, total, message):
                    if total > 0:
                        progress = (current / total) * 100
                        progress_cb(progress)
                    log_cb("info", message)
                
                # Run search
                results = self.search_service.run_search_sync(
                    selected_crawler,
                    novel_name=novel_name,
                    progress_callback=progress_wrapper
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
        
        # Create temporary search job
        job_id = self.job_manager.create_job(
            JobType.CRAWL_URL,
            f"Search: {novel_name}"
        )
        
        # Connect job manager's log signal to update search dialog
        def on_search_log(timestamp, log_job_id, level, message):
            if log_job_id == job_id:
                search_dialog.add_log_line(message, level=level)

        def on_search_progress(progress_job_id, progress):
            if progress_job_id != job_id:
                return
            safe_progress = int(max(0.0, min(100.0, float(progress))))
            search_dialog.set_progress(safe_progress, 100)

        self.job_manager.log_emitted.connect(on_search_log)
        self.job_manager.progress_changed.connect(on_search_progress)
        
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
                self.job_manager.progress_changed.disconnect(on_search_progress)
            
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
            self._set_active_search_action_state(False)
            return
        
        ctx = self._pending_search
        search_results = ctx['results']
        
        # Check for errors
        if search_results['error']:
            self._show_actionable_error(
                "Search Error",
                context="search",
                error_message=str(search_results['error']),
            )
            del self._pending_search
            self._set_active_search_action_state(False)
            return
        
        results = search_results['results']
        if not results:
            QMessageBox.warning(
                self,
                "No Results",
                f"No novels found matching '{ctx['novel_name']}'"
            )
            del self._pending_search
            self._set_active_search_action_state(False)
            return

        chapter_count_cache: dict[str, int | None] = {}

        # Fill known chapter counts from existing library cache first.
        for result in results:
            if result.get("chapter_count") is not None:
                continue
            result_url = (result.get("url") or "").strip()
            if not result_url:
                continue
            existing = self.novel_library.get_novel_by_url(result_url)
            if existing:
                cached_count = len(existing.chapters)
                result["chapter_count"] = cached_count
                chapter_count_cache[result_url] = cached_count

        def chapter_count_resolver(result: dict):
            import asyncio

            url = (result.get("url") or "").strip()
            if not url:
                return None

            if url in chapter_count_cache:
                return chapter_count_cache[url]

            existing = self.novel_library.get_novel_by_url(url)
            if existing:
                cached_count = len(existing.chapters)
                chapter_count_cache[url] = cached_count
                return cached_count

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                chapter_count = loop.run_until_complete(
                    self.crawl_service.discover_chapter_count(
                        crawler=ctx["crawler"],
                        url=url
                    )
                )
                chapter_count_cache[url] = chapter_count
                return chapter_count
            finally:
                loop.close()

        grouped_results = self.search_service.group_results(results)
        if not grouped_results:
            QMessageBox.warning(
                self,
                "No Results",
                f"No usable source URLs found for '{ctx['novel_name']}'"
            )
            del self._pending_search
            self._set_active_search_action_state(False)
            return

        auto_prefetch_top_n = 8
        while True:
            self.search_service.refresh_group_summaries(grouped_results)
            group_dialog = SearchNovelGroupsDialog(grouped_results, self)
            if not group_dialog.exec():
                break

            selected_group = group_dialog.get_selected_group()
            if not selected_group:
                continue

            source_rows = selected_group.get("sources") or []
            if not source_rows:
                QMessageBox.warning(
                    self,
                    "No Sources",
                    "No source URLs are available for this grouped novel."
                )
                continue

            source_dialog = SearchResultsDialog(
                source_rows,
                self,
                chapter_count_resolver=chapter_count_resolver,
                novel_title=selected_group.get("title"),
                auto_prefetch_rows=self.search_service.select_prefetch_rows(
                    source_rows,
                    top_n=auto_prefetch_top_n,
                ),
            )
            if source_dialog.exec():
                if selected := source_dialog.get_selected_result():
                    # Crawl the selected source URL.
                    self._crawl_url(selected['url'], ctx['crawler'], selected['title'])
                    break
        
        del self._pending_search
        self._set_active_search_action_state(False)

    def _crawl_url(self, url: str, selected_crawler, novel_title: str = None):
        """Crawl a novel from a direct URL - two phase: discover then download"""
        # Load and edit site-specific crawl settings.
        initial_settings = self._get_crawl_profile(url)
        dialog = CrawlOptionsDialog(url, initial_settings=initial_settings, parent=self)
        if dialog.exec():
            options = dialog.get_options()
            if not options.get('novel_name') and novel_title:
                options['novel_name'] = novel_title
            crawl_settings = CrawlSettings.from_dict(options.get("crawl_settings"))

            # Optional direct EPUB export path from crawled output.
            if crawl_settings.auto_export_epub and not crawl_settings.epub_output_dir:
                default_export_dir = self.crawl_service.default_epub_output_dir()
                selected_output_dir = QFileDialog.getExistingDirectory(
                    self,
                    "Select EPUB Output Directory",
                    default_export_dir
                )
                if not selected_output_dir:
                    return
                crawl_settings.epub_output_dir = selected_output_dir

            self._save_crawl_profile(url, crawl_settings)

            # Use per-run wrapper configured with the selected crawl profile.
            crawl_crawler = self._build_crawl_wrapper(crawl_settings)
            options["crawl_settings"] = crawl_settings.to_dict()

            # Add URL to history with title if known
            self.url_history_panel.add_to_history(url, novel_title or "")

            self.logger.info(
                f"Starting chapter discovery from URL: {options['url']}",
                stage="crawl",
                url=options['url'],
                novel_name=options.get('novel_name'),
                site_key=self.crawl_service.site_key(url)
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
                self._show_actionable_error(
                    "Discovery Failed",
                    context="crawl_discovery",
                    error_message=error_msg,
                )
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
                            url=url,
                            title=title,
                            author=author,
                            discovered_chapters=chapters,
                            selected_chapters=selected_chapters,
                            options=options,
                            selected_crawler=crawl_crawler,
                            crawl_settings=crawl_settings
                        )
            
            # Start discovery worker
            worker = DiscoveryWorker(crawl_crawler, self.crawl_service, url)
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
        selected_crawler,
        crawl_settings: CrawlSettings
    ):
        """Download the selected chapters after user confirmation"""
        existing_novel = (
            self.novel_library.get_novel_by_url(url)
            if crawl_settings.resume_existing
            else None
        )
        pending_chapters = selected_chapters
        skipped_existing_count = 0
        if existing_novel:
            existing_urls = [chapter.url for chapter in existing_novel.chapters]
            pending_chapters, skipped_existing_count = (
                self.crawl_service.filter_pending_chapters_for_resume(
                    selected_chapters,
                    existing_urls
                )
            )

        if not pending_chapters:
            QMessageBox.information(
                self,
                "Nothing to Download",
                "All selected chapters already exist in your library for this source URL."
            )
            return

        self.logger.info(
            f"Starting download of {len(pending_chapters)} chapters: {title}",
            stage="crawl",
            url=url,
            resume_existing=crawl_settings.resume_existing,
            skipped_existing_chapters=skipped_existing_count
        )
        
        # Create crawl job
        job_id = self.job_manager.create_job(
            JobType.CRAWL_URL,
            options.get('novel_name') or title,
            skipped_existing_chapters=skipped_existing_count,
            selected_chapter_count=len(selected_chapters),
            pending_chapter_count=len(pending_chapters),
            **options
        )

        # Create and show download progress dialog (non-modal)
        download_dialog = DownloadProgressDialog(
            f"Downloading: {title} ({len(pending_chapters)} chapters)", 
            self
        )
        download_dialog.show()
        
        # Track chapter rendering for status updates
        rendering_state = {
            'chapters_rendered': 0,
            'total_chapters': len(pending_chapters),
            'latest_status': "Preparing download..."
        }

        # Start crawl worker with async support
        def crawl_processor(job, progress_cb, log_cb):
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                log_cb("info", f"Stage 1/4: Downloading {len(pending_chapters)} chapters...")
                if skipped_existing_count > 0:
                    log_cb(
                        "info",
                        f"Resume enabled: skipped {skipped_existing_count} chapters already in library"
                    )

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
                        selected_chapters=pending_chapters,
                        progress_callback=progress_wrapper,
                        # Enforce per-site crawl policies through the generic-backed path.
                        force_selected_download=True
                    )
                )

                if not novel_data.chapters:
                    raise RuntimeError("Crawler returned no chapter content")

                rendering_state['chapters_rendered'] = len(novel_data.chapters)
                rendering_state['total_chapters'] = len(novel_data.chapters)

                # Convert chapters to text format
                log_cb("info", f"Stage 2/4: Processing {len(novel_data.chapters)} chapters...")
                full_text = self.crawl_service.build_full_text(novel_data)

                # Store in job
                job.original_text = full_text
                job.metadata['chapter_count'] = len(novel_data.chapters)
                job.metadata['novel_title'] = novel_data.title
                job.metadata['author'] = novel_data.author
                job.metadata['skipped_existing_chapters'] = skipped_existing_count

                # Optional direct EPUB export from in-memory crawler output.
                exported_epub_path = ""
                if crawl_settings.auto_export_epub:
                    log_cb("info", "Stage 3/4: Exporting crawled output directly to EPUB...")
                    exported_epub_path = self.crawl_service.export_crawled_epub(
                        novel=novel_data,
                        output_dir=crawl_settings.epub_output_dir,
                        author_fallback=author or "Unknown"
                    )
                    if exported_epub_path:
                        log_cb("info", f"Direct EPUB export completed: {exported_epub_path}")
                job.metadata["exported_epub_path"] = exported_epub_path

                log_cb("info", "Stage 4/4: Saving crawled novel to library...")

                # Save novel to persistent library (merge for resume mode).
                saved_novel = self.novel_library.upsert_novel_from_crawled(
                    novel_data,
                    source_url=url,
                    resume_existing=crawl_settings.resume_existing
                )
                job.metadata['saved_novel_title'] = saved_novel.title
                job.metadata['saved_novel_id'] = saved_novel.novel_id
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
                    skipped = job.metadata.get("skipped_existing_chapters", 0)
                    skipped_msg = f", skipped {skipped} existing" if skipped else ""
                    download_dialog.set_status(
                        f"Completed: {rendering_state['total_chapters']} chapters downloaded{skipped_msg}"
                    )

                # Refresh novel library in UI
                self._refresh_novel_library()

                # Update URL history with resolved title from saved novel.
                if saved_title := job.metadata.get('saved_novel_title'):
                    self.url_history_panel.update_history_title(url, saved_title)

                if exported_epub := job.metadata.get("exported_epub_path"):
                    QMessageBox.information(
                        self,
                        "Direct EPUB Export Complete",
                        f"EPUB exported directly from crawl output:\n{exported_epub}"
                    )
            else:
                download_dialog.set_status("Download failed")
                self._show_actionable_error(
                    "Download Failed",
                    context="crawl_download",
                    error_message=job.error_message or "Crawler job failed.",
                )
            
            # Close download dialog
            download_dialog.close()
        
        self.job_manager.job_updated.connect(on_download_completed)
        self.job_manager.start_job(job_id, crawl_processor)

    def _on_batch_crawl_urls(self):
        """Open batch URL dialog and enqueue crawl queue job."""
        dialog = BatchCrawlDialog(self)
        if not dialog.exec():
            return

        options = dialog.get_options()
        urls = self.crawl_service.normalize_batch_urls(options.get("raw_urls", ""))
        if not urls:
            QMessageBox.warning(
                self,
                "No Valid URLs",
                "No valid HTTP(S) URLs were found in the batch input."
            )
            return

        self._start_batch_crawl_job(urls, options.get("max_chapters", 0))

    def _start_batch_crawl_job(self, urls: list[str], max_chapters: int):
        """Process a list of URLs as a sequential crawl queue job."""
        profile_map = {
            url: self._get_crawl_profile(url).to_dict()
            for url in urls
        }

        self.logger.info(
            f"Starting batch crawl queue ({len(urls)} URLs)",
            stage="crawl_batch",
            url_count=len(urls),
            max_chapters=max_chapters,
        )

        job_id = self.job_manager.create_job(
            JobType.CRAWL_URL,
            f"Batch Crawl ({len(urls)} URLs)",
            batch_url_count=len(urls),
            batch_urls=urls,
            max_chapters=max_chapters,
        )

        batch_dialog = DownloadProgressDialog(
            f"Batch Crawl Queue ({len(urls)} URLs)",
            self
        )
        batch_dialog.show()

        state = {
            "total": len(urls),
            "processed": 0,
            "success": 0,
            "failed": 0,
            "latest_status": "Preparing queue...",
            "results": [],
        }

        def batch_processor(job, progress_cb, log_cb):
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for idx, url in enumerate(urls, 1):
                    state["latest_status"] = f"Queue {idx}/{len(urls)}: {url}"
                    log_cb("info", f"Queue {idx}/{len(urls)}: starting crawl for {url}")
                    settings = CrawlSettings.from_dict(profile_map.get(url, {}))
                    crawler = self._build_crawl_wrapper(settings)

                    def url_progress(current, total, message):
                        total_safe = max(total, 1)
                        local_fraction = current / total_safe
                        overall_fraction = ((idx - 1) + local_fraction) / len(urls)
                        progress_cb(overall_fraction * 100)
                        state["latest_status"] = f"Queue {idx}/{len(urls)}: {message}"
                        log_cb("info", f"[{idx}/{len(urls)}] {message}")

                    try:
                        title, author, discovered_chapters = loop.run_until_complete(
                            self.crawl_service.discover_chapters(
                                crawler,
                                url,
                                progress_callback=url_progress
                            )
                        )
                        if not discovered_chapters:
                            raise RuntimeError("No chapters discovered for URL")

                        selected_chapters = discovered_chapters
                        if max_chapters > 0:
                            selected_chapters = discovered_chapters[:max_chapters]

                        novel_data = loop.run_until_complete(
                            self.crawl_service.download_selected_chapters(
                                crawler=crawler,
                                url=url,
                                title=title,
                                author=author,
                                discovered_chapters=discovered_chapters,
                                selected_chapters=selected_chapters,
                                progress_callback=url_progress,
                                force_selected_download=True,
                            )
                        )
                        if not novel_data.title:
                            novel_data.title = title

                        saved_novel = self.novel_library.upsert_novel_from_crawled(
                            novel_data,
                            source_url=url,
                            resume_existing=settings.resume_existing
                        )
                        state["success"] += 1
                        state["results"].append(
                            {
                                "url": url,
                                "title": saved_novel.title,
                                "status": "success",
                            }
                        )

                        if settings.auto_export_epub and settings.epub_output_dir:
                            try:
                                epub_path = self.crawl_service.export_crawled_epub(
                                    novel=novel_data,
                                    output_dir=settings.epub_output_dir,
                                    author_fallback=saved_novel.author
                                )
                                state["results"][-1]["epub_path"] = epub_path
                                log_cb("info", f"[{idx}/{len(urls)}] Direct EPUB: {epub_path}")
                            except Exception as export_exc:
                                state["results"][-1]["epub_error"] = str(export_exc)
                                log_cb("warning", f"[{idx}/{len(urls)}] EPUB export failed: {export_exc}")

                        log_cb(
                            "info",
                            f"Queue {idx}/{len(urls)} completed: {saved_novel.title} ({len(novel_data.chapters)} chapters)"
                        )
                    except Exception as crawl_exc:
                        state["failed"] += 1
                        state["results"].append(
                            {
                                "url": url,
                                "title": "",
                                "status": "failed",
                                "error": str(crawl_exc),
                            }
                        )
                        log_cb("error", f"Queue {idx}/{len(urls)} failed: {crawl_exc}")
                    finally:
                        state["processed"] = idx

                job.metadata["batch_results"] = state["results"]
                job.metadata["batch_success"] = state["success"]
                job.metadata["batch_failed"] = state["failed"]
                job.metadata["batch_processed"] = state["processed"]
            finally:
                loop.close()

        def on_batch_log(timestamp, log_job_id, level, message):
            if log_job_id != job_id:
                return
            batch_dialog.add_log_line(message, level=level)
            batch_dialog.set_status(state["latest_status"])

        def on_batch_complete(completed_job_id):
            if completed_job_id != job_id:
                return

            job = self.job_manager.get_job(completed_job_id)
            if not job or job.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
                return

            with contextlib.suppress(Exception):
                self.job_manager.job_updated.disconnect(on_batch_complete)
                self.job_manager.log_emitted.disconnect(on_batch_log)

            self._refresh_novel_library()
            for result in state["results"]:
                if result.get("status") == "success" and result.get("title"):
                    self.url_history_panel.add_to_history(result["url"], result["title"])

            summary = (
                f"Batch crawl finished.\n\n"
                f"Processed: {state['processed']}/{state['total']}\n"
                f"Success: {state['success']}\n"
                f"Failed: {state['failed']}"
            )
            if job.status == JobStatus.FAILED:
                summary += f"\n\nJob error: {job.error_message or 'Unknown error'}"

            QMessageBox.information(self, "Batch Crawl Complete", summary)
            batch_dialog.close()

        self.job_manager.log_emitted.connect(on_batch_log)
        self.job_manager.job_updated.connect(on_batch_complete)
        self.job_manager.start_job(job_id, batch_processor)

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
            self._show_actionable_error(
                "Glossary Error",
                context="glossary",
                error_message=f"Failed to load glossary:\n{str(e)}",
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
        if hasattr(self, "source_auto_action"):
            self.source_auto_action.setChecked(lang_code == "auto")
        self._save_settings()
        self.logger.info(f"Source language set to: {lang_code}", stage="settings")

    def _set_translation_backend(self, backend: str):
        """Set translation backend for future processing jobs."""
        backend_meta = {
            entry["name"]: entry
            for entry in self.translator.get_supported_backends()
        }
        if not self.translator.is_available(backend):
            hint = backend_meta.get(backend, {}).get("hint", "Missing optional dependency.")
            QMessageBox.warning(
                self,
                "Backend Unavailable",
                f"The '{backend}' backend is not available.\n\n{hint}"
            )
            self._sync_translation_backend_actions()
            return

        self.processing_options.translation_backend = backend
        self.translator.set_active_backend(backend)
        self._sync_translation_backend_actions()
        self._save_settings()
        self.logger.info(
            f"Translation backend set to: {backend}",
            stage="settings",
            backend=backend
        )

    def _set_translation_chunk_size(self, max_chunk_size: int):
        """Set translation chunk size used by chunked translation."""
        normalized_size = max(100, min(5000, int(max_chunk_size)))
        self.processing_options.max_chunk_size = normalized_size
        self._sync_chunk_size_actions()
        self._save_settings()
        self.logger.info(
            f"Translation chunk size set to: {normalized_size}",
            stage="settings",
            max_chunk_size=normalized_size
        )

    def _sync_translation_backend_actions(self):
        """Sync check state and availability for backend menu actions."""
        selected_backend = self.processing_options.translation_backend
        for backend in self.translator.get_supported_backends():
            action = self.translation_backend_actions.get(backend["name"])
            if not action:
                continue
            action.setEnabled(bool(backend["available"]))
            action.setChecked(backend["name"] == selected_backend)

    def _sync_chunk_size_actions(self):
        """Sync check state for chunk-size menu actions."""
        current_size = self.processing_options.max_chunk_size
        if current_size in self.chunk_size_actions:
            self.chunk_size_actions[current_size].setChecked(True)
            return

        nearest_size = min(self.chunk_size_actions.keys(), key=lambda size: abs(size - current_size))
        self.chunk_size_actions[nearest_size].setChecked(True)

    def _set_ui_language(self, language: str):
        """Set UI language and rebuild menu labels."""
        normalized = language if language in {"en", "es"} else "en"
        if normalized == self.ui_language:
            self._sync_ui_language_actions()
            return

        self.ui_language = normalized
        self.desktop_settings.ui_language = normalized
        self._save_settings()
        self.menuBar().clear()
        self._create_menu_bar()
        self._sync_translation_backend_actions()
        self._sync_chunk_size_actions()
        self._sync_ui_language_actions()
        self._set_active_search_action_state(hasattr(self, "_pending_search"))

        language_name_key = "action.ui_lang_english" if normalized == "en" else "action.ui_lang_spanish"
        QMessageBox.information(
            self,
            self._tr("msg.ui_language_changed.title"),
            self._tr(
                "msg.ui_language_changed.body",
                language_name=self._tr(language_name_key),
            ),
        )

    def _sync_ui_language_actions(self):
        """Sync check state for UI language menu actions."""
        if not hasattr(self, "ui_language_actions"):
            return
        for language, action in self.ui_language_actions.items():
            action.setChecked(language == self.ui_language)

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

    def _on_show_active_search_progress(self):
        """Reopen the active search progress dialog if a search job is still running."""
        if not hasattr(self, "_pending_search"):
            QMessageBox.information(self, "Search", "No active search is currently running.")
            return

        ctx = self._pending_search
        search_dialog = ctx.get("search_dialog")
        if not search_dialog:
            QMessageBox.information(self, "Search", "Search progress dialog is unavailable.")
            return

        search_dialog.showNormal()
        search_dialog.raise_()
        search_dialog.activateWindow()

    def _set_active_search_action_state(self, enabled: bool):
        if hasattr(self, "show_active_search_action"):
            self.show_active_search_action.setEnabled(bool(enabled))

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
        
        # Apply glossary using the unified manager pipeline.
        cleaned_content = self.glossary_manager.apply_glossary(
            original_content,
            self._current_novel_id
        )
        
        # Update the display
        self.preview_panel.set_cleaned_text(f"✨ Cleaned:\n\n{cleaned_content}")
        
        changed = cleaned_content != original_content
        
        self.logger.info(
            f"Applied {len(combined)} glossary terms (changed={changed}) to chapter",
            stage="glossary"
        )
        
        QMessageBox.information(self, "Glossary Applied", 
            f"Applied {len(combined)} glossary terms.\n"
            f"Chapter changed: {'Yes' if changed else 'No'}")

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
        changed_chapters = 0
        for chapter in novel.chapters:
            original = chapter.content
            cleaned = self.glossary_manager.apply_glossary(original, self._current_novel_id)
            chapter.cleaned_content = cleaned
            changed_chapters += int(cleaned != original)

        self.novel_library.update_novel(novel)
        
        self.logger.info(
            f"Applied glossary to {len(novel.chapters)} chapters ({changed_chapters} chapters changed)",
            stage="glossary"
        )
        
        QMessageBox.information(self, "Complete", 
            f"Applied glossary to {len(novel.chapters)} chapters.\n"
            f"Chapters changed: {changed_chapters}")

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
            glossary_loaded=self.glossary.is_loaded(),
            translation_backend=self.processing_options.translation_backend,
            max_chunk_size=self.processing_options.max_chunk_size,
        )

        # Disable processing button
        self.controls_panel.set_processing_enabled(False)

        # Process each job
        for job in jobs:
            self._process_job(job.job_id)

    def _process_job(self, job_id: str):
        """Process a single job"""
        job = self.job_manager.get_job(job_id)
        job_novel_id = self._resolve_job_novel_id(job)

        global_term_count = len(self.glossary_manager.get_global_terms())
        novel_term_count = len(self.glossary_manager.get_novel_terms(job_novel_id)) if job_novel_id else 0
        manager_term_count = global_term_count + novel_term_count

        self.logger.info(
            f"Starting translation job: {job.name}",
            stage="processing",
            job_id=job_id,
            content_length=len(job.original_text),
            translation_backend=self.processing_options.translation_backend,
            max_chunk_size=self.processing_options.max_chunk_size,
            glossary_global_terms=global_term_count,
            glossary_novel_terms=novel_term_count,
        )

        def translate_processor(job, progress_cb, log_cb):
            # Step 1: Apply glossary before
            text = job.original_text
            if self.glossary.is_loaded():
                log_cb("info", "Applying legacy CSV glossary (before translation)...")
                text = self.glossary.apply_before(text)
            if manager_term_count:
                log_cb("info", f"Applying glossary manager terms (before translation): {manager_term_count}")
                text = self.glossary_manager.apply_glossary(text, job_novel_id)

            # Step 2: Translate
            backend = self.processing_options.translation_backend
            if self.translator.is_available(backend):
                log_cb(
                    "info",
                    f"Translating with backend '{backend}' (chunk size={self.processing_options.max_chunk_size})..."
                )
                translated = self.translator.translate(
                    text,
                    self.processing_options.source_lang,
                    self.processing_options.target_lang,
                    progress_callback=progress_cb,
                    log_callback=log_cb,
                    backend=backend,
                    max_chunk_size=self.processing_options.max_chunk_size,
                )
            else:
                log_cb("warn", f"Backend '{backend}' unavailable, skipping translation")
                translated = text

            # Step 3: Apply glossary after
            cleaned = translated
            if self.glossary.is_loaded():
                log_cb("info", "Applying legacy CSV glossary (after translation)...")
                cleaned = self.glossary.apply_after(cleaned)
            if manager_term_count:
                log_cb("info", f"Applying glossary manager terms (after translation): {manager_term_count}")
                cleaned = self.glossary_manager.apply_glossary(cleaned, job_novel_id)

            # Store result
            job.cleaned_text = cleaned
            job.metadata['source_lang'] = self.processing_options.source_lang
            job.metadata['target_lang'] = self.processing_options.target_lang
            job.metadata['translation_backend'] = self.processing_options.translation_backend
            job.metadata['max_chunk_size'] = self.processing_options.max_chunk_size

            # Log completion
            self.logger.info(
                f"Translation job completed: {job.name}",
                stage="processing",
                job_id=job_id,
                result_length=len(cleaned)
            )

        self.job_manager.start_job(job_id, translate_processor)

    def _resolve_job_novel_id(self, job) -> str | None:
        """Resolve novel id from job metadata for novel-specific glossary terms."""
        if not job or not job.metadata:
            return None
        candidate = job.metadata.get("saved_novel_id") or job.metadata.get("novel_id")
        if not candidate:
            return None
        if self.novel_library.get_novel(candidate):
            return candidate
        return None

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
                self._show_actionable_error(
                    "Export Error",
                    context="export",
                    error_message=f"Failed to export files:\n{str(e)}",
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
            self._show_actionable_error(
                "Export Error",
                context="export",
                error_message=f"Failed to export novel:\n{str(e)}",
            )
            self.logger.error(
                f"Novel export failed: {str(e)}",
                stage="export",
                exc_info=e
            )

    def _on_source_lang_changed(self, lang_code: str):
        """Handle source language change"""
        self.processing_options.source_lang = lang_code
        if hasattr(self, "source_auto_action"):
            self.source_auto_action.setChecked(lang_code == "auto")
        self._save_settings()

    def _on_target_lang_changed(self, lang_code: str):
        """Handle target language change"""
        self.processing_options.target_lang = lang_code
        self._save_settings()

    def _on_job_selected(self, job_id: str):
        """Handle job selection"""
        if job := self.job_manager.get_job(job_id):
            self.preview_panel.set_text_pair(job.original_text, job.cleaned_text)

    def _on_job_double_clicked(self, job_id: str):
        """Handle job double click (show error if failed)"""
        job = self.job_manager.get_job(job_id)
        if job and job.status == JobStatus.FAILED:
            context = str(job.job_type.value) if job.job_type else "processing"
            hints = get_error_recovery_hints(job.error_message or "", context=context)
            dialog = ErrorDialog(
                job.name,
                job.error_message or "Unknown error",
                job.error_traceback or "",
                recovery_hints=hints,
                parent=self,
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
            novel.title_locked = True
            self.novel_library.update_novel(novel)  # Proper persistence with timestamp
            self.glossary_manager.set_novel_title(novel_id, new_name)
            
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

    def _on_help_guide(self):
        """Open detailed workflow/options help dialog."""
        dialog = HelpGuideDialog(self)
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
