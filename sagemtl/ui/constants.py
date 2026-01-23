"""Design system constants for SageMTL UI.

This module defines the design tokens for spacing, typography, and icons
used throughout the application UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Spacing:
    """Spacing scale constants (in pixels)."""

    # Base spacing unit
    UNIT = 4

    # Named spacing values
    NONE = 0
    XS = UNIT  # 4px
    SM = UNIT * 2  # 8px
    MD = UNIT * 4  # 16px
    LG = UNIT * 6  # 24px
    XL = UNIT * 8  # 32px
    XXL = UNIT * 12  # 48px

    # Component-specific spacing
    PANEL_PADDING = MD
    CARD_PADDING = MD
    BUTTON_PADDING_H = MD
    BUTTON_PADDING_V = SM
    INPUT_PADDING = SM

    # Layout spacing
    SIDEBAR_WIDTH = 240
    SIDEBAR_COLLAPSED_WIDTH = 64
    TITLE_BAR_HEIGHT = 40
    STATUS_BAR_HEIGHT = 24

    # Border radius
    RADIUS_SM = 4
    RADIUS_MD = 8
    RADIUS_LG = 12
    RADIUS_FULL = 9999


class Typography:
    """Typography scale and font families."""

    # Font families
    FONT_FAMILY = "Segoe UI Variable, Segoe UI, SF Pro Display, -apple-system, system-ui, sans-serif"
    FONT_FAMILY_MONO = "Cascadia Code, Consolas, Monaco, monospace"

    # Font sizes (in pixels)
    SIZE_XS = 10
    SIZE_SM = 12
    SIZE_MD = 14
    SIZE_LG = 16
    SIZE_XL = 20
    SIZE_XXL = 24
    SIZE_DISPLAY = 32

    # Font weights
    WEIGHT_LIGHT = 300
    WEIGHT_REGULAR = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700

    # Line heights
    LINE_HEIGHT_TIGHT = 1.2
    LINE_HEIGHT_NORMAL = 1.5
    LINE_HEIGHT_RELAXED = 1.75

    # Named text styles
    @staticmethod
    def display_style() -> dict:
        """Display heading style."""
        return {
            "font_size": Typography.SIZE_DISPLAY,
            "font_weight": Typography.WEIGHT_BOLD,
            "line_height": Typography.LINE_HEIGHT_TIGHT,
        }

    @staticmethod
    def heading_style() -> dict:
        """Section heading style."""
        return {
            "font_size": Typography.SIZE_XL,
            "font_weight": Typography.WEIGHT_SEMIBOLD,
            "line_height": Typography.LINE_HEIGHT_TIGHT,
        }

    @staticmethod
    def body_style() -> dict:
        """Body text style."""
        return {
            "font_size": Typography.SIZE_MD,
            "font_weight": Typography.WEIGHT_REGULAR,
            "line_height": Typography.LINE_HEIGHT_NORMAL,
        }

    @staticmethod
    def caption_style() -> dict:
        """Caption/small text style."""
        return {
            "font_size": Typography.SIZE_SM,
            "font_weight": Typography.WEIGHT_REGULAR,
            "line_height": Typography.LINE_HEIGHT_NORMAL,
        }


class Icons(str, Enum):
    """Icon constants using Segoe Fluent Icons (Windows) or SF Symbols (macOS).

    These are Unicode code points for Segoe Fluent Icons on Windows.
    Fallback to emoji or custom SVG icons on other platforms.
    """

    # Navigation
    HOME = "\uE80F"
    LIBRARY = "\uE8F1"
    DOWNLOAD = "\uE896"
    TRANSLATE = "\uE8D4"
    GLOSSARY = "\uE82D"
    SETTINGS = "\uE713"

    # Actions
    ADD = "\uE710"
    DELETE = "\uE74D"
    EDIT = "\uE70F"
    SAVE = "\uE74E"
    REFRESH = "\uE72C"
    SEARCH = "\uE721"
    FILTER = "\uE71C"
    SORT = "\uE8CB"

    # File operations
    FOLDER = "\uE8B7"
    FOLDER_OPEN = "\uE838"
    FILE = "\uE7C3"
    FILE_NEW = "\uE8A5"
    EXPORT = "\uE8B6"
    IMPORT = "\uE8B5"

    # Media
    PLAY = "\uE768"
    PAUSE = "\uE769"
    STOP = "\uE71A"

    # UI
    EXPAND = "\uE70D"
    COLLAPSE = "\uE70E"
    CHEVRON_LEFT = "\uE76B"
    CHEVRON_RIGHT = "\uE76C"
    CHEVRON_UP = "\uE70E"
    CHEVRON_DOWN = "\uE70D"
    CLOSE = "\uE8BB"
    MINIMIZE = "\uE921"
    MAXIMIZE = "\uE922"
    RESTORE = "\uE923"

    # Status
    SUCCESS = "\uE73E"
    ERROR = "\uE783"
    WARNING = "\uE7BA"
    INFO = "\uE946"
    LOADING = "\uE712"

    # Theme
    SUN = "\uE706"
    MOON = "\uE708"
    SYSTEM = "\uE770"

    # Novel/reading
    BOOK = "\uE82D"
    BOOK_OPEN = "\uE736"
    CHAPTER = "\uE8A4"

    def __str__(self) -> str:
        return self.value


@dataclass
class IconSet:
    """Platform-specific icon set configuration."""

    use_fluent: bool = True
    use_emoji_fallback: bool = False
    custom_icon_path: str = ""

    def get_icon(self, icon: Icons) -> str:
        """Get the appropriate icon representation for the current platform."""
        if self.use_fluent:
            return icon.value
        elif self.use_emoji_fallback:
            return _EMOJI_FALLBACK.get(icon, "?")
        else:
            return icon.name.lower()


# Emoji fallback mapping for non-Windows platforms
_EMOJI_FALLBACK: dict[Icons, str] = {
    Icons.HOME: "\U0001F3E0",
    Icons.LIBRARY: "\U0001F4DA",
    Icons.DOWNLOAD: "\u2B07\uFE0F",
    Icons.TRANSLATE: "\U0001F310",
    Icons.GLOSSARY: "\U0001F4D6",
    Icons.SETTINGS: "\u2699\uFE0F",
    Icons.ADD: "\u2795",
    Icons.DELETE: "\U0001F5D1\uFE0F",
    Icons.EDIT: "\u270F\uFE0F",
    Icons.SAVE: "\U0001F4BE",
    Icons.REFRESH: "\U0001F504",
    Icons.SEARCH: "\U0001F50D",
    Icons.FOLDER: "\U0001F4C1",
    Icons.FILE: "\U0001F4C4",
    Icons.PLAY: "\u25B6\uFE0F",
    Icons.PAUSE: "\u23F8\uFE0F",
    Icons.STOP: "\u23F9\uFE0F",
    Icons.CLOSE: "\u274C",
    Icons.SUCCESS: "\u2705",
    Icons.ERROR: "\u274C",
    Icons.WARNING: "\u26A0\uFE0F",
    Icons.INFO: "\u2139\uFE0F",
    Icons.SUN: "\u2600\uFE0F",
    Icons.MOON: "\U0001F319",
    Icons.BOOK: "\U0001F4D5",
}
