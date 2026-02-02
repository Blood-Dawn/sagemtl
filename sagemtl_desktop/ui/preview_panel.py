"""
Side-by-side text preview panel with glossary integration.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QSplitter, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction


class GlossaryTextEdit(QTextEdit):
    """Text edit with context menu for glossary operations"""
    
    add_to_glossary = Signal(str)  # Selected text
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _show_context_menu(self, pos):
        """Show context menu with glossary option"""
        menu = self.createStandardContextMenu()
        
        selected = self.textCursor().selectedText()
        if selected and len(selected.strip()) > 0:
            menu.addSeparator()
            
            glossary_action = QAction(f"📋 Add to Glossary: \"{selected[:30]}...\"" if len(selected) > 30 else f"📋 Add to Glossary: \"{selected}\"", self)
            glossary_action.triggered.connect(lambda: self.add_to_glossary.emit(selected))
            menu.addAction(glossary_action)
        
        menu.exec_(self.mapToGlobal(pos))


class PreviewPanel(QWidget):
    """Widget displaying original and cleaned text side-by-side"""
    
    # Signal emitted when user wants to add selected text to glossary
    add_to_glossary_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _create_text_panel(self, label_text: str, placeholder: str) -> tuple[QWidget, 'GlossaryTextEdit']:
        """Create a panel with label and text edit."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(2)

        label = QLabel(label_text)
        label.setStyleSheet("font-weight: bold; color: #888; padding: 4px;")
        layout.addWidget(label)

        text_edit = GlossaryTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlaceholderText(placeholder)
        text_edit.add_to_glossary.connect(self.add_to_glossary_requested.emit)
        layout.addWidget(text_edit)

        return container, text_edit

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Splitter for side-by-side views
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Original text
        left_container, self.original_text = self._create_text_panel(
            "Original Text", "Original text will appear here..."
        )
        splitter.addWidget(left_container)

        # Right panel - Cleaned/Translated text
        right_container, self.cleaned_text = self._create_text_panel(
            "Cleaned/Translated Text", "Cleaned text will appear here..."
        )
        splitter.addWidget(right_container)

        # Equal split
        splitter.setSizes([500, 500])

        layout.addWidget(splitter)

    def set_original_text(self, text: str):
        """
        Set original text.

        Args:
            text: Original text
        """
        self.original_text.setPlainText(text)

    def set_cleaned_text(self, text: str):
        """
        Set cleaned/translated text.

        Args:
            text: Cleaned text
        """
        self.cleaned_text.setPlainText(text)

    def clear(self):
        """Clear both text areas"""
        self.original_text.clear()
        self.cleaned_text.clear()

    def set_text_pair(self, original: str, cleaned: str):
        """
        Set both text areas at once.

        Args:
            original: Original text
            cleaned: Cleaned text
        """
        self.set_original_text(original)
        self.set_cleaned_text(cleaned)
