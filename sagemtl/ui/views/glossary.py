"""Glossary view for SageMTL.

This module provides the glossary management view with:
- Term editor with search and filtering
- Import/export functionality
- Category management
- Novel-specific glossaries
"""

from __future__ import annotations

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
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QFrame,
        QDialog,
        QFormLayout,
        QDialogButtonBox,
        QFileDialog,
        QMessageBox,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from ..constants import Spacing, Icons, Typography
from ..theme import get_theme_manager
from ..components.buttons import PrimaryButton, SecondaryButton, IconButton


if HAS_PYSIDE6:
    class AddTermDialog(QDialog):
        """Dialog for adding/editing glossary terms."""

        def __init__(
            self,
            parent: Optional[QWidget] = None,
            source: str = "",
            target: str = "",
            category: str = "",
        ):
            super().__init__(parent)
            self._source = source
            self._target = target
            self._category = category

            self.setWindowTitle("Add Term" if not source else "Edit Term")
            self.setMinimumWidth(400)
            self._setup_ui()

        def _setup_ui(self) -> None:
            """Set up the dialog UI."""
            layout = QFormLayout(self)
            layout.setSpacing(Spacing.MD)

            # Source term
            self._source_input = QLineEdit(self._source)
            self._source_input.setPlaceholderText("Original term (e.g., Chinese)")
            layout.addRow("Source Term:", self._source_input)

            # Target term
            self._target_input = QLineEdit(self._target)
            self._target_input.setPlaceholderText("Translation (e.g., English)")
            layout.addRow("Translation:", self._target_input)

            # Category
            self._category_input = QComboBox()
            self._category_input.setEditable(True)
            self._category_input.addItems([
                "",
                "Character Names",
                "Place Names",
                "Cultivation Terms",
                "Titles",
                "Items",
                "Skills",
                "Organizations",
            ])
            self._category_input.setCurrentText(self._category)
            layout.addRow("Category:", self._category_input)

            # Buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok |
                QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addRow(buttons)

        def get_values(self) -> tuple:
            """Get the dialog values."""
            return (
                self._source_input.text().strip(),
                self._target_input.text().strip(),
                self._category_input.currentText().strip(),
            )


    class GlossaryView(QWidget):
        """Glossary management view.

        Features:
        - Term list with search and filtering
        - Add/edit/delete terms
        - Import from CSV/JSON
        - Export to CSV/JSON
        - Category management

        Usage:
            view = GlossaryView()
            view.load_terms(term_list)
            view.term_added.connect(on_term_added)
        """

        term_added = Signal(str, str, str)  # source, target, category
        term_updated = Signal(int, str, str, str)  # id, source, target, category
        term_deleted = Signal(int)  # id
        import_requested = Signal(str)  # file path
        export_requested = Signal(str)  # file path

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._terms: List[dict] = []
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._apply_theme()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        def load_terms(self, terms: List[dict]) -> None:
            """Load glossary terms.

            Args:
                terms: List of term dictionaries with keys:
                    - id: Unique identifier
                    - source: Source term
                    - target: Target translation
                    - category: Optional category
            """
            self._terms = terms
            self._refresh_table()

        def _setup_ui(self) -> None:
            """Set up the glossary UI."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
            layout.setSpacing(Spacing.MD)

            # Header
            header = QLabel("Glossary")
            header.setStyleSheet(f"""
                font-size: {Typography.SIZE_XXL}px;
                font-weight: {Typography.WEIGHT_BOLD};
            """)
            layout.addWidget(header)

            # Toolbar
            toolbar = self._create_toolbar()
            layout.addLayout(toolbar)

            # Table
            self._table = QTableWidget()
            self._table.setColumnCount(4)
            self._table.setHorizontalHeaderLabels([
                "Source Term", "Translation", "Category", "Actions"
            ])
            self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            self._table.setColumnWidth(2, 150)
            self._table.setColumnWidth(3, 100)
            self._table.verticalHeader().setVisible(False)
            self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            layout.addWidget(self._table, 1)

            # Stats bar
            stats_bar = self._create_stats_bar()
            layout.addLayout(stats_bar)

        def _create_toolbar(self) -> QHBoxLayout:
            """Create the toolbar."""
            layout = QHBoxLayout()
            layout.setSpacing(Spacing.SM)

            # Search
            self._search_input = QLineEdit()
            self._search_input.setPlaceholderText("Search terms...")
            self._search_input.setMinimumWidth(250)
            self._search_input.textChanged.connect(self._on_search)
            layout.addWidget(self._search_input)

            # Category filter
            self._category_filter = QComboBox()
            self._category_filter.addItem("All Categories")
            self._category_filter.setMinimumWidth(150)
            self._category_filter.currentIndexChanged.connect(self._on_filter_changed)
            layout.addWidget(self._category_filter)

            layout.addStretch()

            # Import button
            import_btn = SecondaryButton("Import", Icons.IMPORT.value)
            import_btn.clicked.connect(self._on_import)
            layout.addWidget(import_btn)

            # Export button
            export_btn = SecondaryButton("Export", Icons.EXPORT.value)
            export_btn.clicked.connect(self._on_export)
            layout.addWidget(export_btn)

            # Add button
            add_btn = PrimaryButton("Add Term", Icons.ADD.value)
            add_btn.clicked.connect(self._on_add_term)
            layout.addWidget(add_btn)

            return layout

        def _create_stats_bar(self) -> QHBoxLayout:
            """Create the stats bar."""
            layout = QHBoxLayout()

            self._stats_label = QLabel("0 terms")
            self._stats_label.setStyleSheet(f"font-size: {Typography.SIZE_SM}px;")
            layout.addWidget(self._stats_label)

            layout.addStretch()

            return layout

        def _refresh_table(self) -> None:
            """Refresh the terms table."""
            self._table.setRowCount(len(self._terms))

            # Update category filter
            categories = set()
            for term in self._terms:
                if term.get("category"):
                    categories.add(term["category"])

            self._category_filter.clear()
            self._category_filter.addItem("All Categories")
            for category in sorted(categories):
                self._category_filter.addItem(category)

            # Populate table
            for row, term in enumerate(self._terms):
                # Source
                source_item = QTableWidgetItem(term.get("source", ""))
                self._table.setItem(row, 0, source_item)

                # Target
                target_item = QTableWidgetItem(term.get("target", ""))
                self._table.setItem(row, 1, target_item)

                # Category
                category_item = QTableWidgetItem(term.get("category", ""))
                self._table.setItem(row, 2, category_item)

                # Actions
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 4, 4, 4)
                actions_layout.setSpacing(4)

                edit_btn = IconButton(Icons.EDIT.value, size=24)
                edit_btn.setToolTip("Edit")
                edit_btn.clicked.connect(lambda r=row: self._on_edit_term(r))
                actions_layout.addWidget(edit_btn)

                delete_btn = IconButton(Icons.DELETE.value, size=24)
                delete_btn.setToolTip("Delete")
                delete_btn.clicked.connect(lambda r=row: self._on_delete_term(r))
                actions_layout.addWidget(delete_btn)

                self._table.setCellWidget(row, 3, actions_widget)

            # Update stats
            self._stats_label.setText(f"{len(self._terms)} terms")

        def _on_search(self, text: str) -> None:
            """Handle search input."""
            search_lower = text.lower()
            for row in range(self._table.rowCount()):
                source = self._table.item(row, 0).text().lower()
                target = self._table.item(row, 1).text().lower()
                visible = (
                    not text or
                    search_lower in source or
                    search_lower in target
                )
                self._table.setRowHidden(row, not visible)

        def _on_filter_changed(self, index: int) -> None:
            """Handle category filter change."""
            if index == 0:
                # Show all
                for row in range(self._table.rowCount()):
                    self._table.setRowHidden(row, False)
            else:
                category = self._category_filter.currentText()
                for row in range(self._table.rowCount()):
                    row_category = self._table.item(row, 2).text()
                    self._table.setRowHidden(row, row_category != category)

        def _on_add_term(self) -> None:
            """Handle add term button."""
            dialog = AddTermDialog(self)
            if dialog.exec():
                source, target, category = dialog.get_values()
                if source and target:
                    self.term_added.emit(source, target, category)
                    # Add to local list for immediate display
                    self._terms.append({
                        "source": source,
                        "target": target,
                        "category": category,
                    })
                    self._refresh_table()

        def _on_edit_term(self, row: int) -> None:
            """Handle edit term button."""
            if row < len(self._terms):
                term = self._terms[row]
                dialog = AddTermDialog(
                    self,
                    source=term.get("source", ""),
                    target=term.get("target", ""),
                    category=term.get("category", ""),
                )
                if dialog.exec():
                    source, target, category = dialog.get_values()
                    if source and target:
                        term_id = term.get("id", row)
                        self.term_updated.emit(term_id, source, target, category)
                        # Update local list
                        self._terms[row] = {
                            "id": term_id,
                            "source": source,
                            "target": target,
                            "category": category,
                        }
                        self._refresh_table()

        def _on_delete_term(self, row: int) -> None:
            """Handle delete term button."""
            if row < len(self._terms):
                term = self._terms[row]
                reply = QMessageBox.question(
                    self,
                    "Delete Term",
                    f"Are you sure you want to delete '{term.get('source', '')}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    term_id = term.get("id", row)
                    self.term_deleted.emit(term_id)
                    # Remove from local list
                    del self._terms[row]
                    self._refresh_table()

        def _on_import(self) -> None:
            """Handle import button."""
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Glossary",
                "",
                "CSV Files (*.csv);;JSON Files (*.json);;All Files (*)",
            )
            if file_path:
                self.import_requested.emit(file_path)

        def _on_export(self) -> None:
            """Handle export button."""
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Glossary",
                "glossary.csv",
                "CSV Files (*.csv);;JSON Files (*.json);;All Files (*)",
            )
            if file_path:
                self.export_requested.emit(file_path)

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            self.setStyleSheet(f"""
                GlossaryView {{
                    background-color: {colors.background};
                }}
                QLabel {{
                    color: {colors.text_primary};
                    background-color: transparent;
                }}
            """)

else:
    class GlossaryView:
        """Stub GlossaryView when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")
