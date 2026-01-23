"""Toast notification system for SageMTL.

This module provides a toast notification system with:
- Multiple notification types (success, error, warning, info)
- Auto-dismiss with configurable duration
- Stacking notifications
- Animation effects
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time

try:
    from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
    from PySide6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QGraphicsOpacityEffect,
    )
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from ..constants import Spacing, Icons, Typography
from ..theme import get_theme_manager


class ToastType(str, Enum):
    """Type of toast notification."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Toast:
    """Toast notification data."""

    message: str
    type: ToastType = ToastType.INFO
    duration: int = 4000  # ms
    title: Optional[str] = None
    dismissible: bool = True
    id: str = field(default_factory=lambda: str(time.time()))


if HAS_PYSIDE6:
    class ToastWidget(QWidget):
        """Individual toast notification widget."""

        def __init__(
            self,
            toast: Toast,
            on_dismiss: Optional[callable] = None,
            parent: Optional[QWidget] = None,
        ):
            super().__init__(parent)
            self._toast = toast
            self._on_dismiss = on_dismiss
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._apply_theme()

            # Auto-dismiss timer
            if toast.duration > 0:
                QTimer.singleShot(toast.duration, self._dismiss)

        def _setup_ui(self) -> None:
            """Set up the toast UI."""
            self.setFixedWidth(360)
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowStaysOnTopHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            # Opacity effect for fade animation
            self._opacity = QGraphicsOpacityEffect(self)
            self._opacity.setOpacity(1.0)
            self.setGraphicsEffect(self._opacity)

            layout = QHBoxLayout(self)
            layout.setContentsMargins(
                Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD
            )
            layout.setSpacing(Spacing.SM)

            # Icon
            icon = self._get_icon()
            icon_label = QLabel(icon)
            icon_label.setFixedSize(24, 24)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon_label)

            # Content
            content_layout = QVBoxLayout()
            content_layout.setSpacing(Spacing.XS)

            if self._toast.title:
                title_label = QLabel(self._toast.title)
                title_label.setStyleSheet(f"""
                    font-weight: {Typography.WEIGHT_SEMIBOLD};
                    font-size: {Typography.SIZE_MD}px;
                """)
                content_layout.addWidget(title_label)

            message_label = QLabel(self._toast.message)
            message_label.setWordWrap(True)
            message_label.setStyleSheet(f"""
                font-size: {Typography.SIZE_SM}px;
            """)
            content_layout.addWidget(message_label)

            layout.addLayout(content_layout, 1)

            # Close button
            if self._toast.dismissible:
                close_btn = QPushButton(Icons.CLOSE.value)
                close_btn.setFixedSize(24, 24)
                close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                close_btn.clicked.connect(self._dismiss)
                layout.addWidget(close_btn)

        def _get_icon(self) -> str:
            """Get the icon for the toast type."""
            icons = {
                ToastType.SUCCESS: Icons.SUCCESS.value,
                ToastType.ERROR: Icons.ERROR.value,
                ToastType.WARNING: Icons.WARNING.value,
                ToastType.INFO: Icons.INFO.value,
            }
            return icons.get(self._toast.type, Icons.INFO.value)

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            type_colors = {
                ToastType.SUCCESS: (colors.success, colors.success_subtle),
                ToastType.ERROR: (colors.error, colors.error_subtle),
                ToastType.WARNING: (colors.warning, colors.warning_subtle),
                ToastType.INFO: (colors.info, colors.info_subtle),
            }

            accent, bg = type_colors.get(
                self._toast.type,
                (colors.info, colors.info_subtle)
            )

            self.setStyleSheet(f"""
                ToastWidget {{
                    background-color: {colors.surface};
                    border: 1px solid {colors.border};
                    border-left: 4px solid {accent};
                    border-radius: {Spacing.RADIUS_MD}px;
                }}

                QLabel {{
                    color: {colors.text_primary};
                    background-color: transparent;
                }}

                QPushButton {{
                    background-color: transparent;
                    color: {colors.text_secondary};
                    border: none;
                    border-radius: {Spacing.RADIUS_SM}px;
                    font-family: "Segoe Fluent Icons";
                }}

                QPushButton:hover {{
                    background-color: {colors.surface_hover};
                }}
            """)

        def _dismiss(self) -> None:
            """Dismiss the toast with fade animation."""
            anim = QPropertyAnimation(self._opacity, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(self._on_fade_complete)
            anim.start()
            self._anim = anim  # Keep reference

        def _on_fade_complete(self) -> None:
            """Handle fade animation complete."""
            if self._on_dismiss:
                self._on_dismiss(self._toast.id)
            self.deleteLater()

        def show_animated(self) -> None:
            """Show the toast with slide-in animation."""
            self.show()

            # Slide in from right
            start_pos = self.pos() + QPoint(50, 0)
            end_pos = self.pos()

            self.move(start_pos)
            self._opacity.setOpacity(0.0)

            # Position animation
            pos_anim = QPropertyAnimation(self, b"pos")
            pos_anim.setDuration(300)
            pos_anim.setStartValue(start_pos)
            pos_anim.setEndValue(end_pos)
            pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            pos_anim.start()
            self._pos_anim = pos_anim

            # Opacity animation
            opacity_anim = QPropertyAnimation(self._opacity, b"opacity")
            opacity_anim.setDuration(300)
            opacity_anim.setStartValue(0.0)
            opacity_anim.setEndValue(1.0)
            opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            opacity_anim.start()
            self._opacity_anim = opacity_anim


    class ToastManager:
        """Manages toast notifications.

        Usage:
            manager = ToastManager(parent_widget)
            manager.show_success("Operation completed!")
            manager.show_error("An error occurred", title="Error")
        """

        _instance: Optional["ToastManager"] = None

        def __init__(self, parent: QWidget):
            self._parent = parent
            self._toasts: List[ToastWidget] = []
            self._max_visible = 5
            self._spacing = Spacing.SM
            self._margin = Spacing.MD

        @classmethod
        def instance(cls, parent: Optional[QWidget] = None) -> "ToastManager":
            """Get or create the singleton instance."""
            if cls._instance is None:
                if parent is None:
                    raise ValueError("Parent required for first initialization")
                cls._instance = cls(parent)
            return cls._instance

        def show(self, toast: Toast) -> None:
            """Show a toast notification."""
            if len(self._toasts) >= self._max_visible:
                # Remove oldest toast
                oldest = self._toasts.pop(0)
                oldest.deleteLater()

            widget = ToastWidget(toast, self._on_dismiss, self._parent)
            self._toasts.append(widget)
            self._position_toasts()
            widget.show_animated()

        def show_success(
            self,
            message: str,
            title: Optional[str] = None,
            duration: int = 4000,
        ) -> None:
            """Show a success toast."""
            self.show(Toast(
                message=message,
                type=ToastType.SUCCESS,
                title=title,
                duration=duration,
            ))

        def show_error(
            self,
            message: str,
            title: Optional[str] = None,
            duration: int = 6000,
        ) -> None:
            """Show an error toast."""
            self.show(Toast(
                message=message,
                type=ToastType.ERROR,
                title=title,
                duration=duration,
            ))

        def show_warning(
            self,
            message: str,
            title: Optional[str] = None,
            duration: int = 5000,
        ) -> None:
            """Show a warning toast."""
            self.show(Toast(
                message=message,
                type=ToastType.WARNING,
                title=title,
                duration=duration,
            ))

        def show_info(
            self,
            message: str,
            title: Optional[str] = None,
            duration: int = 4000,
        ) -> None:
            """Show an info toast."""
            self.show(Toast(
                message=message,
                type=ToastType.INFO,
                title=title,
                duration=duration,
            ))

        def _on_dismiss(self, toast_id: str) -> None:
            """Handle toast dismiss."""
            self._toasts = [t for t in self._toasts if t._toast.id != toast_id]
            self._position_toasts()

        def _position_toasts(self) -> None:
            """Position all visible toasts."""
            parent_rect = self._parent.rect()

            y = self._margin
            for widget in self._toasts:
                x = parent_rect.width() - widget.width() - self._margin
                widget.move(x, y)
                y += widget.height() + self._spacing

        def clear_all(self) -> None:
            """Clear all visible toasts."""
            for toast in self._toasts:
                toast.deleteLater()
            self._toasts.clear()

else:
    class ToastManager:
        """Stub ToastManager when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")
