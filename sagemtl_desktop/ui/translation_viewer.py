"""
Translation Viewer Window - Dedicated window for viewing and translating text.

Features:
- Side-by-side view of original and translated text
- Live glossary term highlighting
- Translation with glossary application
- English MTL refinement (grammar/style fix)
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QPushButton, QLabel, QComboBox, QProgressBar,
    QFrame, QScrollArea, QMessageBox, QToolBar, QStatusBar
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QAction, QTextCursor
import re
from typing import List, Optional, Tuple

from sagemtl_desktop.core.glossary_manager import GlossaryManager, GlossaryTerm


class TranslationWorker(QObject):
    """Worker for background translation"""
    finished = Signal(str)
    error = Signal(str)
    progress = Signal(int, str)
    
    def __init__(self, text: str, translator, glossary_manager: GlossaryManager, 
                 novel_id: str = None, refine_english: bool = False):
        super().__init__()
        self.text = text
        self.translator = translator
        self.glossary_manager = glossary_manager
        self.novel_id = novel_id
        self.refine_english = refine_english
    
    def run(self):
        """Execute translation"""
        try:
            self.progress.emit(10, "Applying glossary to source text...")
            
            # Apply glossary before translation
            processed_text = self.glossary_manager.apply_glossary(
                self.text, self.novel_id
            )
            
            self.progress.emit(30, "Translating text...")
            
            # Translate
            if self.translator and hasattr(self.translator, 'translate'):
                translated = self.translator.translate(processed_text)
            else:
                # If no translator, just return glossary-applied text
                translated = processed_text
            
            self.progress.emit(70, "Applying glossary to translation...")
            
            # Apply glossary after translation
            final_text = self.glossary_manager.apply_glossary(
                translated, self.novel_id
            )
            
            # Refine English if requested
            if self.refine_english:
                self.progress.emit(85, "Refining English text...")
                final_text = self._refine_english(final_text)
            
            self.progress.emit(100, "Done!")
            self.finished.emit(final_text)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _refine_english(self, text: str) -> str:
        """
        Apply English refinement rules to improve MTL quality.
        This is a rule-based approach that fixes common MTL issues.
        """
        # Common MTL fixes
        refinements = [
            # Fix double spaces
            (r'\s{2,}', ' '),
            # Fix punctuation spacing
            (r'\s+([,\.!\?;:])', r'\1'),
            (r'([,\.!\?;:])([A-Za-z])', r'\1 \2'),
            # Fix quote spacing
            (r'"\s+', '"'),
            (r'\s+"', '"'),
            # Capitalize after periods
            (r'(\.\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper()),
            # Fix common MTL patterns
            (r'\bhe\s+he\b', 'he', re.IGNORECASE),
            (r'\bshe\s+she\b', 'she', re.IGNORECASE),
            (r'\bthe\s+the\b', 'the', re.IGNORECASE),
            (r'\ba\s+a\b', 'a', re.IGNORECASE),
            # Fix "this this" type duplications
            (r'\b(\w+)\s+\1\b', r'\1'),
            # Fix awkward "of the of" patterns
            (r'\bof\s+the\s+of\b', 'of the', re.IGNORECASE),
            # Normalize quotes
            (r'["""]', '"'),
            (r"[''']", "'"),
            # Fix sentence fragments with no subject
            # ... more rules can be added
        ]
        
        result = text
        for pattern, replacement, *flags in refinements:
            flag = flags[0] if flags else 0
            if callable(replacement):
                result = re.sub(pattern, replacement, result, flags=flag)
            else:
                result = re.sub(pattern, replacement, result, flags=flag)
        
        return result


class GlossaryHighlighter:
    """Handles highlighting of glossary terms in text"""
    
    def __init__(self, text_edit: QTextEdit, terms: List[GlossaryTerm]):
        self.text_edit = text_edit
        self.terms = terms
    
    def highlight_terms(self):
        """Highlight all glossary terms in the text"""
        try:
            if not self.terms:
                return
                
            cursor = self.text_edit.textCursor()
            
            # Format for highlights
            highlight_format = QTextCharFormat()
            highlight_format.setBackground(QColor("#fef08a"))  # Yellow highlight
            highlight_format.setForeground(QColor("#854d0e"))  # Dark yellow text
            highlight_format.setFontWeight(QFont.Weight.Bold)
            
            text = self.text_edit.toPlainText()
            if not text:
                return
            
            # Reset formatting first - use begin/endEditBlock for performance
            cursor.beginEditBlock()
            try:
                cursor.select(QTextCursor.SelectionType.Document)
                default_format = QTextCharFormat()
                cursor.setCharFormat(default_format)
                
                # Highlight each term
                for term in self.terms:
                    pattern = re.escape(term.source)
                    if not term.case_sensitive:
                        flags = re.IGNORECASE
                    else:
                        flags = 0
                    
                    if term.word_boundary:
                        pattern = r'\b' + pattern + r'\b'
                    
                    for match in re.finditer(pattern, text, flags):
                        cursor.setPosition(match.start())
                        cursor.setPosition(match.end(), QTextCursor.MoveMode.KeepAnchor)
                        cursor.setCharFormat(highlight_format)
            finally:
                cursor.endEditBlock()
        except Exception as e:
            # Silently ignore highlighting errors to prevent crashes
            pass


class TranslationViewerWindow(QMainWindow):
    """
    Dedicated window for viewing and translating text with glossary support.
    """
    
    def __init__(self, glossary_manager: GlossaryManager, 
                 translator=None, novel_id: str = None, 
                 novel_title: str = None, parent=None):
        super().__init__(parent)
        self.glossary_manager = glossary_manager
        self.translator = translator
        self.novel_id = novel_id
        self.novel_title = novel_title or "Untitled"
        
        self._worker = None
        self._thread = None
        
        self.setWindowTitle(f"Translation Viewer - {self.novel_title}")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        self._init_ui()
        self._load_glossary_terms()
    
    def _init_ui(self):
        """Initialize the UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Toolbar
        self._create_toolbar()
        
        # Main splitter for source/translated
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Original text
        left_panel = self._create_text_panel("Original Text", "original")
        splitter.addWidget(left_panel)
        
        # Right panel - Translated text
        right_panel = self._create_text_panel("Translated Text", "translated")
        splitter.addWidget(right_panel)
        
        splitter.setSizes([600, 600])
        layout.addWidget(splitter)
        
        # Bottom panel - Glossary terms preview
        glossary_panel = self._create_glossary_panel()
        layout.addWidget(glossary_panel)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _create_toolbar(self):
        """Create the toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Translate button
        translate_action = QAction("🌐 Translate", self)
        translate_action.setToolTip("Translate the original text with glossary applied")
        translate_action.triggered.connect(self._on_translate)
        toolbar.addAction(translate_action)
        
        toolbar.addSeparator()
        
        # Apply glossary only
        glossary_action = QAction("📋 Apply Glossary Only", self)
        glossary_action.setToolTip("Apply glossary replacements without translation")
        glossary_action.triggered.connect(self._on_apply_glossary_only)
        toolbar.addAction(glossary_action)
        
        toolbar.addSeparator()
        
        # Refine English button
        refine_action = QAction("✨ Refine English", self)
        refine_action.setToolTip("Fix grammar and improve MTL English quality")
        refine_action.triggered.connect(self._on_refine_english)
        toolbar.addAction(refine_action)
        
        toolbar.addSeparator()
        
        # Highlight terms toggle
        self.highlight_action = QAction("🔍 Highlight Terms", self)
        self.highlight_action.setCheckable(True)
        self.highlight_action.setChecked(True)  # Enabled by default
        self.highlight_action.setToolTip("Highlight glossary terms in the text")
        self.highlight_action.triggered.connect(self._on_toggle_highlight)
        toolbar.addAction(self.highlight_action)
        
        toolbar.addSeparator()
        
        # Clear button
        clear_action = QAction("🗑️ Clear", self)
        clear_action.triggered.connect(self._on_clear)
        toolbar.addAction(clear_action)
    
    def _create_text_panel(self, title: str, panel_type: str) -> QWidget:
        """Create a text panel with title and text edit"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel(f"<b>{title}</b>")
        header.setStyleSheet("font-size: 14px; padding: 4px;")
        layout.addWidget(header)
        
        # Text edit
        text_edit = QTextEdit()
        text_edit.setAcceptRichText(False)
        text_edit.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                line-height: 1.6;
                padding: 8px;
            }
        """)
        
        if panel_type == "original":
            self.original_text = text_edit
            text_edit.setPlaceholderText("Paste or type original text here...")
            text_edit.textChanged.connect(self._on_original_text_changed)
        else:
            self.translated_text = text_edit
            text_edit.setPlaceholderText("Translated text will appear here...")
        
        layout.addWidget(text_edit)
        
        # Word count label
        word_count = QLabel("0 characters | 0 words")
        word_count.setStyleSheet("color: gray; font-size: 11px; padding: 2px;")
        
        if panel_type == "original":
            self.original_word_count = word_count
        else:
            self.translated_word_count = word_count
        
        layout.addWidget(word_count)
        
        return panel
    
    def _create_glossary_panel(self) -> QWidget:
        """Create the glossary terms preview panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMaximumHeight(150)
        layout = QVBoxLayout(panel)
        
        # Header with term count
        header_layout = QHBoxLayout()
        header = QLabel("<b>📋 Active Glossary Terms</b>")
        header_layout.addWidget(header)
        
        self.term_count_label = QLabel("0 global + 0 novel terms")
        self.term_count_label.setStyleSheet("color: gray;")
        header_layout.addWidget(self.term_count_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Scrollable term list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.terms_container = QWidget()
        self.terms_layout = QHBoxLayout(self.terms_container)
        self.terms_layout.setAlignment(Qt.AlignLeft)
        scroll.setWidget(self.terms_container)
        
        layout.addWidget(scroll)
        
        return panel
    
    def _load_glossary_terms(self):
        """Load and display glossary terms"""
        # Clear existing terms
        while self.terms_layout.count():
            child = self.terms_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        global_terms = self.glossary_manager.get_global_terms()
        novel_terms = []
        if self.novel_id:
            novel_terms = self.glossary_manager.get_novel_terms(self.novel_id)
        
        self.all_terms = novel_terms + global_terms  # Novel terms first (priority)
        
        # Update count label
        self.term_count_label.setText(
            f"{len(global_terms)} global + {len(novel_terms)} novel terms"
        )
        
        # Display terms as pills
        for term in self.all_terms[:50]:  # Limit display
            pill = QLabel(f"{term.source} → {term.target}")
            pill.setStyleSheet("""
                QLabel {
                    background-color: #e0e7ff;
                    color: #3730a3;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                }
            """)
            pill.setToolTip(f"Category: {term.category}\nNotes: {term.notes}")
            self.terms_layout.addWidget(pill)
        
        if len(self.all_terms) > 50:
            more_label = QLabel(f"... and {len(self.all_terms) - 50} more")
            more_label.setStyleSheet("color: gray; font-style: italic;")
            self.terms_layout.addWidget(more_label)
        
        self.terms_layout.addStretch()
    
    def set_text(self, original: str, translated: str = ""):
        """Set the text content"""
        self.original_text.setPlainText(original)
        self.translated_text.setPlainText(translated)
        self._update_word_counts()
        
        # Highlighting disabled temporarily due to PySide6 compatibility issues
        # if self.highlight_action.isChecked():
        #     self._highlight_all_terms()
    
    def _on_original_text_changed(self):
        """Handle original text changes"""
        self._update_word_counts()
        # Highlighting disabled temporarily due to PySide6 compatibility issues
        # if self.highlight_action.isChecked():
        #     self._highlight_original_terms()
    
    def _update_word_counts(self):
        """Update word count labels"""
        orig_text = self.original_text.toPlainText()
        trans_text = self.translated_text.toPlainText()
        
        orig_words = len(orig_text.split()) if orig_text else 0
        trans_words = len(trans_text.split()) if trans_text else 0
        
        self.original_word_count.setText(
            f"{len(orig_text)} characters | {orig_words} words"
        )
        self.translated_word_count.setText(
            f"{len(trans_text)} characters | {trans_words} words"
        )
    
    def _highlight_original_terms(self):
        """Highlight glossary terms in original text"""
        highlighter = GlossaryHighlighter(self.original_text, self.all_terms)
        highlighter.highlight_terms()
    
    def _highlight_translated_terms(self):
        """Highlight glossary terms in translated text"""
        highlighter = GlossaryHighlighter(self.translated_text, self.all_terms)
        highlighter.highlight_terms()
    
    def _highlight_all_terms(self):
        """Highlight terms in both panels"""
        self._highlight_original_terms()
        self._highlight_translated_terms()
    
    def _on_toggle_highlight(self, checked: bool):
        """Toggle term highlighting"""
        if checked:
            self._highlight_all_terms()
        else:
            # Clear highlighting by resetting format
            for text_edit in [self.original_text, self.translated_text]:
                cursor = text_edit.textCursor()
                cursor.select(QTextCursor.SelectionType.Document)
                cursor.setCharFormat(QTextCharFormat())
    
    def _on_translate(self):
        """Start translation"""
        text = self.original_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "No Text", "Please enter text to translate.")
            return
        
        self._start_processing(text, translate=True, refine=False)
    
    def _on_apply_glossary_only(self):
        """Apply glossary without translation"""
        text = self.original_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "No Text", "Please enter text to apply glossary.")
            return
        
        # Direct glossary application
        result = self.glossary_manager.apply_glossary(text, self.novel_id)
        self.translated_text.setPlainText(result)
        self._update_word_counts()
        
        if self.highlight_action.isChecked():
            self._highlight_translated_terms()
        
        self.status_bar.showMessage("Glossary applied successfully")
    
    def _on_refine_english(self):
        """Refine the translated English text"""
        text = self.translated_text.toPlainText().strip()
        if not text:
            # Try original text if translated is empty
            text = self.original_text.toPlainText().strip()
        
        if not text:
            QMessageBox.warning(self, "No Text", "Please enter text to refine.")
            return
        
        # Apply refinement directly
        worker = TranslationWorker(text, None, self.glossary_manager, 
                                   self.novel_id, refine_english=True)
        refined = worker._refine_english(text)
        
        self.translated_text.setPlainText(refined)
        self._update_word_counts()
        
        if self.highlight_action.isChecked():
            self._highlight_translated_terms()
        
        self.status_bar.showMessage("English text refined successfully")
    
    def _start_processing(self, text: str, translate: bool = False, refine: bool = False):
        """Start background processing"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self._thread = QThread()
        self._worker = TranslationWorker(
            text, 
            self.translator if translate else None,
            self.glossary_manager,
            self.novel_id,
            refine_english=refine
        )
        self._worker.moveToThread(self._thread)
        
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_processing_finished)
        self._worker.error.connect(self._on_processing_error)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        
        self._thread.start()
    
    def _on_processing_finished(self, result: str):
        """Handle processing completion"""
        self.translated_text.setPlainText(result)
        self._update_word_counts()
        
        if self.highlight_action.isChecked():
            self._highlight_translated_terms()
        
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Processing completed successfully")
    
    def _on_processing_error(self, error: str):
        """Handle processing error"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"Processing failed:\n{error}")
        self.status_bar.showMessage("Processing failed")
    
    def _on_progress(self, value: int, message: str):
        """Update progress bar"""
        self.progress_bar.setValue(value)
        self.status_bar.showMessage(message)
    
    def _on_clear(self):
        """Clear all text"""
        self.original_text.clear()
        self.translated_text.clear()
        self._update_word_counts()
        self.status_bar.showMessage("Cleared")
