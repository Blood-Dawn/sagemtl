"""Theme management for SageMTL UI.

This module provides a complete theme system with:
- Light and dark themes
- System theme detection
- Theme persistence
- Dynamic theme switching
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ThemeMode(str, Enum):
    """Theme mode selection."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass
class ThemeColors:
    """Complete color palette for a theme.

    All colors are in hex format (#RRGGBB or #RRGGBBAA).
    """

    # Background colors
    background: str = "#FFFFFF"
    background_secondary: str = "#F5F5F5"
    background_tertiary: str = "#EBEBEB"
    surface: str = "#FFFFFF"
    surface_hover: str = "#F0F0F0"
    surface_active: str = "#E5E5E5"

    # Text colors
    text_primary: str = "#1A1A1A"
    text_secondary: str = "#666666"
    text_tertiary: str = "#999999"
    text_disabled: str = "#CCCCCC"
    text_inverse: str = "#FFFFFF"

    # Border colors
    border: str = "#E0E0E0"
    border_subtle: str = "#F0F0F0"
    border_strong: str = "#CCCCCC"

    # Accent colors (brand)
    accent: str = "#0078D4"
    accent_hover: str = "#106EBE"
    accent_active: str = "#005A9E"
    accent_subtle: str = "#E6F2FA"

    # Status colors
    success: str = "#107C10"
    success_subtle: str = "#DFF6DD"
    warning: str = "#FFB900"
    warning_subtle: str = "#FFF4CE"
    error: str = "#D13438"
    error_subtle: str = "#FDE7E9"
    info: str = "#0078D4"
    info_subtle: str = "#E6F2FA"

    # Interactive elements
    button_primary_bg: str = "#0078D4"
    button_primary_text: str = "#FFFFFF"
    button_secondary_bg: str = "#F3F3F3"
    button_secondary_text: str = "#1A1A1A"

    # Sidebar
    sidebar_bg: str = "#F5F5F5"
    sidebar_item_hover: str = "#E8E8E8"
    sidebar_item_active: str = "#E0E0E0"
    sidebar_text: str = "#1A1A1A"
    sidebar_icon: str = "#666666"

    # Title bar
    titlebar_bg: str = "#F5F5F5"
    titlebar_text: str = "#1A1A1A"
    titlebar_button_hover: str = "#E5E5E5"
    titlebar_button_close_hover: str = "#C42B1C"

    # Scrollbar
    scrollbar_track: str = "#F0F0F0"
    scrollbar_thumb: str = "#CCCCCC"
    scrollbar_thumb_hover: str = "#AAAAAA"

    # Shadow (RGBA format)
    shadow_sm: str = "rgba(0, 0, 0, 0.05)"
    shadow_md: str = "rgba(0, 0, 0, 0.10)"
    shadow_lg: str = "rgba(0, 0, 0, 0.15)"


@dataclass
class Theme:
    """Complete theme definition."""

    name: str
    mode: ThemeMode
    colors: ThemeColors
    description: str = ""
    is_builtin: bool = True

    def to_dict(self) -> dict:
        """Convert theme to dictionary for serialization."""
        return {
            "name": self.name,
            "mode": self.mode.value,
            "description": self.description,
            "colors": {
                k: v for k, v in self.colors.__dict__.items()
            },
            "is_builtin": self.is_builtin,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Theme":
        """Create theme from dictionary."""
        colors = ThemeColors(**data.get("colors", {}))
        return cls(
            name=data["name"],
            mode=ThemeMode(data.get("mode", "light")),
            colors=colors,
            description=data.get("description", ""),
            is_builtin=data.get("is_builtin", False),
        )


# Built-in Light Theme
LIGHT_THEME = Theme(
    name="Light",
    mode=ThemeMode.LIGHT,
    colors=ThemeColors(),
    description="Default light theme",
    is_builtin=True,
)

# Built-in Dark Theme
DARK_THEME = Theme(
    name="Dark",
    mode=ThemeMode.DARK,
    colors=ThemeColors(
        # Background colors
        background="#1F1F1F",
        background_secondary="#2D2D2D",
        background_tertiary="#3D3D3D",
        surface="#2D2D2D",
        surface_hover="#3D3D3D",
        surface_active="#4D4D4D",

        # Text colors
        text_primary="#FFFFFF",
        text_secondary="#B0B0B0",
        text_tertiary="#808080",
        text_disabled="#606060",
        text_inverse="#1A1A1A",

        # Border colors
        border="#404040",
        border_subtle="#333333",
        border_strong="#505050",

        # Accent colors
        accent="#4CC2FF",
        accent_hover="#60CDFF",
        accent_active="#3DB4F0",
        accent_subtle="#1A3A4D",

        # Status colors
        success="#6CCB5F",
        success_subtle="#1D3D1D",
        warning="#FCE100",
        warning_subtle="#4D4400",
        error="#FF6B6B",
        error_subtle="#4D1F1F",
        info="#4CC2FF",
        info_subtle="#1A3A4D",

        # Interactive elements
        button_primary_bg="#4CC2FF",
        button_primary_text="#1A1A1A",
        button_secondary_bg="#404040",
        button_secondary_text="#FFFFFF",

        # Sidebar
        sidebar_bg="#252525",
        sidebar_item_hover="#3D3D3D",
        sidebar_item_active="#4D4D4D",
        sidebar_text="#FFFFFF",
        sidebar_icon="#B0B0B0",

        # Title bar
        titlebar_bg="#1F1F1F",
        titlebar_text="#FFFFFF",
        titlebar_button_hover="#3D3D3D",
        titlebar_button_close_hover="#C42B1C",

        # Scrollbar
        scrollbar_track="#2D2D2D",
        scrollbar_thumb="#505050",
        scrollbar_thumb_hover="#606060",

        # Shadow
        shadow_sm="rgba(0, 0, 0, 0.20)",
        shadow_md="rgba(0, 0, 0, 0.30)",
        shadow_lg="rgba(0, 0, 0, 0.40)",
    ),
    description="Default dark theme",
    is_builtin=True,
)


class ThemeManager:
    """Manages theme loading, switching, and persistence.

    Usage:
        manager = ThemeManager()
        manager.set_theme_mode(ThemeMode.DARK)
        current = manager.current_theme

        # Listen for changes
        manager.add_listener(lambda theme: print(f"Theme changed to {theme.name}"))
    """

    _instance: Optional["ThemeManager"] = None

    def __new__(cls) -> "ThemeManager":
        """Singleton pattern for theme manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._themes: Dict[str, Theme] = {
            "light": LIGHT_THEME,
            "dark": DARK_THEME,
        }
        self._current_mode: ThemeMode = ThemeMode.SYSTEM
        self._current_theme: Theme = LIGHT_THEME
        self._listeners: List[Callable[[Theme], None]] = []
        self._config_path: Optional[Path] = None
        self._initialized = True

    @property
    def current_theme(self) -> Theme:
        """Get the currently active theme."""
        return self._current_theme

    @property
    def current_mode(self) -> ThemeMode:
        """Get the current theme mode setting."""
        return self._current_mode

    @property
    def available_themes(self) -> List[str]:
        """Get list of available theme names."""
        return list(self._themes.keys())

    def set_config_path(self, path: Path) -> None:
        """Set the path for theme configuration persistence."""
        self._config_path = path

    def set_theme_mode(self, mode: ThemeMode) -> None:
        """Set the theme mode and update current theme."""
        self._current_mode = mode

        if mode == ThemeMode.SYSTEM:
            # Detect system theme
            is_dark = self._detect_system_dark_mode()
            self._current_theme = self._themes["dark"] if is_dark else self._themes["light"]
        elif mode == ThemeMode.DARK:
            self._current_theme = self._themes["dark"]
        else:
            self._current_theme = self._themes["light"]

        self._notify_listeners()
        self._save_preference()

    def set_theme(self, name: str) -> bool:
        """Set a specific theme by name."""
        if name not in self._themes:
            logger.warning(f"Theme '{name}' not found")
            return False

        self._current_theme = self._themes[name]
        self._current_mode = self._current_theme.mode
        self._notify_listeners()
        self._save_preference()
        return True

    def register_theme(self, theme: Theme) -> None:
        """Register a custom theme."""
        self._themes[theme.name.lower()] = theme

    def add_listener(self, callback: Callable[[Theme], None]) -> None:
        """Add a listener for theme changes."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[Theme], None]) -> None:
        """Remove a theme change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """Notify all listeners of theme change."""
        for listener in self._listeners:
            try:
                listener(self._current_theme)
            except Exception as e:
                logger.error(f"Error in theme listener: {e}")

    def _detect_system_dark_mode(self) -> bool:
        """Detect if the system is using dark mode."""
        if sys.platform == "win32":
            return self._detect_windows_dark_mode()
        elif sys.platform == "darwin":
            return self._detect_macos_dark_mode()
        else:
            return self._detect_linux_dark_mode()

    def _detect_windows_dark_mode(self) -> bool:
        """Detect Windows dark mode via registry."""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0
        except Exception:
            return False

    def _detect_macos_dark_mode(self) -> bool:
        """Detect macOS dark mode via defaults command."""
        try:
            import subprocess
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip().lower() == "dark"
        except Exception:
            return False

    def _detect_linux_dark_mode(self) -> bool:
        """Detect Linux dark mode via gsettings or environment."""
        try:
            import subprocess
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True,
                text=True
            )
            return "dark" in result.stdout.lower()
        except Exception:
            # Check XDG_CURRENT_DESKTOP environment
            import os
            desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            # Default to light if we can't detect
            return False

    def _save_preference(self) -> None:
        """Save theme preference to config file."""
        if not self._config_path:
            return

        try:
            config = {
                "theme_mode": self._current_mode.value,
                "theme_name": self._current_theme.name.lower(),
            }
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save theme preference: {e}")

    def load_preference(self) -> None:
        """Load theme preference from config file."""
        if not self._config_path or not self._config_path.exists():
            return

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            mode = ThemeMode(config.get("theme_mode", "system"))
            self.set_theme_mode(mode)
        except Exception as e:
            logger.error(f"Failed to load theme preference: {e}")

    def generate_stylesheet(self) -> str:
        """Generate Qt stylesheet from current theme."""
        colors = self._current_theme.colors
        return f"""
            /* Main Window */
            QMainWindow {{
                background-color: {colors.background};
            }}

            QWidget {{
                background-color: transparent;
                color: {colors.text_primary};
                font-family: "Segoe UI", "SF Pro Display", system-ui, sans-serif;
                font-size: 14px;
            }}

            /* Labels */
            QLabel {{
                color: {colors.text_primary};
                background-color: transparent;
            }}

            QLabel[class="secondary"] {{
                color: {colors.text_secondary};
            }}

            QLabel[class="caption"] {{
                font-size: 12px;
                color: {colors.text_secondary};
            }}

            /* Buttons */
            QPushButton {{
                background-color: {colors.button_secondary_bg};
                color: {colors.button_secondary_text};
                border: 1px solid {colors.border};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
            }}

            QPushButton:hover {{
                background-color: {colors.surface_hover};
            }}

            QPushButton:pressed {{
                background-color: {colors.surface_active};
            }}

            QPushButton:disabled {{
                background-color: {colors.background_secondary};
                color: {colors.text_disabled};
            }}

            QPushButton[class="primary"] {{
                background-color: {colors.button_primary_bg};
                color: {colors.button_primary_text};
                border: none;
            }}

            QPushButton[class="primary"]:hover {{
                background-color: {colors.accent_hover};
            }}

            QPushButton[class="primary"]:pressed {{
                background-color: {colors.accent_active};
            }}

            /* Line Edit / Text Input */
            QLineEdit {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                border-radius: 4px;
                padding: 8px 12px;
            }}

            QLineEdit:focus {{
                border-color: {colors.accent};
            }}

            QLineEdit:disabled {{
                background-color: {colors.background_secondary};
                color: {colors.text_disabled};
            }}

            /* Text Edit / Multiline */
            QTextEdit, QPlainTextEdit {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                border-radius: 4px;
                padding: 8px;
            }}

            QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {colors.accent};
            }}

            /* Combo Box */
            QComboBox {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                border-radius: 4px;
                padding: 8px 12px;
                padding-right: 30px;
            }}

            QComboBox:hover {{
                background-color: {colors.surface_hover};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}

            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}

            QComboBox QAbstractItemView {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                selection-background-color: {colors.accent_subtle};
            }}

            /* List Widget */
            QListWidget {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                border-radius: 4px;
            }}

            QListWidget::item {{
                padding: 8px 12px;
            }}

            QListWidget::item:hover {{
                background-color: {colors.surface_hover};
            }}

            QListWidget::item:selected {{
                background-color: {colors.accent_subtle};
                color: {colors.text_primary};
            }}

            /* Table Widget */
            QTableWidget, QTableView {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                gridline-color: {colors.border_subtle};
            }}

            QTableWidget::item, QTableView::item {{
                padding: 8px;
            }}

            QTableWidget::item:selected, QTableView::item:selected {{
                background-color: {colors.accent_subtle};
            }}

            QHeaderView::section {{
                background-color: {colors.background_secondary};
                color: {colors.text_primary};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {colors.border};
            }}

            /* Scroll Bars */
            QScrollBar:vertical {{
                background-color: {colors.scrollbar_track};
                width: 12px;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical {{
                background-color: {colors.scrollbar_thumb};
                border-radius: 6px;
                min-height: 30px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: {colors.scrollbar_thumb_hover};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar:horizontal {{
                background-color: {colors.scrollbar_track};
                height: 12px;
                border-radius: 6px;
            }}

            QScrollBar::handle:horizontal {{
                background-color: {colors.scrollbar_thumb};
                border-radius: 6px;
                min-width: 30px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background-color: {colors.scrollbar_thumb_hover};
            }}

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}

            /* Tab Widget */
            QTabWidget::pane {{
                background-color: {colors.surface};
                border: 1px solid {colors.border};
                border-radius: 4px;
            }}

            QTabBar::tab {{
                background-color: transparent;
                color: {colors.text_secondary};
                padding: 8px 16px;
                border-bottom: 2px solid transparent;
            }}

            QTabBar::tab:hover {{
                color: {colors.text_primary};
            }}

            QTabBar::tab:selected {{
                color: {colors.accent};
                border-bottom-color: {colors.accent};
            }}

            /* Progress Bar */
            QProgressBar {{
                background-color: {colors.background_secondary};
                border: none;
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }}

            QProgressBar::chunk {{
                background-color: {colors.accent};
                border-radius: 4px;
            }}

            /* Splitter */
            QSplitter::handle {{
                background-color: {colors.border};
            }}

            QSplitter::handle:horizontal {{
                width: 2px;
            }}

            QSplitter::handle:vertical {{
                height: 2px;
            }}

            /* Menu */
            QMenu {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                border-radius: 8px;
                padding: 4px;
            }}

            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
            }}

            QMenu::item:selected {{
                background-color: {colors.surface_hover};
            }}

            QMenu::separator {{
                height: 1px;
                background-color: {colors.border};
                margin: 4px 8px;
            }}

            /* Tool Tip */
            QToolTip {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                border-radius: 4px;
                padding: 4px 8px;
            }}

            /* Status Bar */
            QStatusBar {{
                background-color: {colors.background_secondary};
                color: {colors.text_secondary};
            }}

            /* Group Box */
            QGroupBox {{
                font-weight: 600;
                border: 1px solid {colors.border};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 4px;
                color: {colors.text_primary};
            }}

            /* Check Box */
            QCheckBox {{
                spacing: 8px;
            }}

            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {colors.border};
                border-radius: 4px;
            }}

            QCheckBox::indicator:checked {{
                background-color: {colors.accent};
                border-color: {colors.accent};
            }}

            /* Radio Button */
            QRadioButton {{
                spacing: 8px;
            }}

            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {colors.border};
                border-radius: 9px;
            }}

            QRadioButton::indicator:checked {{
                background-color: {colors.accent};
                border-color: {colors.accent};
            }}

            /* Spin Box */
            QSpinBox, QDoubleSpinBox {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                border-radius: 4px;
                padding: 8px;
            }}

            QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {colors.accent};
            }}
        """


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return ThemeManager()
