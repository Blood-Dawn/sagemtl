"""Custom frameless title bar for SageMTL.

This module provides a custom title bar with:
- Draggable window movement
- Minimize/maximize/close buttons
- Title and icon
- Theme toggle
"""

from __future__ import annotations

import sys
from typing import Optional

try:
    from PySide6.QtCore import Qt, QPoint, Signal
    from PySide6.QtGui import QMouseEvent, QIcon
    from PySide6.QtWidgets import (
        QWidget,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QSizePolicy,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from ..constants import Spacing, Icons, Typography
from ..theme import get_theme_manager, ThemeMode


if HAS_PYSIDE6:
    class TitleBar(QWidget):
        """Custom frameless title bar widget.

        Features:
        - Draggable area for window movement
        - Minimize, maximize, close buttons
        - Title text and optional icon
        - Theme toggle button

        Usage:
            title_bar = TitleBar(parent=main_window)
            title_bar.title = "SageMTL"
            main_window.setMenuWidget(title_bar)
        """

        # Signals
        minimize_clicked = Signal()
        maximize_clicked = Signal()
        close_clicked = Signal()
        theme_clicked = Signal()

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._title = "SageMTL"
            self._drag_pos: Optional[QPoint] = None
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._connect_signals()
            self._apply_theme()

            # Listen for theme changes
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        @property
        def title(self) -> str:
            """Get the title text."""
            return self._title

        @title.setter
        def title(self, value: str) -> None:
            """Set the title text."""
            self._title = value
            self._title_label.setText(value)

        def _setup_ui(self) -> None:
            """Set up the title bar UI."""
            self.setFixedHeight(Spacing.TITLE_BAR_HEIGHT)
            self.setMouseTracking(True)

            layout = QHBoxLayout(self)
            layout.setContentsMargins(Spacing.SM, 0, 0, 0)
            layout.setSpacing(0)

            # App icon
            self._icon_label = QLabel()
            self._icon_label.setFixedSize(24, 24)
            layout.addWidget(self._icon_label)

            layout.addSpacing(Spacing.SM)

            # Title
            self._title_label = QLabel(self._title)
            self._title_label.setStyleSheet(f"""
                font-size: {Typography.SIZE_MD}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            """)
            layout.addWidget(self._title_label)

            # Spacer
            layout.addStretch()

            # Theme toggle button
            self._theme_btn = self._create_button(Icons.SUN.value)
            self._theme_btn.setToolTip("Toggle theme")
            self._theme_btn.clicked.connect(self._on_theme_clicked)
            layout.addWidget(self._theme_btn)

            layout.addSpacing(Spacing.SM)

            # Window control buttons
            self._min_btn = self._create_button(Icons.MINIMIZE.value)
            self._min_btn.setToolTip("Minimize")
            self._min_btn.setObjectName("minimize")
            layout.addWidget(self._min_btn)

            self._max_btn = self._create_button(Icons.MAXIMIZE.value)
            self._max_btn.setToolTip("Maximize")
            self._max_btn.setObjectName("maximize")
            layout.addWidget(self._max_btn)

            self._close_btn = self._create_button(Icons.CLOSE.value)
            self._close_btn.setToolTip("Close")
            self._close_btn.setObjectName("close")
            layout.addWidget(self._close_btn)

        def _create_button(self, text: str) -> QPushButton:
            """Create a title bar button."""
            btn = QPushButton(text)
            btn.setFixedSize(46, Spacing.TITLE_BAR_HEIGHT)
            btn.setCursor(Qt.CursorShape.ArrowCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            return btn

        def _connect_signals(self) -> None:
            """Connect button signals."""
            self._min_btn.clicked.connect(self._on_minimize)
            self._max_btn.clicked.connect(self._on_maximize)
            self._close_btn.clicked.connect(self._on_close)

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors
            mode = self._theme_manager.current_mode

            # Update theme button icon
            if mode == ThemeMode.DARK:
                self._theme_btn.setText(Icons.SUN.value)
            else:
                self._theme_btn.setText(Icons.MOON.value)

            self.setStyleSheet(f"""
                TitleBar {{
                    background-color: {colors.titlebar_bg};
                }}

                QLabel {{
                    color: {colors.titlebar_text};
                    background-color: transparent;
                }}

                QPushButton {{
                    border: none;
                    background-color: transparent;
                    color: {colors.titlebar_text};
                    font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets";
                    font-size: 10px;
                }}

                QPushButton:hover {{
                    background-color: {colors.titlebar_button_hover};
                }}

                QPushButton#close:hover {{
                    background-color: {colors.titlebar_button_close_hover};
                    color: white;
                }}
            """)

        def _on_minimize(self) -> None:
            """Handle minimize button click."""
            self.minimize_clicked.emit()
            if self.window():
                self.window().showMinimized()

        def _on_maximize(self) -> None:
            """Handle maximize button click."""
            self.maximize_clicked.emit()
            if self.window():
                if self.window().isMaximized():
                    self.window().showNormal()
                    self._max_btn.setText(Icons.MAXIMIZE.value)
                    self._max_btn.setToolTip("Maximize")
                else:
                    self.window().showMaximized()
                    self._max_btn.setText(Icons.RESTORE.value)
                    self._max_btn.setToolTip("Restore")

        def _on_close(self) -> None:
            """Handle close button click."""
            self.close_clicked.emit()
            if self.window():
                self.window().close()

        def _on_theme_clicked(self) -> None:
            """Handle theme toggle button click."""
            self.theme_clicked.emit()
            current = self._theme_manager.current_mode
            if current == ThemeMode.DARK:
                self._theme_manager.set_theme_mode(ThemeMode.LIGHT)
            else:
                self._theme_manager.set_theme_mode(ThemeMode.DARK)

        def mousePressEvent(self, event: QMouseEvent) -> None:
            """Start window drag on mouse press."""
            if event.button() == Qt.MouseButton.LeftButton:
                # Check if we're in the draggable area (not on buttons)
                if event.position().x() < self.width() - 138:  # 3 buttons * 46
                    self._drag_pos = event.globalPosition().toPoint()
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event: QMouseEvent) -> None:
            """Move window during drag."""
            if self._drag_pos is not None:
                window = self.window()
                if window:
                    # Restore if maximized
                    if window.isMaximized():
                        window.showNormal()
                        self._max_btn.setText(Icons.MAXIMIZE.value)
                        # Adjust position relative to mouse
                        ratio = event.position().x() / self.width()
                        new_pos = event.globalPosition().toPoint()
                        window.move(
                            int(new_pos.x() - window.width() * ratio),
                            int(new_pos.y() - self.height() / 2)
                        )
                        self._drag_pos = event.globalPosition().toPoint()
                    else:
                        delta = event.globalPosition().toPoint() - self._drag_pos
                        window.move(window.pos() + delta)
                        self._drag_pos = event.globalPosition().toPoint()
            super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event: QMouseEvent) -> None:
            """End window drag on mouse release."""
            self._drag_pos = None
            super().mouseReleaseEvent(event)

        def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
            """Toggle maximize on double click."""
            if event.button() == Qt.MouseButton.LeftButton:
                if event.position().x() < self.width() - 138:
                    self._on_maximize()
            super().mouseDoubleClickEvent(event)

else:
    # Stub for when PySide6 is not available
    class TitleBar:
        """Stub TitleBar when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")
