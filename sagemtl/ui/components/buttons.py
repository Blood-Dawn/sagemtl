"""Button components for SageMTL UI.

This module provides styled button components including:
- IconButton for icon-only buttons
- PrimaryButton for primary actions
- SecondaryButton for secondary actions
"""

from __future__ import annotations

from typing import Optional

try:
    from PySide6.QtCore import Qt, QSize
    from PySide6.QtWidgets import QPushButton, QWidget
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from ..constants import Spacing, Typography
from ..theme import get_theme_manager


if HAS_PYSIDE6:
    class IconButton(QPushButton):
        """Icon-only button widget.

        Features:
        - Circular or square shape
        - Hover and active states
        - Tooltip support

        Usage:
            btn = IconButton(Icons.SETTINGS)
            btn.setToolTip("Settings")
            btn.clicked.connect(on_settings)
        """

        def __init__(
            self,
            icon: str,
            size: int = 32,
            circular: bool = False,
            parent: Optional[QWidget] = None,
        ):
            super().__init__(icon, parent)
            self._icon = icon
            self._size = size
            self._circular = circular
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._apply_theme()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        def _setup_ui(self) -> None:
            """Set up the button UI."""
            self.setFixedSize(self._size, self._size)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors
            radius = self._size // 2 if self._circular else Spacing.RADIUS_SM

            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {colors.text_secondary};
                    border: none;
                    border-radius: {radius}px;
                    font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets";
                    font-size: {self._size // 2}px;
                }}
                QPushButton:hover {{
                    background-color: {colors.surface_hover};
                    color: {colors.text_primary};
                }}
                QPushButton:pressed {{
                    background-color: {colors.surface_active};
                }}
                QPushButton:focus {{
                    outline: 2px solid {colors.accent};
                    outline-offset: 2px;
                }}
                QPushButton:disabled {{
                    color: {colors.text_disabled};
                }}
            """)


    class PrimaryButton(QPushButton):
        """Primary action button.

        Features:
        - Accent color background
        - Prominent styling
        - Loading state support

        Usage:
            btn = PrimaryButton("Save")
            btn.clicked.connect(on_save)
        """

        def __init__(
            self,
            text: str,
            icon: Optional[str] = None,
            parent: Optional[QWidget] = None,
        ):
            super().__init__(parent)
            self._text = text
            self._icon = icon
            self._loading = False
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._apply_theme()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        @property
        def loading(self) -> bool:
            """Check if button is in loading state."""
            return self._loading

        @loading.setter
        def loading(self, value: bool) -> None:
            """Set loading state."""
            self._loading = value
            self.setEnabled(not value)
            if value:
                self.setText("Loading...")
            else:
                self._update_text()

        def _setup_ui(self) -> None:
            """Set up the button UI."""
            self._update_text()
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            self.setMinimumHeight(36)

        def _update_text(self) -> None:
            """Update button text with icon if present."""
            if self._icon:
                self.setText(f"{self._icon}  {self._text}")
            else:
                self.setText(self._text)

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.button_primary_bg};
                    color: {colors.button_primary_text};
                    border: none;
                    border-radius: {Spacing.RADIUS_SM}px;
                    padding: {Spacing.BUTTON_PADDING_V}px {Spacing.BUTTON_PADDING_H}px;
                    font-size: {Typography.SIZE_MD}px;
                    font-weight: {Typography.WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {colors.accent_hover};
                }}
                QPushButton:pressed {{
                    background-color: {colors.accent_active};
                }}
                QPushButton:focus {{
                    outline: 2px solid {colors.accent};
                    outline-offset: 2px;
                }}
                QPushButton:disabled {{
                    background-color: {colors.background_secondary};
                    color: {colors.text_disabled};
                }}
            """)


    class SecondaryButton(QPushButton):
        """Secondary action button.

        Features:
        - Subtle background
        - Border styling
        - Used for less prominent actions

        Usage:
            btn = SecondaryButton("Cancel")
            btn.clicked.connect(on_cancel)
        """

        def __init__(
            self,
            text: str,
            icon: Optional[str] = None,
            parent: Optional[QWidget] = None,
        ):
            super().__init__(parent)
            self._text = text
            self._icon = icon
            self._theme_manager = get_theme_manager()

            self._setup_ui()
            self._apply_theme()
            self._theme_manager.add_listener(lambda _: self._apply_theme())

        def _setup_ui(self) -> None:
            """Set up the button UI."""
            self._update_text()
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            self.setMinimumHeight(36)

        def _update_text(self) -> None:
            """Update button text with icon if present."""
            if self._icon:
                self.setText(f"{self._icon}  {self._text}")
            else:
                self.setText(self._text)

        def _apply_theme(self) -> None:
            """Apply current theme colors."""
            colors = self._theme_manager.current_theme.colors

            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.button_secondary_bg};
                    color: {colors.button_secondary_text};
                    border: 1px solid {colors.border};
                    border-radius: {Spacing.RADIUS_SM}px;
                    padding: {Spacing.BUTTON_PADDING_V}px {Spacing.BUTTON_PADDING_H}px;
                    font-size: {Typography.SIZE_MD}px;
                    font-weight: {Typography.WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {colors.surface_hover};
                    border-color: {colors.border_strong};
                }}
                QPushButton:pressed {{
                    background-color: {colors.surface_active};
                }}
                QPushButton:focus {{
                    outline: 2px solid {colors.accent};
                    outline-offset: 2px;
                }}
                QPushButton:disabled {{
                    background-color: {colors.background_secondary};
                    color: {colors.text_disabled};
                    border-color: {colors.border_subtle};
                }}
            """)

else:
    class IconButton:
        """Stub IconButton when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")

    class PrimaryButton:
        """Stub PrimaryButton when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")

    class SecondaryButton:
        """Stub SecondaryButton when PySide6 is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PySide6 is required for the desktop UI")
