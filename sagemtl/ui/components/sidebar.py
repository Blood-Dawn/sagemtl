"""Sidebar navigation component for SageMTL.

This module provides a Fluent-style sidebar with:
- Expandable/collapsible navigation
- Icon and text navigation items
- Active state indication
- Keyboard navigation support
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

try:
    from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QLabel,
        QScrollArea,
        QSizePolicy,
        QFrame,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from ..constants import Spacing, Icons, Typography
from ..theme import get_theme_manager


@dataclass
class SidebarItem:
    """Definition for a sidebar navigation item."""

    id: str
    label: str
    icon: str
    tooltip: str = ""
    badge: Optional[str] = None


if HAS_PYSIDE6:
    class SidebarButton(QPushButton):
        """Individual navigation button in the sidebar."""

        def __init__(
            self,
            item: SidebarItem,
            collapsed: bool = False,
            parent: Optional[QWidget] = None,
        ):
            super().__init__(parent)
            self._item = item
            self._collapsed = collapsed
            self._active = False
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        @property
        def item(self) -> SidebarItem:
            """Get the sidebar item definition."""
            return self._item

        @property
        def active(self) -> bool:
            """Check if this button is active."""
            return self._active

        @active.setter
        def active(self, value: bool) -> None:
            """Set the active state."""
            self._active = value
            self._apply_theme()

        def set_collapsed(self, collapsed: bool) -> None:
            """Update collapsed state."""
            self._collapsed = collapsed
            self._update_content()

        def _setup_ui(self) -> None:
            """Set up the button UI."""
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            self.setToolTip(self._item.tooltip or self._item.label)
            self._update_content()
            self._apply_theme()

        def _update_content(self) -> None:
            """Update button content based on collapsed state."""
            if self._collapsed:
                self.setText(self._item.icon)
                self.setFixedSize(
                    Spacing.SIDEBAR_COLLAPSED_WIDTH - Spacing.SM * 2,
                    44
                )
            else:
                self.setText(f"  {self._item.icon}    {self._item.label}")
                self.setFixedHeight(44)
                self.setMinimumWidth(Spacing.SIDEBAR_WIDTH - Spacing.SM * 2)

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            if self._active:
                bg = colors.sidebar_item_active
                text = colors.accent
            else:
                bg = "transparent"
                text = colors.sidebar_text

            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {text};
                    border: none;
                    border-radius: {Spacing.RADIUS_SM}px;
                    padding: {Spacing.SM}px {Spacing.MD}px;
                    text-align: left;
                    font-family: "Segoe Fluent Icons", "Segoe UI";
                    font-size: {Typography.SIZE_MD}px;
                }}
                QPushButton:hover {{
                    background-color: {colors.sidebar_item_hover};
                }}
                QPushButton:focus {{
                    outline: 2px solid {colors.accent};
                    outline-offset: -2px;
                }}
            """)


    class Sidebar(QWidget):
        """Fluent-style sidebar navigation component.

        Features:
        - Expandable/collapsible sidebar
        - Icon and text navigation items
        - Active state indication
        - Smooth animations

        Usage:
            sidebar = Sidebar()
            sidebar.add_item(SidebarItem("home", "Home", Icons.HOME))
            sidebar.add_item(SidebarItem("library", "Library", Icons.LIBRARY))
            sidebar.item_clicked.connect(on_nav_changed)
        """

        item_clicked = Signal(str)  # Emits item id
        collapse_changed = Signal(bool)

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._items: List[SidebarItem] = []
            self._buttons: dict[str, SidebarButton] = {}
            self._collapsed = False
            self._active_id: Optional[str] = None
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        @property
        def collapsed(self) -> bool:
            """Check if sidebar is collapsed."""
            return self._collapsed

        @collapsed.setter
        def collapsed(self, value: bool) -> None:
            """Set collapsed state with animation."""
            if self._collapsed == value:
                return
            self._collapsed = value
            self._animate_collapse()
            self.collapse_changed.emit(value)

        def toggle_collapse(self) -> None:
            """Toggle collapsed state."""
            self.collapsed = not self._collapsed

        def add_item(self, item: SidebarItem) -> None:
            """Add a navigation item to the sidebar."""
            self._items.append(item)

            button = SidebarButton(item, self._collapsed)
            button.clicked.connect(lambda: self._on_item_clicked(item.id))
            self._buttons[item.id] = button
            self._nav_layout.addWidget(button)

        def add_separator(self) -> None:
            """Add a visual separator."""
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFixedHeight(1)
            separator.setStyleSheet(f"""
                background-color: {self._theme_manager.current_theme.colors.border};
            """)
            self._nav_layout.addWidget(separator)
            self._nav_layout.addSpacing(Spacing.SM)

        def add_spacer(self) -> None:
            """Add a flexible spacer."""
            self._nav_layout.addStretch()

        def set_active(self, item_id: str) -> None:
            """Set the active navigation item."""
            if self._active_id:
                if self._active_id in self._buttons:
                    self._buttons[self._active_id].active = False

            self._active_id = item_id
            if item_id in self._buttons:
                self._buttons[item_id].active = True

        def _setup_ui(self) -> None:
            """Set up the sidebar UI."""
            self.setFixedWidth(Spacing.SIDEBAR_WIDTH)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
            layout.setSpacing(Spacing.XS)

            # Collapse toggle button
            self._toggle_btn = QPushButton(Icons.CHEVRON_LEFT.value)
            self._toggle_btn.setFixedSize(32, 32)
            self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._toggle_btn.setToolTip("Collapse sidebar")
            self._toggle_btn.clicked.connect(self.toggle_collapse)
            layout.addWidget(self._toggle_btn, alignment=Qt.AlignmentFlag.AlignRight)

            layout.addSpacing(Spacing.SM)

            # Scrollable navigation area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setFrameShape(QFrame.Shape.NoFrame)

            nav_widget = QWidget()
            self._nav_layout = QVBoxLayout(nav_widget)
            self._nav_layout.setContentsMargins(0, 0, 0, 0)
            self._nav_layout.setSpacing(Spacing.XS)
            self._nav_layout.addStretch()

            scroll.setWidget(nav_widget)
            layout.addWidget(scroll)

            self._apply_theme()

        def _on_item_clicked(self, item_id: str) -> None:
            """Handle item click."""
            self.set_active(item_id)
            self.item_clicked.emit(item_id)

        def _animate_collapse(self) -> None:
            """Animate collapse/expand transition."""
            target_width = (
                Spacing.SIDEBAR_COLLAPSED_WIDTH if self._collapsed
                else Spacing.SIDEBAR_WIDTH
            )

            # Update toggle button
            if self._collapsed:
                self._toggle_btn.setText(Icons.CHEVRON_RIGHT.value)
                self._toggle_btn.setToolTip("Expand sidebar")
            else:
                self._toggle_btn.setText(Icons.CHEVRON_LEFT.value)
                self._toggle_btn.setToolTip("Collapse sidebar")

            # Update all buttons
            for button in self._buttons.values():
                button.set_collapsed(self._collapsed)

            # Animate width
            self._animation = QPropertyAnimation(self, b"minimumWidth")
            self._animation.setDuration(200)
            self._animation.setStartValue(self.width())
            self._animation.setEndValue(target_width)
            self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animation.start()

            self._animation2 = QPropertyAnimation(self, b"maximumWidth")
            self._animation2.setDuration(200)
            self._animation2.setStartValue(self.width())
            self._animation2.setEndValue(target_width)
            self._animation2.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animation2.start()

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            self.setStyleSheet(f"""
                Sidebar {{
                    background-color: {colors.sidebar_bg};
                    border-right: 1px solid {colors.border};
                }}

                QScrollArea {{
                    background-color: transparent;
                }}

                QScrollArea > QWidget > QWidget {{
                    background-color: transparent;
                }}

                QPushButton {{
                    background-color: transparent;
                    color: {colors.sidebar_icon};
                    border: none;
                    border-radius: {Spacing.RADIUS_SM}px;
                    font-family: "Segoe Fluent Icons";
                    font-size: 14px;
                }}

                QPushButton:hover {{
                    background-color: {colors.sidebar_item_hover};
                }}
            """)

else:
    @dataclass
    class SidebarItem:
        """Definition for a sidebar navigation item."""
        id: str
        label: str
        icon: str
        tooltip: str = ""
        badge: Optional[str] = None

    class Sidebar:
        """Stub Sidebar when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")
