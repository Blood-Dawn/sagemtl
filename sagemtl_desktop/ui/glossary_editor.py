"""
Glossary Editor Dialog for managing global and novel-specific glossary terms.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QWidget, QLineEdit, QComboBox, QCheckBox, QTextEdit,
    QMessageBox, QFileDialog, QMenu, QFormLayout, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from sagemtl_desktop.core.glossary_manager import GlossaryManager, GlossaryTerm


class GlossaryEditorDialog(QDialog):
    """
    Dialog for managing glossary terms.
    
    Features:
    - Tab for Global glossary (applies to all novels)
    - Tab for Novel-specific glossary
    - Add/Edit/Delete terms
    - Import/Export CSV
    - Search/filter
    """
    
    glossary_updated = Signal()  # Emitted when glossary changes
    
    def __init__(self, glossary_manager: GlossaryManager, 
                 novel_id: str = None, novel_title: str = None,
                 parent=None):
        super().__init__(parent)
        self.glossary_manager = glossary_manager
        self.novel_id = novel_id
        self.novel_title = novel_title or "Current Novel"
        
        self.setWindowTitle("Glossary Manager")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)
        
        self._init_ui()
        self._load_data()
    
    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Tab widget for Global vs Novel glossary
        self.tab_widget = QTabWidget()
        
        # Global glossary tab
        self.global_tab = self._create_glossary_tab("global")
        self.tab_widget.addTab(self.global_tab, "🌐 Global Glossary")
        
        # Novel-specific glossary tab
        if self.novel_id:
            self.novel_tab = self._create_glossary_tab("novel")
            self.tab_widget.addTab(self.novel_tab, f"📖 {self.novel_title[:30]}...")
        
        layout.addWidget(self.tab_widget)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("📥 Import CSV")
        self.import_btn.clicked.connect(self._on_import)
        button_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 Export CSV")
        self.export_btn.clicked.connect(self._on_export)
        button_layout.addWidget(self.export_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_glossary_tab(self, glossary_type: str) -> QWidget:
        """Create a tab for either global or novel glossary"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Search:")
        search_layout.addWidget(search_label)
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Filter terms...")
        search_input.textChanged.connect(
            lambda text, t=glossary_type: self._filter_table(text, t)
        )
        search_layout.addWidget(search_input)
        
        layout.addLayout(search_layout)
        
        # Table for terms
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Source", "Target", "Category", "Case", "Word Bound", "Notes"
        ])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(
            lambda pos, t=glossary_type: self._show_context_menu(pos, t)
        )
        table.cellDoubleClicked.connect(
            lambda row, col, t=glossary_type: self._on_edit_term(t)
        )
        
        # Store reference
        if glossary_type == "global":
            self.global_table = table
            self.global_search = search_input
        else:
            self.novel_table = table
            self.novel_search = search_input
        
        layout.addWidget(table)
        
        # Add/Edit/Delete buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ Add Term")
        add_btn.clicked.connect(lambda checked, t=glossary_type: self._on_add_term(t))
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("✏️ Edit Selected")
        edit_btn.clicked.connect(lambda checked, t=glossary_type: self._on_edit_term(t))
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.clicked.connect(lambda checked, t=glossary_type: self._on_delete_term(t))
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        # Stats label
        stats_label = QLabel("0 terms")
        if glossary_type == "global":
            self.global_stats = stats_label
        else:
            self.novel_stats = stats_label
        btn_layout.addWidget(stats_label)
        
        layout.addLayout(btn_layout)
        
        return tab
    
    def _load_data(self):
        """Load glossary data into tables"""
        # Load global terms
        global_terms = self.glossary_manager.get_global_terms()
        self._populate_table(self.global_table, global_terms)
        self.global_stats.setText(f"{len(global_terms)} terms")
        
        # Load novel terms if applicable
        if self.novel_id:
            novel_terms = self.glossary_manager.get_novel_terms(self.novel_id)
            self._populate_table(self.novel_table, novel_terms)
            self.novel_stats.setText(f"{len(novel_terms)} terms")
    
    def _populate_table(self, table: QTableWidget, terms: list):
        """Populate a table with glossary terms"""
        table.clearContents()  # Clear existing content first
        table.setRowCount(len(terms))
        
        for row, term in enumerate(terms):
            table.setItem(row, 0, QTableWidgetItem(term.source))
            table.setItem(row, 1, QTableWidgetItem(term.target))
            table.setItem(row, 2, QTableWidgetItem(term.category))
            
            case_item = QTableWidgetItem("✓" if term.case_sensitive else "")
            case_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 3, case_item)
            
            bound_item = QTableWidgetItem("✓" if term.word_boundary else "")
            bound_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 4, bound_item)
            
            table.setItem(row, 5, QTableWidgetItem(term.notes))
    
    def _filter_table(self, text: str, glossary_type: str):
        """Filter table rows based on search text"""
        table = self.global_table if glossary_type == "global" else self.novel_table
        text = text.lower()
        
        for row in range(table.rowCount()):
            show = False
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item and text in item.text().lower():
                    show = True
                    break
            table.setRowHidden(row, not show)
    
    def _show_context_menu(self, pos, glossary_type: str):
        """Show right-click context menu"""
        table = self.global_table if glossary_type == "global" else self.novel_table
        
        menu = QMenu(self)
        
        edit_action = QAction("✏️ Edit", self)
        edit_action.triggered.connect(lambda: self._on_edit_term(glossary_type))
        menu.addAction(edit_action)
        
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(lambda: self._on_delete_term(glossary_type))
        menu.addAction(delete_action)
        
        menu.addSeparator()
        
        if glossary_type == "novel" and self.novel_id:
            promote_action = QAction("⬆️ Move to Global", self)
            promote_action.triggered.connect(lambda: self._on_promote_to_global())
            menu.addAction(promote_action)
        elif glossary_type == "global" and self.novel_id:
            demote_action = QAction("⬇️ Copy to Novel", self)
            demote_action.triggered.connect(lambda: self._on_copy_to_novel())
            menu.addAction(demote_action)
        
        menu.exec_(table.mapToGlobal(pos))
    
    def _on_add_term(self, glossary_type: str):
        """Add a new term"""
        dialog = TermEditorDialog(parent=self)
        if dialog.exec():
            term = dialog.get_term()
            
            if glossary_type == "global":
                if self.glossary_manager.add_global_term(term):
                    self._load_data()
                    self.glossary_updated.emit()
                else:
                    QMessageBox.warning(self, "Duplicate", 
                        f"A term with source '{term.source}' already exists.")
            elif self.glossary_manager.add_novel_term(self.novel_id, term):
                self._load_data()
                self.glossary_updated.emit()
            else:
                QMessageBox.warning(self, "Duplicate",
                    f"A term with source '{term.source}' already exists.")
    
    def _on_edit_term(self, glossary_type: str):
        """Edit the selected term"""
        table = self.global_table if glossary_type == "global" else self.novel_table
        row = table.currentRow()
        
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select a term to edit.")
            return
        
        # Get current term data
        source = table.item(row, 0).text()
        target = table.item(row, 1).text()
        category = table.item(row, 2).text() if table.item(row, 2) else ""
        case_sensitive = table.item(row, 3).text() == "✓"
        word_boundary = table.item(row, 4).text() == "✓"
        notes = table.item(row, 5).text() if table.item(row, 5) else ""
        
        current_term = GlossaryTerm(
            source=source,
            target=target,
            category=category,
            case_sensitive=case_sensitive,
            word_boundary=word_boundary,
            notes=notes
        )
        
        dialog = TermEditorDialog(term=current_term, parent=self)
        if dialog.exec():
            updated_term = dialog.get_term()
            
            if glossary_type == "global":
                self.glossary_manager.update_global_term(source, updated_term)
            else:
                self.glossary_manager.update_novel_term(self.novel_id, source, updated_term)
            
            self._load_data()
            self.glossary_updated.emit()
    
    def _on_delete_term(self, glossary_type: str):
        """Delete the selected term"""
        table = self.global_table if glossary_type == "global" else self.novel_table
        row = table.currentRow()
        
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select a term to delete.")
            return
        
        source = table.item(row, 0).text()
        target = table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete term?\n\n'{source}' → '{target}'",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if glossary_type == "global":
                self.glossary_manager.remove_global_term(source)
            else:
                self.glossary_manager.remove_novel_term(self.novel_id, source)
            
            self._load_data()
            self.glossary_updated.emit()
    
    def _on_promote_to_global(self):
        """Move a novel term to global glossary"""
        row = self.novel_table.currentRow()
        if row < 0:
            return
        
        source = self.novel_table.item(row, 0).text()
        target = self.novel_table.item(row, 1).text()
        category = self.novel_table.item(row, 2).text() if self.novel_table.item(row, 2) else ""
        case_sensitive = self.novel_table.item(row, 3).text() == "✓"
        word_boundary = self.novel_table.item(row, 4).text() == "✓"
        notes = self.novel_table.item(row, 5).text() if self.novel_table.item(row, 5) else ""
        
        term = GlossaryTerm(
            source=source, target=target, category=category,
            case_sensitive=case_sensitive, word_boundary=word_boundary, notes=notes
        )
        
        if self.glossary_manager.add_global_term(term):
            self.glossary_manager.remove_novel_term(self.novel_id, source)
            self._load_data()
            self.glossary_updated.emit()
            QMessageBox.information(self, "Moved", f"'{source}' moved to global glossary.")
        else:
            QMessageBox.warning(self, "Exists", "Term already exists in global glossary.")
    
    def _on_copy_to_novel(self):
        """Copy a global term to novel glossary"""
        row = self.global_table.currentRow()
        if row < 0:
            return
        
        source = self.global_table.item(row, 0).text()
        target = self.global_table.item(row, 1).text()
        category = self.global_table.item(row, 2).text() if self.global_table.item(row, 2) else ""
        case_sensitive = self.global_table.item(row, 3).text() == "✓"
        word_boundary = self.global_table.item(row, 4).text() == "✓"
        notes = self.global_table.item(row, 5).text() if self.global_table.item(row, 5) else ""
        
        term = GlossaryTerm(
            source=source, target=target, category=category,
            case_sensitive=case_sensitive, word_boundary=word_boundary, notes=notes
        )
        
        if self.glossary_manager.add_novel_term(self.novel_id, term):
            self._load_data()
            self.glossary_updated.emit()
            QMessageBox.information(self, "Copied", f"'{source}' copied to novel glossary.")
        else:
            QMessageBox.warning(self, "Exists", "Term already exists in novel glossary.")
    
    def _on_import(self):
        """Import terms from CSV"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Glossary CSV", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Ask which glossary to import to
        current_tab = "global" if self.tab_widget.currentIndex() == 0 else "novel"
        
        if current_tab == "global":
            target = "global"
            novel_id = None
        else:
            target = "novel"
            novel_id = self.novel_id
        
        result = self.glossary_manager.import_from_csv(file_path, target, novel_id)
        
        if result['success']:
            self._load_data()
            self.glossary_updated.emit()
            msg = f"Imported {result['terms_added']} terms"
            if result['terms_skipped']:
                msg += f"\nSkipped {result['terms_skipped']} duplicates"
            QMessageBox.information(self, "Import Complete", msg)
        else:
            QMessageBox.critical(self, "Import Failed", result.get('error', 'Unknown error'))
    
    def _on_export(self):
        """Export terms to CSV"""
        current_tab = "global" if self.tab_widget.currentIndex() == 0 else "novel"
        
        default_name = "global_glossary.csv" if current_tab == "global" else f"{self.novel_id}_glossary.csv"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Glossary CSV", default_name,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        result = self.glossary_manager.export_to_csv(
            file_path, 
            current_tab,
            self.novel_id if current_tab == "novel" else None
        )
        
        if result['success']:
            QMessageBox.information(self, "Export Complete", 
                f"Exported {result['terms_exported']} terms to:\n{file_path}")
        else:
            QMessageBox.critical(self, "Export Failed", result.get('error', 'Unknown error'))


class TermEditorDialog(QDialog):
    """Dialog for adding/editing a single glossary term"""
    
    def __init__(self, term: GlossaryTerm = None, parent=None):
        super().__init__(parent)
        self.term = term
        
        self.setWindowTitle("Edit Term" if term else "Add Term")
        self.setMinimumWidth(500)
        
        self._init_ui()
        
        if term:
            self._load_term(term)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Source text
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Original text to find...")
        form.addRow("Source:", self.source_input)
        
        # Target text
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Replacement text...")
        form.addRow("Target:", self.target_input)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(GlossaryManager.CATEGORIES)
        form.addRow("Category:", self.category_combo)
        
        # Options
        options_layout = QHBoxLayout()
        
        self.case_check = QCheckBox("Case Sensitive")
        options_layout.addWidget(self.case_check)
        
        self.boundary_check = QCheckBox("Word Boundary")
        self.boundary_check.setChecked(True)  # Default on
        self.boundary_check.setToolTip("Only match whole words, not substrings")
        options_layout.addWidget(self.boundary_check)
        
        options_layout.addStretch()
        form.addRow("Options:", options_layout)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlaceholderText("Optional notes about this term...")
        form.addRow("Notes:", self.notes_input)
        
        layout.addLayout(form)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_term(self, term: GlossaryTerm):
        """Load existing term data"""
        self.source_input.setText(term.source)
        self.target_input.setText(term.target)
        self.category_combo.setCurrentText(term.category)
        self.case_check.setChecked(term.case_sensitive)
        self.boundary_check.setChecked(term.word_boundary)
        self.notes_input.setPlainText(term.notes)
    
    def _on_save(self):
        """Validate and accept"""
        if not self.source_input.text().strip():
            QMessageBox.warning(self, "Missing Source", "Please enter source text.")
            return
        
        if not self.target_input.text().strip():
            QMessageBox.warning(self, "Missing Target", "Please enter target text.")
            return
        
        self.accept()
    
    def get_term(self) -> GlossaryTerm:
        """Get the term from form data"""
        return GlossaryTerm(
            source=self.source_input.text().strip(),
            target=self.target_input.text().strip(),
            category=self.category_combo.currentText(),
            case_sensitive=self.case_check.isChecked(),
            word_boundary=self.boundary_check.isChecked(),
            notes=self.notes_input.toPlainText().strip()
        )


class QuickTermDialog(QDialog):
    """
    Quick dialog for adding a term from selected text.
    Used when user selects text in the preview and wants to add it to glossary.
    """
    
    def __init__(self, selected_text: str, glossary_type: str = "novel", parent=None):
        super().__init__(parent)
        self.selected_text = selected_text
        self.glossary_type = glossary_type
        
        self.setWindowTitle("Add to Glossary")
        self.setMinimumWidth(400)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Source (pre-filled with selection)
        self.source_input = QLineEdit(self.selected_text)
        form.addRow("Source:", self.source_input)
        
        # Target
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Enter replacement...")
        self.target_input.setFocus()
        form.addRow("Replace with:", self.target_input)
        
        # Glossary type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Novel Glossary", "Global Glossary"])
        if self.glossary_type == "global":
            self.type_combo.setCurrentIndex(1)
        form.addRow("Add to:", self.type_combo)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(GlossaryManager.CATEGORIES)
        form.addRow("Category:", self.category_combo)
        
        layout.addLayout(form)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        add_btn = QPushButton("Add")
        add_btn.setDefault(True)
        add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(add_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_add(self):
        if not self.target_input.text().strip():
            QMessageBox.warning(self, "Missing", "Please enter replacement text.")
            return
        self.accept()
    
    def get_term(self) -> GlossaryTerm:
        return GlossaryTerm(
            source=self.source_input.text().strip(),
            target=self.target_input.text().strip(),
            category=self.category_combo.currentText(),
            word_boundary=True
        )
    
    def is_global(self) -> bool:
        return self.type_combo.currentIndex() == 1
