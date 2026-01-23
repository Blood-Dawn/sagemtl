"""Library view for SageMTL.

This module provides the library view with:
- Grid/list view toggle
- Novel cards with covers
- Search and filtering
- Sort options
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
        QScrollArea,
        QGridLayout,
        QFrame,
        QSizePolicy,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from ..constants import Spacing, Icons, Typography
from ..theme import get_theme_manager
from ..components.cards import NovelCard
from ..components.buttons import IconButton, PrimaryButton


if HAS_PYSIDE6:
    class LibraryView(QWidget):
        """Library view showing all downloaded novels.

        Features:
        - Grid/list view toggle
        - Search filtering
        - Sort by title, date, progress
        - Novel cards with covers

        Usage:
            library = LibraryView()
            library.novel_selected.connect(on_novel_opened)
            library.load_novels(novel_list)
        """

        novel_selected = Signal(str)  # Emits novel ID
        download_requested = Signal()

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._novels: List[dict] = []
            self._cards: List[NovelCard] = []
            self._grid_view = True
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._apply_theme()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        def load_novels(self, novels: List[dict]) -> None:
            """Load novels into the library.

            Args:
                novels: List of novel dictionaries with keys:
                    - id: Unique identifier
                    - title: Novel title
                    - author: Author name (optional)
                    - cover: Cover image path (optional)
                    - chapters: Total chapter count
                    - read_chapters: Number of read chapters
                    - status: Novel status
            """
            self._novels = novels
            self._refresh_grid()

        def _setup_ui(self) -> None:
            """Set up the library UI."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
            layout.setSpacing(Spacing.MD)

            # Header
            header = self._create_header()
            layout.addLayout(header)

            # Toolbar
            toolbar = self._create_toolbar()
            layout.addLayout(toolbar)

            # Content area (scrollable)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setFrameShape(QFrame.Shape.NoFrame)

            self._content_widget = QWidget()
            self._content_layout = QGridLayout(self._content_widget)
            self._content_layout.setContentsMargins(0, 0, 0, 0)
            self._content_layout.setSpacing(Spacing.MD)
            self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            scroll.setWidget(self._content_widget)
            layout.addWidget(scroll)

        def _create_header(self) -> QHBoxLayout:
            """Create the header with title and add button."""
            layout = QHBoxLayout()
            layout.setSpacing(Spacing.MD)

            # Title
            title = QLabel("Library")
            title.setStyleSheet(f"""
                font-size: {Typography.SIZE_XXL}px;
                font-weight: {Typography.WEIGHT_BOLD};
            """)
            layout.addWidget(title)

            layout.addStretch()

            # Add novel button
            add_btn = PrimaryButton("Add Novel", Icons.ADD.value)
            add_btn.clicked.connect(self.download_requested.emit)
            layout.addWidget(add_btn)

            return layout

        def _create_toolbar(self) -> QHBoxLayout:
            """Create the toolbar with search and filters."""
            layout = QHBoxLayout()
            layout.setSpacing(Spacing.SM)

            # Search
            self._search_input = QLineEdit()
            self._search_input.setPlaceholderText("Search novels...")
            self._search_input.setMinimumWidth(250)
            self._search_input.textChanged.connect(self._on_search)
            layout.addWidget(self._search_input)

            layout.addStretch()

            # Sort dropdown
            sort_label = QLabel("Sort by:")
            layout.addWidget(sort_label)

            self._sort_combo = QComboBox()
            self._sort_combo.addItems(["Title", "Date Added", "Progress", "Chapters"])
            self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
            layout.addWidget(self._sort_combo)

            layout.addSpacing(Spacing.SM)

            # View toggle
            self._grid_btn = IconButton(Icons.FILTER.value)
            self._grid_btn.setToolTip("Grid view")
            self._grid_btn.clicked.connect(lambda: self._set_view_mode(True))
            layout.addWidget(self._grid_btn)

            self._list_btn = IconButton(Icons.SORT.value)
            self._list_btn.setToolTip("List view")
            self._list_btn.clicked.connect(lambda: self._set_view_mode(False))
            layout.addWidget(self._list_btn)

            return layout

        def _refresh_grid(self) -> None:
            """Refresh the novel grid."""
            # Clear existing cards
            for card in self._cards:
                card.deleteLater()
            self._cards.clear()

            # Clear layout
            while self._content_layout.count():
                item = self._content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add novel cards
            columns = 5 if self._grid_view else 1
            for i, novel in enumerate(self._novels):
                card = NovelCard(
                    title=novel.get("title", "Unknown"),
                    author=novel.get("author", ""),
                    cover_path=novel.get("cover"),
                    chapters=novel.get("chapters", 0),
                    read_chapters=novel.get("read_chapters", 0),
                    status=novel.get("status", ""),
                )
                card.clicked.connect(
                    lambda nid=novel.get("id"): self.novel_selected.emit(nid)
                )
                self._cards.append(card)

                row = i // columns
                col = i % columns
                self._content_layout.addWidget(card, row, col)

            # Show empty state if no novels
            if not self._novels:
                empty_label = QLabel("No novels in library.\nClick 'Add Novel' to get started.")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_label.setStyleSheet(f"""
                    color: {self._theme_manager.current_theme.colors.text_secondary};
                    font-size: {Typography.SIZE_LG}px;
                    padding: {Spacing.XXL}px;
                """)
                self._content_layout.addWidget(empty_label, 0, 0, 1, columns)

        def _set_view_mode(self, grid: bool) -> None:
            """Set the view mode."""
            if self._grid_view != grid:
                self._grid_view = grid
                self._refresh_grid()

        def _on_search(self, text: str) -> None:
            """Handle search input."""
            search_lower = text.lower()
            for card in self._cards:
                visible = (
                    not text or
                    search_lower in card._title.lower() or
                    search_lower in card._author.lower()
                )
                card.setVisible(visible)

        def _on_sort_changed(self, index: int) -> None:
            """Handle sort selection change."""
            sort_keys = ["title", "date_added", "progress", "chapters"]
            if index < len(sort_keys):
                key = sort_keys[index]
                reverse = key != "title"
                self._novels.sort(
                    key=lambda n: n.get(key, ""),
                    reverse=reverse
                )
                self._refresh_grid()

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            self.setStyleSheet(f"""
                LibraryView {{
                    background-color: {colors.background};
                }}
                QLabel {{
                    color: {colors.text_primary};
                }}
                QScrollArea {{
                    background-color: transparent;
                }}
                QScrollArea > QWidget > QWidget {{
                    background-color: transparent;
                }}
            """)

else:
    class LibraryView:
        """Stub LibraryView when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")
