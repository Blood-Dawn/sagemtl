"""Card components for SageMTL UI.

This module provides card components including:
- Generic Card container
- NovelCard for displaying novel information
"""

from __future__ import annotations

from typing import Optional

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QPixmap, QPainter, QPainterPath
    from PySide6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QSizePolicy,
        QGraphicsDropShadowEffect,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from ..constants import Spacing, Typography
from ..theme import get_theme_manager


if HAS_PYSIDE6:
    class Card(QWidget):
        """Generic card container widget.

        Features:
        - Rounded corners
        - Shadow effect
        - Hover state
        - Clickable

        Usage:
            card = Card()
            card.set_content(my_widget)
        """

        clicked = Signal()

        def __init__(
            self,
            parent: Optional[QWidget] = None,
            clickable: bool = False,
        ):
            super().__init__(parent)
            self._clickable = clickable
            self._theme_manager = get_theme_manager()
            self._content: Optional[QWidget] = None

            self._setup_ui()
            self._apply_theme()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        def set_content(self, widget: QWidget) -> None:
            """Set the card content."""
            if self._content:
                self._layout.removeWidget(self._content)
                self._content.deleteLater()

            self._content = widget
            self._layout.addWidget(widget)

        def _setup_ui(self) -> None:
            """Set up the card UI."""
            self._layout = QVBoxLayout(self)
            self._layout.setContentsMargins(
                Spacing.CARD_PADDING,
                Spacing.CARD_PADDING,
                Spacing.CARD_PADDING,
                Spacing.CARD_PADDING,
            )
            self._layout.setSpacing(0)

            # Shadow effect
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(16)
            shadow.setXOffset(0)
            shadow.setYOffset(4)
            self.setGraphicsEffect(shadow)

            if self._clickable:
                self.setCursor(Qt.CursorShape.PointingHandCursor)

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            # Update shadow color
            shadow = self.graphicsEffect()
            if shadow:
                from PySide6.QtGui import QColor
                shadow.setColor(QColor(0, 0, 0, 30))

            hover_style = f"""
                Card:hover {{
                    background-color: {colors.surface_hover};
                    border-color: {colors.border_strong};
                }}
            """ if self._clickable else ""

            self.setStyleSheet(f"""
                Card {{
                    background-color: {colors.surface};
                    border: 1px solid {colors.border};
                    border-radius: {Spacing.RADIUS_MD}px;
                }}
                {hover_style}
            """)

        def mousePressEvent(self, event) -> None:
            """Handle mouse press."""
            if self._clickable and event.button() == Qt.MouseButton.LeftButton:
                self.clicked.emit()
            super().mousePressEvent(event)


    class NovelCard(QWidget):
        """Card widget for displaying novel information.

        Features:
        - Cover image with rounded corners
        - Title and author
        - Chapter count and status
        - Progress indicator

        Usage:
            card = NovelCard(
                title="My Novel",
                author="Author Name",
                cover_path="/path/to/cover.jpg",
                chapters=100,
                read_chapters=50,
            )
        """

        clicked = Signal()

        def __init__(
            self,
            title: str,
            author: str = "",
            cover_path: Optional[str] = None,
            chapters: int = 0,
            read_chapters: int = 0,
            status: str = "",
            parent: Optional[QWidget] = None,
        ):
            super().__init__(parent)
            self._title = title
            self._author = author
            self._cover_path = cover_path
            self._chapters = chapters
            self._read_chapters = read_chapters
            self._status = status
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._apply_theme()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        def _setup_ui(self) -> None:
            """Set up the card UI."""
            self.setFixedSize(180, 280)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
            layout.setSpacing(Spacing.SM)

            # Cover image
            self._cover_label = QLabel()
            self._cover_label.setFixedSize(164, 200)
            self._cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._cover_label.setScaledContents(True)
            self._set_cover()
            layout.addWidget(self._cover_label)

            # Title
            self._title_label = QLabel(self._title)
            self._title_label.setWordWrap(True)
            self._title_label.setMaximumHeight(40)
            self._title_label.setStyleSheet(f"""
                font-weight: {Typography.WEIGHT_SEMIBOLD};
                font-size: {Typography.SIZE_SM}px;
            """)
            layout.addWidget(self._title_label)

            # Author/status
            if self._author or self._status:
                info_text = self._author or self._status
                self._info_label = QLabel(info_text)
                self._info_label.setStyleSheet(f"""
                    font-size: {Typography.SIZE_XS}px;
                """)
                layout.addWidget(self._info_label)

            # Shadow effect
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(12)
            shadow.setXOffset(0)
            shadow.setYOffset(2)
            self.setGraphicsEffect(shadow)

        def _set_cover(self) -> None:
            """Set the cover image."""
            if self._cover_path:
                pixmap = QPixmap(self._cover_path)
                if not pixmap.isNull():
                    # Round corners
                    rounded = self._round_pixmap(pixmap, Spacing.RADIUS_SM)
                    self._cover_label.setPixmap(rounded)
                    return

            # Placeholder
            self._cover_label.setText(self._title[:2].upper())
            self._cover_label.setStyleSheet(f"""
                background-color: #3498db;
                color: white;
                font-size: 48px;
                font-weight: bold;
                border-radius: {Spacing.RADIUS_SM}px;
            """)

        def _round_pixmap(self, pixmap: QPixmap, radius: int) -> QPixmap:
            """Create a pixmap with rounded corners."""
            target = QPixmap(pixmap.size())
            target.fill(Qt.GlobalColor.transparent)

            painter = QPainter(target)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            path = QPainterPath()
            path.addRoundedRect(
                0, 0,
                pixmap.width(), pixmap.height(),
                radius, radius
            )

            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            return target

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            # Update shadow color
            shadow = self.graphicsEffect()
            if shadow:
                from PySide6.QtGui import QColor
                shadow.setColor(QColor(0, 0, 0, 25))

            self.setStyleSheet(f"""
                NovelCard {{
                    background-color: {colors.surface};
                    border: 1px solid {colors.border};
                    border-radius: {Spacing.RADIUS_MD}px;
                }}
                NovelCard:hover {{
                    background-color: {colors.surface_hover};
                    border-color: {colors.accent};
                }}
                QLabel {{
                    color: {colors.text_primary};
                    background-color: transparent;
                }}
            """)

            # Update info label color if exists
            if hasattr(self, '_info_label'):
                self._info_label.setStyleSheet(f"""
                    font-size: {Typography.SIZE_XS}px;
                    color: {colors.text_secondary};
                """)

        def mousePressEvent(self, event) -> None:
            """Handle mouse press."""
            if event.button() == Qt.MouseButton.LeftButton:
                self.clicked.emit()
            super().mousePressEvent(event)

else:
    class Card:
        """Stub Card when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")

    class NovelCard:
        """Stub NovelCard when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")
