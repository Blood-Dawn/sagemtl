# UI Modernization Specification

## Overview

The UI modernization transforms SageMTL into a contemporary desktop application with support for light/dark themes, a custom title bar, Fluent Design-inspired aesthetics, and a flexible layout with dockable panels.

---

## Design System

### Color Palette

```python
# Location: sagemtl_desktop/ui/theme/colors.py

from dataclasses import dataclass

@dataclass
class ColorPalette:
    """Color palette for theming."""

    # Primary colors
    primary: str
    primary_hover: str
    primary_pressed: str

    # Background colors
    background: str
    background_secondary: str
    background_tertiary: str

    # Surface colors (cards, panels)
    surface: str
    surface_hover: str
    surface_border: str

    # Text colors
    text_primary: str
    text_secondary: str
    text_disabled: str

    # Accent colors
    accent: str
    accent_hover: str

    # Status colors
    success: str
    warning: str
    error: str
    info: str

    # Glassmorphism
    glass_background: str
    glass_border: str


LIGHT_THEME = ColorPalette(
    # Primary (Blue)
    primary="#0078D4",
    primary_hover="#106EBE",
    primary_pressed="#005A9E",

    # Background
    background="#F3F3F3",
    background_secondary="#FFFFFF",
    background_tertiary="#E5E5E5",

    # Surface
    surface="#FFFFFF",
    surface_hover="#F5F5F5",
    surface_border="#E0E0E0",

    # Text
    text_primary="#1A1A1A",
    text_secondary="#666666",
    text_disabled="#A0A0A0",

    # Accent
    accent="#0078D4",
    accent_hover="#106EBE",

    # Status
    success="#107C10",
    warning="#FFB900",
    error="#D13438",
    info="#0078D4",

    # Glass
    glass_background="rgba(255, 255, 255, 0.7)",
    glass_border="rgba(255, 255, 255, 0.3)",
)

DARK_THEME = ColorPalette(
    # Primary (Blue)
    primary="#60CDFF",
    primary_hover="#7ED7FF",
    primary_pressed="#4CC2FF",

    # Background
    background="#202020",
    background_secondary="#2D2D2D",
    background_tertiary="#383838",

    # Surface
    surface="#2D2D2D",
    surface_hover="#383838",
    surface_border="#404040",

    # Text
    text_primary="#FFFFFF",
    text_secondary="#B0B0B0",
    text_disabled="#606060",

    # Accent
    accent="#60CDFF",
    accent_hover="#7ED7FF",

    # Status
    success="#6CCB5F",
    warning="#FCE100",
    error="#FF6B6B",
    info="#60CDFF",

    # Glass
    glass_background="rgba(45, 45, 45, 0.7)",
    glass_border="rgba(255, 255, 255, 0.1)",
)
```

### Typography

```python
# Location: sagemtl_desktop/ui/theme/typography.py

from dataclasses import dataclass

@dataclass
class Typography:
    """Typography settings."""
    family: str
    size_display: int      # Large headers
    size_title: int        # Page titles
    size_subtitle: int     # Section headers
    size_body: int         # Body text
    size_caption: int      # Small text
    size_button: int       # Button text

    weight_normal: int
    weight_medium: int
    weight_bold: int


DEFAULT_TYPOGRAPHY = Typography(
    family="Segoe UI, SF Pro Display, -apple-system, sans-serif",
    size_display=32,
    size_title=24,
    size_subtitle=18,
    size_body=14,
    size_caption=12,
    size_button=14,

    weight_normal=400,
    weight_medium=500,
    weight_bold=600,
)
```

### Spacing & Sizing

```python
# Location: sagemtl_desktop/ui/theme/spacing.py

from dataclasses import dataclass

@dataclass
class Spacing:
    """Spacing constants."""
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48


@dataclass
class Sizing:
    """Size constants."""
    sidebar_width: int = 64           # Collapsed sidebar
    sidebar_width_expanded: int = 280  # Expanded sidebar
    title_bar_height: int = 32
    panel_min_width: int = 200
    panel_min_height: int = 150
    button_height: int = 32
    button_height_large: int = 40
    input_height: int = 32
    icon_size: int = 20
    icon_size_large: int = 24


SPACING = Spacing()
SIZING = Sizing()
```

---

## Component Architecture

### Theme Engine

```python
# Location: sagemtl_desktop/ui/theme_engine.py

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPalette, QColor
from enum import Enum
from typing import Optional
import platform

class ThemeMode(Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ThemeEngine(QObject):
    """Manages application theming."""

    theme_changed = Signal(str)  # Emits 'light' or 'dark'

    _instance: Optional['ThemeEngine'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        super().__init__()
        self._initialized = True
        self._mode = ThemeMode.SYSTEM
        self._effective_theme = 'light'

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    @mode.setter
    def mode(self, value: ThemeMode):
        self._mode = value
        self._apply_theme()

    @property
    def effective_theme(self) -> str:
        """Get the actual theme being used ('light' or 'dark')."""
        return self._effective_theme

    @property
    def colors(self) -> ColorPalette:
        """Get current color palette."""
        return DARK_THEME if self._effective_theme == 'dark' else LIGHT_THEME

    def _detect_system_theme(self) -> str:
        """Detect system theme preference."""
        if platform.system() == 'Windows':
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return 'light' if value else 'dark'
            except:
                pass
        elif platform.system() == 'Darwin':  # macOS
            try:
                import subprocess
                result = subprocess.run(
                    ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                    capture_output=True, text=True
                )
                return 'dark' if 'Dark' in result.stdout else 'light'
            except:
                pass
        return 'light'

    def _apply_theme(self):
        """Apply the current theme."""
        if self._mode == ThemeMode.SYSTEM:
            theme = self._detect_system_theme()
        else:
            theme = self._mode.value

        if theme != self._effective_theme:
            self._effective_theme = theme
            self._apply_stylesheet()
            self.theme_changed.emit(theme)

    def _apply_stylesheet(self):
        """Apply QSS stylesheet."""
        app = QApplication.instance()
        if app:
            stylesheet = self._generate_stylesheet()
            app.setStyleSheet(stylesheet)

    def _generate_stylesheet(self) -> str:
        """Generate QSS stylesheet from current theme."""
        c = self.colors
        return f"""
            /* Global */
            QWidget {{
                font-family: {DEFAULT_TYPOGRAPHY.family};
                font-size: {DEFAULT_TYPOGRAPHY.size_body}px;
                color: {c.text_primary};
                background-color: {c.background};
            }}

            /* Main Window */
            QMainWindow {{
                background-color: {c.background};
            }}

            /* Buttons */
            QPushButton {{
                background-color: {c.surface};
                border: 1px solid {c.surface_border};
                border-radius: 4px;
                padding: 6px 16px;
                min-height: {SIZING.button_height}px;
            }}

            QPushButton:hover {{
                background-color: {c.surface_hover};
            }}

            QPushButton:pressed {{
                background-color: {c.primary_pressed};
            }}

            QPushButton[primary="true"] {{
                background-color: {c.primary};
                color: white;
                border: none;
            }}

            QPushButton[primary="true"]:hover {{
                background-color: {c.primary_hover};
            }}

            /* Line Edits */
            QLineEdit {{
                background-color: {c.surface};
                border: 1px solid {c.surface_border};
                border-radius: 4px;
                padding: 6px 12px;
                min-height: {SIZING.input_height}px;
            }}

            QLineEdit:focus {{
                border-color: {c.primary};
            }}

            /* Text Edits */
            QTextEdit, QPlainTextEdit {{
                background-color: {c.surface};
                border: 1px solid {c.surface_border};
                border-radius: 4px;
                padding: 8px;
            }}

            /* Lists */
            QListWidget, QListView {{
                background-color: {c.surface};
                border: 1px solid {c.surface_border};
                border-radius: 4px;
            }}

            QListWidget::item, QListView::item {{
                padding: 8px 12px;
                border-radius: 4px;
            }}

            QListWidget::item:hover, QListView::item:hover {{
                background-color: {c.surface_hover};
            }}

            QListWidget::item:selected, QListView::item:selected {{
                background-color: {c.primary};
                color: white;
            }}

            /* Scroll Bars */
            QScrollBar:vertical {{
                background-color: transparent;
                width: 12px;
                margin: 0;
            }}

            QScrollBar::handle:vertical {{
                background-color: {c.text_disabled};
                border-radius: 6px;
                min-height: 30px;
                margin: 2px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: {c.text_secondary};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}

            /* Tab Widget */
            QTabWidget::pane {{
                border: 1px solid {c.surface_border};
                border-radius: 4px;
                background-color: {c.surface};
            }}

            QTabBar::tab {{
                background-color: {c.background};
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}

            QTabBar::tab:selected {{
                background-color: {c.surface};
            }}

            QTabBar::tab:hover {{
                background-color: {c.surface_hover};
            }}

            /* Menu */
            QMenu {{
                background-color: {c.surface};
                border: 1px solid {c.surface_border};
                border-radius: 8px;
                padding: 4px;
            }}

            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
            }}

            QMenu::item:selected {{
                background-color: {c.surface_hover};
            }}

            /* Progress Bar */
            QProgressBar {{
                background-color: {c.background_tertiary};
                border-radius: 4px;
                text-align: center;
                min-height: 8px;
            }}

            QProgressBar::chunk {{
                background-color: {c.primary};
                border-radius: 4px;
            }}

            /* Group Box */
            QGroupBox {{
                border: 1px solid {c.surface_border};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
        """


# Global instance
theme_engine = ThemeEngine()
```

### Custom Title Bar

```python
# Location: sagemtl_desktop/ui/title_bar.py

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QMouseEvent, QIcon
import platform


class WindowButton(QPushButton):
    """Custom window control button."""

    def __init__(self, icon_char: str, hover_color: str = None, parent=None):
        super().__init__(parent)
        self.setText(icon_char)
        self.setFixedSize(46, 32)
        self.setCursor(Qt.ArrowCursor)
        self._hover_color = hover_color

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-family: "Segoe MDL2 Assets", "SF Pro Display";
                font-size: 10px;
                color: {theme_engine.colors.text_primary};
            }}
            QPushButton:hover {{
                background-color: {hover_color or theme_engine.colors.surface_hover};
            }}
        """)


class TitleBar(QWidget):
    """Custom window title bar with dragging support."""

    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._is_dragging = False
        self._drag_start_pos = QPoint()

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(0)

        # App icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        layout.addWidget(self.icon_label)

        layout.addSpacing(8)

        # Title
        self.title_label = QLabel("SageMTL")
        self.title_label.setStyleSheet(f"""
            font-size: 12px;
            color: {theme_engine.colors.text_primary};
        """)
        layout.addWidget(self.title_label)

        # Spacer
        layout.addStretch()

        # Window buttons
        if platform.system() == 'Windows':
            # Windows style: minimize, maximize, close
            self.btn_minimize = WindowButton("─", parent=self)
            self.btn_maximize = WindowButton("□", parent=self)
            self.btn_close = WindowButton("✕", "#E81123", parent=self)

            self.btn_minimize.clicked.connect(self.minimize_clicked.emit)
            self.btn_maximize.clicked.connect(self.maximize_clicked.emit)
            self.btn_close.clicked.connect(self.close_clicked.emit)

            layout.addWidget(self.btn_minimize)
            layout.addWidget(self.btn_maximize)
            layout.addWidget(self.btn_close)
        else:
            # macOS style: handled by system
            pass

    def set_title(self, title: str):
        self.title_label.setText(title)

    def set_maximized(self, maximized: bool):
        """Update maximize button icon."""
        if hasattr(self, 'btn_maximize'):
            self.btn_maximize.setText("❐" if maximized else "□")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.globalPos() - self.window().pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPos() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.maximize_clicked.emit()
```

### Sidebar Navigation

```python
# Location: sagemtl_desktop/ui/sidebar.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class NavItem:
    """Navigation item definition."""
    id: str
    icon: str  # Icon path or character
    label: str
    tooltip: str = ""


class NavButton(QPushButton):
    """Navigation button with icon and optional label."""

    def __init__(self, item: NavItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(item.tooltip or item.label)

        self._expanded = False
        self._update_style()

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self._update_style()

    def _update_style(self):
        c = theme_engine.colors
        icon_html = f'<span style="font-size: 20px;">{self.item.icon}</span>'

        if self._expanded:
            self.setText(f"{self.item.icon}  {self.item.label}")
            min_width = 200
        else:
            self.setText(self.item.icon)
            min_width = 48

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 12px;
                text-align: left;
                min-height: 40px;
                min-width: {min_width}px;
                font-size: 14px;
                color: {c.text_primary};
            }}
            QPushButton:hover {{
                background-color: {c.surface_hover};
            }}
            QPushButton:checked {{
                background-color: {c.primary};
                color: white;
            }}
        """)


class Sidebar(QWidget):
    """Collapsible sidebar navigation."""

    navigation_changed = Signal(str)  # Emits nav item id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._current_item: Optional[str] = None
        self._nav_buttons: List[NavButton] = []

        self.setFixedWidth(SIZING.sidebar_width)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Toggle button
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.clicked.connect(self.toggle_expanded)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 20px;
                color: {theme_engine.colors.text_primary};
            }}
            QPushButton:hover {{
                background-color: {theme_engine.colors.surface_hover};
            }}
        """)
        layout.addWidget(self.toggle_btn)

        layout.addSpacing(8)

        # Navigation items container
        self.nav_layout = QVBoxLayout()
        self.nav_layout.setSpacing(2)
        layout.addLayout(self.nav_layout)

        layout.addStretch()

        # Bottom items (Settings, etc.)
        self.bottom_layout = QVBoxLayout()
        self.bottom_layout.setSpacing(2)
        layout.addLayout(self.bottom_layout)

    def add_nav_item(self, item: NavItem, is_bottom: bool = False):
        """Add a navigation item."""
        button = NavButton(item)
        button.clicked.connect(lambda: self._on_nav_clicked(item.id))

        self._nav_buttons.append(button)

        if is_bottom:
            self.bottom_layout.addWidget(button)
        else:
            self.nav_layout.addWidget(button)

    def set_current_item(self, item_id: str):
        """Set the current active navigation item."""
        self._current_item = item_id
        for btn in self._nav_buttons:
            btn.setChecked(btn.item.id == item_id)

    def toggle_expanded(self):
        """Toggle sidebar expansion."""
        self._expanded = not self._expanded

        target_width = SIZING.sidebar_width_expanded if self._expanded else SIZING.sidebar_width

        # Animate width change
        anim = QPropertyAnimation(self, b"minimumWidth")
        anim.setDuration(200)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setEndValue(target_width)
        anim.start()

        anim2 = QPropertyAnimation(self, b"maximumWidth")
        anim2.setDuration(200)
        anim2.setEasingCurve(QEasingCurve.OutCubic)
        anim2.setEndValue(target_width)
        anim2.start()

        # Update button labels
        for btn in self._nav_buttons:
            btn.set_expanded(self._expanded)

    def _on_nav_clicked(self, item_id: str):
        """Handle navigation item click."""
        self.set_current_item(item_id)
        self.navigation_changed.emit(item_id)


# Default navigation items
DEFAULT_NAV_ITEMS = [
    NavItem("library", "📚", "Library", "View your novel library"),
    NavItem("download", "⬇️", "Download", "Download novels from web"),
    NavItem("translate", "🔤", "Translate", "Translate novels"),
    NavItem("glossary", "📖", "Glossary", "Manage translation glossaries"),
]

BOTTOM_NAV_ITEMS = [
    NavItem("settings", "⚙️", "Settings", "Application settings"),
]
```

---

## Main Views

### View Base Class

```python
# Location: sagemtl_desktop/ui/views/base_view.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Signal


class BaseView(QWidget):
    """Base class for all main views."""

    # Common signals
    status_message = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_base_layout()

    def _setup_base_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

    def add_header(self, title: str, subtitle: str = None):
        """Add a header section."""
        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 16)
        header_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: {DEFAULT_TYPOGRAPHY.size_title}px;
            font-weight: {DEFAULT_TYPOGRAPHY.weight_bold};
            color: {theme_engine.colors.text_primary};
        """)
        header_layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet(f"""
                font-size: {DEFAULT_TYPOGRAPHY.size_body}px;
                color: {theme_engine.colors.text_secondary};
            """)
            header_layout.addWidget(subtitle_label)

        self.main_layout.addWidget(header)

    def show_loading(self, message: str = "Loading..."):
        """Show loading indicator."""
        pass  # Implement loading overlay

    def hide_loading(self):
        """Hide loading indicator."""
        pass

    def on_activated(self):
        """Called when view becomes active."""
        pass

    def on_deactivated(self):
        """Called when view becomes inactive."""
        pass
```

### Library View

```python
# Location: sagemtl_desktop/ui/views/library_view.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea,
    QFrame, QMenu, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class NovelItem:
    """Novel display item."""
    id: int
    title: str
    author: Optional[str]
    cover_path: Optional[str]
    chapter_count: int
    translated_count: int
    status: str  # downloading, translating, completed


class NovelCard(QFrame):
    """Card widget for displaying a novel."""

    clicked = Signal(int)  # Novel ID
    context_menu_requested = Signal(int)

    def __init__(self, novel: NovelItem, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedSize(180, 280)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_engine.colors.surface};
                border: 1px solid {theme_engine.colors.surface_border};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {theme_engine.colors.primary};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 12)
        layout.setSpacing(8)

        # Cover image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(164, 200)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("""
            background-color: #E0E0E0;
            border-radius: 4px;
        """)

        if self.novel.cover_path:
            pixmap = QPixmap(self.novel.cover_path)
            self.cover_label.setPixmap(
                pixmap.scaled(164, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self.cover_label.setText("📖")
            self.cover_label.setStyleSheet("""
                background-color: #E0E0E0;
                border-radius: 4px;
                font-size: 48px;
            """)

        layout.addWidget(self.cover_label)

        # Title
        self.title_label = QLabel(self.novel.title)
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(40)
        self.title_label.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 500;
            color: {theme_engine.colors.text_primary};
        """)
        layout.addWidget(self.title_label)

        # Progress
        progress = (self.novel.translated_count / self.novel.chapter_count * 100
                   if self.novel.chapter_count > 0 else 0)
        self.progress_label = QLabel(f"{int(progress)}% translated")
        self.progress_label.setStyleSheet(f"""
            font-size: 11px;
            color: {theme_engine.colors.text_secondary};
        """)
        layout.addWidget(self.progress_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.novel.id)
        elif event.button() == Qt.RightButton:
            self.context_menu_requested.emit(self.novel.id)

    def contextMenuEvent(self, event):
        self.context_menu_requested.emit(self.novel.id)


class LibraryView(BaseView):
    """Library view showing all novels."""

    novel_selected = Signal(int)
    novel_delete_requested = Signal(int)
    novel_export_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._novels: List[NovelItem] = []
        self._setup_ui()

    def _setup_ui(self):
        self.add_header("Library", "Your downloaded and translated novels")

        # Toolbar
        toolbar = QHBoxLayout()

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search novels...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)

        toolbar.addStretch()

        # View toggle
        self.view_combo = QComboBox()
        self.view_combo.addItems(["Grid", "List"])
        self.view_combo.currentTextChanged.connect(self._on_view_changed)
        toolbar.addWidget(self.view_combo)

        # Sort
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Recently Added", "Title", "Author", "Progress"])
        toolbar.addWidget(self.sort_combo)

        self.main_layout.addLayout(toolbar)

        # Novel grid (in scroll area)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll_area.setWidget(self.grid_widget)
        self.main_layout.addWidget(scroll_area)

    def set_novels(self, novels: List[NovelItem]):
        """Set the list of novels to display."""
        self._novels = novels
        self._refresh_grid()

    def _refresh_grid(self):
        """Refresh the novel grid."""
        # Clear existing
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add novel cards
        cols = max(1, (self.width() - 48) // 196)  # 180 + 16 spacing
        for i, novel in enumerate(self._novels):
            card = NovelCard(novel)
            card.clicked.connect(self.novel_selected.emit)
            card.context_menu_requested.connect(self._show_context_menu)
            self.grid_layout.addWidget(card, i // cols, i % cols)

    def _on_search(self, text: str):
        """Filter novels by search text."""
        # Implement filtering
        pass

    def _on_view_changed(self, view_type: str):
        """Switch between grid and list view."""
        # Implement view switching
        pass

    def _show_context_menu(self, novel_id: int):
        """Show context menu for a novel."""
        menu = QMenu(self)
        menu.addAction("Open", lambda: self.novel_selected.emit(novel_id))
        menu.addAction("Export...", lambda: self.novel_export_requested.emit(novel_id))
        menu.addSeparator()
        menu.addAction("Delete", lambda: self.novel_delete_requested.emit(novel_id))
        menu.exec_(QCursor.pos())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_grid()
```

### Download View

```python
# Location: sagemtl_desktop/ui/views/download_view.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QProgressBar, QFrame, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from typing import List
from dataclasses import dataclass


@dataclass
class DownloadJob:
    """Download job representation."""
    id: str
    url: str
    title: str
    status: str  # pending, downloading, completed, failed
    progress: float
    chapters_done: int
    chapters_total: int
    error_message: Optional[str] = None


class DownloadJobItem(QFrame):
    """Widget for displaying a download job."""

    cancel_requested = Signal(str)
    retry_requested = Signal(str)

    def __init__(self, job: DownloadJob, parent=None):
        super().__init__(parent)
        self.job = job
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_engine.colors.surface};
                border: 1px solid {theme_engine.colors.surface_border};
                border-radius: 8px;
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        self.title_label = QLabel(self.job.title or self.job.url)
        self.title_label.setStyleSheet(f"""
            font-weight: 500;
            color: {theme_engine.colors.text_primary};
        """)
        header.addWidget(self.title_label)

        header.addStretch()

        self.status_label = QLabel(self.job.status.title())
        status_color = {
            'pending': theme_engine.colors.text_secondary,
            'downloading': theme_engine.colors.info,
            'completed': theme_engine.colors.success,
            'failed': theme_engine.colors.error,
        }.get(self.job.status, theme_engine.colors.text_secondary)
        self.status_label.setStyleSheet(f"color: {status_color};")
        header.addWidget(self.status_label)

        layout.addLayout(header)

        # Progress
        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(int(self.job.progress))
        progress_row.addWidget(self.progress_bar)

        self.progress_label = QLabel(
            f"{self.job.chapters_done}/{self.job.chapters_total} chapters"
        )
        self.progress_label.setStyleSheet(f"""
            font-size: 12px;
            color: {theme_engine.colors.text_secondary};
            min-width: 100px;
        """)
        progress_row.addWidget(self.progress_label)

        layout.addLayout(progress_row)

        # Error message
        if self.job.error_message:
            error_label = QLabel(self.job.error_message)
            error_label.setStyleSheet(f"""
                font-size: 12px;
                color: {theme_engine.colors.error};
            """)
            layout.addWidget(error_label)

    def update_job(self, job: DownloadJob):
        """Update with new job data."""
        self.job = job
        self.progress_bar.setValue(int(job.progress))
        self.progress_label.setText(f"{job.chapters_done}/{job.chapters_total} chapters")
        self.status_label.setText(job.status.title())


class DownloadView(BaseView):
    """View for downloading novels from web."""

    download_requested = Signal(str, dict)  # URL, options
    search_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._jobs: List[DownloadJob] = []
        self._setup_ui()

    def _setup_ui(self):
        self.add_header("Download", "Download novels from supported websites")

        # URL input section
        url_section = QFrame()
        url_section.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_engine.colors.surface};
                border: 1px solid {theme_engine.colors.surface_border};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        url_layout = QVBoxLayout(url_section)

        # URL row
        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter novel URL (e.g., https://fanmtl.com/novel/...)")
        self.url_input.returnPressed.connect(self._on_download)
        url_row.addWidget(self.url_input)

        self.download_btn = QPushButton("Download")
        self.download_btn.setProperty("primary", True)
        self.download_btn.clicked.connect(self._on_download)
        url_row.addWidget(self.download_btn)

        url_layout.addLayout(url_row)

        # Options row
        options_row = QHBoxLayout()

        self.crawler_combo = QComboBox()
        self.crawler_combo.addItems(["Auto-detect", "SageCrawler", "LightNovel-Crawler"])
        options_row.addWidget(QLabel("Crawler:"))
        options_row.addWidget(self.crawler_combo)

        options_row.addStretch()

        self.translate_checkbox = QCheckBox("Translate after download")
        self.translate_checkbox.setChecked(True)
        options_row.addWidget(self.translate_checkbox)

        url_layout.addLayout(options_row)

        self.main_layout.addWidget(url_section)

        # Jobs section
        jobs_header = QHBoxLayout()
        jobs_header.addWidget(QLabel("Download Queue"))
        jobs_header.addStretch()
        self.clear_btn = QPushButton("Clear Completed")
        self.clear_btn.clicked.connect(self._clear_completed)
        jobs_header.addWidget(self.clear_btn)
        self.main_layout.addLayout(jobs_header)

        # Jobs list
        self.jobs_list = QVBoxLayout()
        self.jobs_list.setSpacing(8)
        self.main_layout.addLayout(self.jobs_list)
        self.main_layout.addStretch()

    def _on_download(self):
        """Start download."""
        url = self.url_input.text().strip()
        if not url:
            return

        options = {
            'crawler': self.crawler_combo.currentText(),
            'translate': self.translate_checkbox.isChecked(),
        }

        self.download_requested.emit(url, options)
        self.url_input.clear()

    def add_job(self, job: DownloadJob):
        """Add a new download job."""
        self._jobs.append(job)
        item = DownloadJobItem(job)
        self.jobs_list.insertWidget(0, item)

    def update_job(self, job: DownloadJob):
        """Update an existing job."""
        for i, j in enumerate(self._jobs):
            if j.id == job.id:
                self._jobs[i] = job
                # Update widget
                widget = self.jobs_list.itemAt(i).widget()
                if isinstance(widget, DownloadJobItem):
                    widget.update_job(job)
                break

    def _clear_completed(self):
        """Remove completed jobs from list."""
        pass  # Implement
```

### Translation View

```python
# Location: sagemtl_desktop/ui/views/translation_view.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QLabel, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, Signal


class TranslationView(BaseView):
    """View for translating novels with side-by-side comparison."""

    translate_requested = Signal(int, str, str)  # novel_id, source_lang, target_lang

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.add_header("Translate", "Machine translate your novels")

        # Top controls
        controls = QHBoxLayout()

        # Novel selector
        controls.addWidget(QLabel("Novel:"))
        self.novel_combo = QComboBox()
        self.novel_combo.setMinimumWidth(300)
        controls.addWidget(self.novel_combo)

        controls.addStretch()

        # Language settings
        controls.addWidget(QLabel("From:"))
        self.source_lang = QComboBox()
        self.source_lang.addItems(["Chinese (zh)", "Japanese (ja)", "Korean (ko)"])
        controls.addWidget(self.source_lang)

        controls.addWidget(QLabel("To:"))
        self.target_lang = QComboBox()
        self.target_lang.addItems(["English (en)"])
        controls.addWidget(self.target_lang)

        # Provider
        controls.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Argos (Offline)", "Google", "DeepL"])
        controls.addWidget(self.provider_combo)

        self.main_layout.addLayout(controls)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        # Splitter with chapter list and text comparison
        splitter = QSplitter(Qt.Horizontal)

        # Chapter list
        chapter_frame = QFrame()
        chapter_layout = QVBoxLayout(chapter_frame)
        chapter_layout.setContentsMargins(0, 0, 0, 0)

        chapter_header = QHBoxLayout()
        chapter_header.addWidget(QLabel("Chapters"))
        chapter_header.addStretch()
        self.select_all_btn = QPushButton("Select All")
        chapter_header.addWidget(self.select_all_btn)
        chapter_layout.addLayout(chapter_header)

        self.chapter_list = QListWidget()
        self.chapter_list.setSelectionMode(QListWidget.ExtendedSelection)
        chapter_layout.addWidget(self.chapter_list)

        splitter.addWidget(chapter_frame)

        # Text comparison
        text_frame = QFrame()
        text_layout = QVBoxLayout(text_frame)
        text_layout.setContentsMargins(0, 0, 0, 0)

        text_splitter = QSplitter(Qt.Horizontal)

        # Source text
        source_frame = QFrame()
        source_layout = QVBoxLayout(source_frame)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.addWidget(QLabel("Original"))
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        source_layout.addWidget(self.source_text)
        text_splitter.addWidget(source_frame)

        # Translated text
        target_frame = QFrame()
        target_layout = QVBoxLayout(target_frame)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.addWidget(QLabel("Translated"))
        self.target_text = QTextEdit()
        self.target_text.setReadOnly(True)
        target_layout.addWidget(self.target_text)
        text_splitter.addWidget(target_frame)

        text_layout.addWidget(text_splitter)
        splitter.addWidget(text_frame)

        splitter.setSizes([250, 750])
        self.main_layout.addWidget(splitter)

        # Bottom controls
        bottom = QHBoxLayout()
        bottom.addStretch()

        self.glossary_btn = QPushButton("Edit Glossary")
        bottom.addWidget(self.glossary_btn)

        self.translate_btn = QPushButton("Translate Selected")
        self.translate_btn.setProperty("primary", True)
        bottom.addWidget(self.translate_btn)

        self.main_layout.addLayout(bottom)
```

### Glossary View

```python
# Location: sagemtl_desktop/ui/views/glossary_view.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QLineEdit,
    QComboBox, QLabel, QMenu, QDialog, QFormLayout,
    QDialogButtonBox, QTextEdit
)
from PySide6.QtCore import Qt, Signal


class GlossaryEntryDialog(QDialog):
    """Dialog for adding/editing glossary entries."""

    def __init__(self, entry=None, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setWindowTitle("Edit Glossary Entry" if entry else "Add Glossary Entry")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        self.source_input = QLineEdit()
        if self.entry:
            self.source_input.setText(self.entry.source_term)
        layout.addRow("Source Term:", self.source_input)

        self.target_input = QLineEdit()
        if self.entry:
            self.target_input.setText(self.entry.target_term)
        layout.addRow("Translation:", self.target_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "character", "item", "location", "technique", "title", "other"
        ])
        if self.entry and self.entry.term_type:
            self.type_combo.setCurrentText(self.entry.term_type)
        layout.addRow("Type:", self.type_combo)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        if self.entry and self.entry.notes:
            self.notes_input.setText(self.entry.notes)
        layout.addRow("Notes:", self.notes_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_entry(self) -> GlossaryEntry:
        return GlossaryEntry(
            source_term=self.source_input.text(),
            target_term=self.target_input.text(),
            term_type=self.type_combo.currentText(),
            notes=self.notes_input.toPlainText() or None,
        )


class GlossaryView(BaseView):
    """View for managing translation glossaries."""

    entry_added = Signal(int, GlossaryEntry)  # novel_id, entry
    entry_updated = Signal(int, GlossaryEntry)
    entry_deleted = Signal(int, int)  # novel_id, entry_id
    import_requested = Signal(int, str)  # novel_id, file_path
    export_requested = Signal(int, str)  # novel_id, file_path
    auto_generate_requested = Signal(int)  # novel_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_novel_id = None
        self._setup_ui()

    def _setup_ui(self):
        self.add_header("Glossary", "Manage translation terminology for consistent results")

        # Top controls
        controls = QHBoxLayout()

        # Novel selector
        controls.addWidget(QLabel("Novel:"))
        self.novel_combo = QComboBox()
        self.novel_combo.setMinimumWidth(300)
        self.novel_combo.currentIndexChanged.connect(self._on_novel_changed)
        controls.addWidget(self.novel_combo)

        controls.addStretch()

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search terms...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self._on_search)
        controls.addWidget(self.search_input)

        # Filter by type
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "character", "item", "location", "technique"])
        self.type_filter.currentTextChanged.connect(self._on_filter)
        controls.addWidget(self.type_filter)

        self.main_layout.addLayout(controls)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Source", "Translation", "Type", "Notes", "Confidence"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_edit)

        self.main_layout.addWidget(self.table)

        # Bottom buttons
        bottom = QHBoxLayout()

        self.import_btn = QPushButton("Import CSV")
        self.import_btn.clicked.connect(self._on_import)
        bottom.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.clicked.connect(self._on_export)
        bottom.addWidget(self.export_btn)

        self.auto_btn = QPushButton("Auto-Generate")
        self.auto_btn.clicked.connect(self._on_auto_generate)
        bottom.addWidget(self.auto_btn)

        bottom.addStretch()

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self._on_delete)
        bottom.addWidget(self.delete_btn)

        self.add_btn = QPushButton("Add Entry")
        self.add_btn.setProperty("primary", True)
        self.add_btn.clicked.connect(self._on_add)
        bottom.addWidget(self.add_btn)

        self.main_layout.addLayout(bottom)

    def set_entries(self, entries: List[GlossaryEntry]):
        """Set the glossary entries to display."""
        self.table.setRowCount(len(entries))
        for i, entry in enumerate(entries):
            self.table.setItem(i, 0, QTableWidgetItem(entry.source_term))
            self.table.setItem(i, 1, QTableWidgetItem(entry.target_term))
            self.table.setItem(i, 2, QTableWidgetItem(entry.term_type or ""))
            self.table.setItem(i, 3, QTableWidgetItem(entry.notes or ""))
            self.table.setItem(i, 4, QTableWidgetItem(f"{entry.confidence:.0%}"))

            # Store entry ID in first column
            self.table.item(i, 0).setData(Qt.UserRole, entry.id)

    def _on_novel_changed(self, index):
        novel_id = self.novel_combo.currentData()
        self._current_novel_id = novel_id
        # Emit signal to load glossary
        pass

    def _on_search(self, text):
        """Filter table by search text."""
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def _on_filter(self, filter_type):
        """Filter by term type."""
        if filter_type == "All Types":
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, False)
        else:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 2)
                hidden = item is None or item.text() != filter_type
                self.table.setRowHidden(row, hidden)

    def _on_add(self):
        """Add new entry."""
        dialog = GlossaryEntryDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            entry = dialog.get_entry()
            self.entry_added.emit(self._current_novel_id, entry)

    def _on_edit(self):
        """Edit selected entry."""
        row = self.table.currentRow()
        if row < 0:
            return

        # Create entry from current row
        entry = GlossaryEntry(
            id=self.table.item(row, 0).data(Qt.UserRole),
            source_term=self.table.item(row, 0).text(),
            target_term=self.table.item(row, 1).text(),
            term_type=self.table.item(row, 2).text() or None,
            notes=self.table.item(row, 3).text() or None,
        )

        dialog = GlossaryEntryDialog(entry, parent=self)
        if dialog.exec() == QDialog.Accepted:
            updated = dialog.get_entry()
            updated.id = entry.id
            self.entry_updated.emit(self._current_novel_id, updated)

    def _on_delete(self):
        """Delete selected entries."""
        rows = set(index.row() for index in self.table.selectedIndexes())
        for row in rows:
            entry_id = self.table.item(row, 0).data(Qt.UserRole)
            self.entry_deleted.emit(self._current_novel_id, entry_id)

    def _on_import(self):
        """Import from file."""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Glossary", "", "CSV Files (*.csv);;JSON Files (*.json)"
        )
        if path:
            self.import_requested.emit(self._current_novel_id, path)

    def _on_export(self):
        """Export to file."""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Glossary", "glossary.csv", "CSV Files (*.csv);;JSON Files (*.json)"
        )
        if path:
            self.export_requested.emit(self._current_novel_id, path)

    def _on_auto_generate(self):
        """Auto-generate glossary entries."""
        self.auto_generate_requested.emit(self._current_novel_id)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("Edit", self._on_edit)
        menu.addAction("Delete", self._on_delete)
        menu.exec_(self.table.mapToGlobal(pos))
```

### Settings View

```python
# Location: sagemtl_desktop/ui/views/settings_view.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QPushButton, QLineEdit,
    QCheckBox, QSpinBox, QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Signal


class SettingsView(BaseView):
    """Application settings view."""

    settings_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.add_header("Settings", "Configure application preferences")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(24)

        # Appearance
        appearance = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        appearance_layout.addRow("Theme:", self.theme_combo)

        layout.addWidget(appearance)

        # Translation
        translation = QGroupBox("Translation")
        translation_layout = QFormLayout(translation)

        self.default_provider = QComboBox()
        self.default_provider.addItems(["Argos (Offline)", "Google Cloud", "DeepL", "Azure"])
        translation_layout.addRow("Default Provider:", self.default_provider)

        self.source_lang = QComboBox()
        self.source_lang.addItems(["Chinese (zh)", "Japanese (ja)", "Korean (ko)"])
        translation_layout.addRow("Source Language:", self.source_lang)

        self.target_lang = QComboBox()
        self.target_lang.addItems(["English (en)"])
        translation_layout.addRow("Target Language:", self.target_lang)

        self.chunk_size = QSpinBox()
        self.chunk_size.setRange(1000, 10000)
        self.chunk_size.setValue(4000)
        self.chunk_size.setSuffix(" characters")
        translation_layout.addRow("Chunk Size:", self.chunk_size)

        layout.addWidget(translation)

        # API Keys
        api_keys = QGroupBox("API Keys")
        api_layout = QFormLayout(api_keys)

        self.google_key = QLineEdit()
        self.google_key.setPlaceholderText("Enter Google Cloud API key")
        self.google_key.setEchoMode(QLineEdit.Password)
        api_layout.addRow("Google API Key:", self.google_key)

        self.deepl_key = QLineEdit()
        self.deepl_key.setPlaceholderText("Enter DeepL API key")
        self.deepl_key.setEchoMode(QLineEdit.Password)
        api_layout.addRow("DeepL API Key:", self.deepl_key)

        self.azure_key = QLineEdit()
        self.azure_key.setPlaceholderText("Enter Azure Translator key")
        self.azure_key.setEchoMode(QLineEdit.Password)
        api_layout.addRow("Azure API Key:", self.azure_key)

        layout.addWidget(api_keys)

        # Crawler
        crawler = QGroupBox("Crawler")
        crawler_layout = QFormLayout(crawler)

        self.default_crawler = QComboBox()
        self.default_crawler.addItems(["Auto-detect", "SageCrawler", "LightNovel-Crawler"])
        crawler_layout.addRow("Default Crawler:", self.default_crawler)

        self.request_delay = QSpinBox()
        self.request_delay.setRange(0, 5000)
        self.request_delay.setValue(500)
        self.request_delay.setSuffix(" ms")
        crawler_layout.addRow("Request Delay:", self.request_delay)

        self.max_concurrent = QSpinBox()
        self.max_concurrent.setRange(1, 20)
        self.max_concurrent.setValue(5)
        crawler_layout.addRow("Max Concurrent:", self.max_concurrent)

        layout.addWidget(crawler)

        # Output
        output = QGroupBox("Output")
        output_layout = QFormLayout(output)

        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("~/Documents/lightnovels")
        output_layout.addRow("Output Directory:", self.output_dir)

        self.default_formats = QHBoxLayout()
        for fmt in ["EPUB", "PDF", "TXT", "DOCX", "MOBI"]:
            cb = QCheckBox(fmt)
            cb.setChecked(fmt in ["EPUB", "PDF", "TXT"])
            self.default_formats.addWidget(cb)
        output_layout.addRow("Default Formats:", self.default_formats)

        layout.addWidget(output)

        layout.addStretch()
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

        # Save button
        bottom = QHBoxLayout()
        bottom.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setProperty("primary", True)
        self.save_btn.clicked.connect(self._on_save)
        bottom.addWidget(self.save_btn)
        self.main_layout.addLayout(bottom)

    def _on_theme_changed(self, theme: str):
        mode = {
            "System": ThemeMode.SYSTEM,
            "Light": ThemeMode.LIGHT,
            "Dark": ThemeMode.DARK,
        }.get(theme, ThemeMode.SYSTEM)
        theme_engine.mode = mode

    def _on_save(self):
        """Save all settings."""
        settings = {
            'theme': self.theme_combo.currentText().lower(),
            'translation': {
                'provider': self.default_provider.currentText(),
                'source_lang': self.source_lang.currentText().split('(')[1].strip(')'),
                'target_lang': self.target_lang.currentText().split('(')[1].strip(')'),
                'chunk_size': self.chunk_size.value(),
            },
            'api_keys': {
                'google': self.google_key.text(),
                'deepl': self.deepl_key.text(),
                'azure': self.azure_key.text(),
            },
            'crawler': {
                'default': self.default_crawler.currentText(),
                'request_delay': self.request_delay.value(),
                'max_concurrent': self.max_concurrent.value(),
            },
            'output': {
                'directory': self.output_dir.text(),
            },
        }
        self.settings_changed.emit(settings)
```

---

## Main Window Integration

```python
# Location: sagemtl_desktop/ui/main_window.py

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
import platform


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SageMTL")
        self.setMinimumSize(1200, 800)

        # Remove native title bar on Windows
        if platform.system() == 'Windows':
            self.setWindowFlags(Qt.FramelessWindowHint)

        self._setup_ui()
        self._setup_tray()
        self._connect_signals()

    def _setup_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom title bar
        self.title_bar = TitleBar(self)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.title_bar.maximize_clicked.connect(self._toggle_maximize)
        self.title_bar.close_clicked.connect(self.close)
        main_layout.addWidget(self.title_bar)

        # Content area
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.navigation_changed.connect(self._on_nav_changed)

        # Add navigation items
        for item in DEFAULT_NAV_ITEMS:
            self.sidebar.add_nav_item(item)
        for item in BOTTOM_NAV_ITEMS:
            self.sidebar.add_nav_item(item, is_bottom=True)

        content_layout.addWidget(self.sidebar)

        # View stack
        self.view_stack = QStackedWidget()

        # Create views
        self.library_view = LibraryView()
        self.download_view = DownloadView()
        self.translation_view = TranslationView()
        self.glossary_view = GlossaryView()
        self.settings_view = SettingsView()

        self.view_stack.addWidget(self.library_view)
        self.view_stack.addWidget(self.download_view)
        self.view_stack.addWidget(self.translation_view)
        self.view_stack.addWidget(self.glossary_view)
        self.view_stack.addWidget(self.settings_view)

        content_layout.addWidget(self.view_stack)
        main_layout.addLayout(content_layout)

        # Set default view
        self.sidebar.set_current_item("library")

    def _setup_tray(self):
        """Setup system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        # self.tray_icon.setIcon(QIcon(":/icons/app.png"))

        tray_menu = QMenu()
        tray_menu.addAction("Show", self.show)
        tray_menu.addSeparator()
        tray_menu.addAction("Quit", self.close)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _connect_signals(self):
        """Connect view signals to handlers."""
        # Library
        self.library_view.novel_selected.connect(self._on_novel_selected)

        # Download
        self.download_view.download_requested.connect(self._on_download_requested)

        # Settings
        self.settings_view.settings_changed.connect(self._on_settings_changed)

        # Theme
        theme_engine.theme_changed.connect(self._on_theme_changed)

    @Slot(str)
    def _on_nav_changed(self, item_id: str):
        """Handle navigation change."""
        view_map = {
            'library': 0,
            'download': 1,
            'translate': 2,
            'glossary': 3,
            'settings': 4,
        }
        index = view_map.get(item_id, 0)
        self.view_stack.setCurrentIndex(index)

    def _toggle_maximize(self):
        """Toggle window maximize state."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.title_bar.set_maximized(self.isMaximized())

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()

    @Slot(int)
    def _on_novel_selected(self, novel_id: int):
        """Handle novel selection."""
        pass  # Open novel detail view

    @Slot(str, dict)
    def _on_download_requested(self, url: str, options: dict):
        """Handle download request."""
        pass  # Start download job

    @Slot(dict)
    def _on_settings_changed(self, settings: dict):
        """Handle settings save."""
        pass  # Save to config

    @Slot(str)
    def _on_theme_changed(self, theme: str):
        """Handle theme change."""
        pass  # Additional UI updates if needed
```

---

## Toast Notifications

```python
# Location: sagemtl_desktop/ui/components/toast.py

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from typing import Optional


class Toast(QWidget):
    """Toast notification widget."""

    def __init__(self, message: str, toast_type: str = "info",
                 duration: int = 3000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._duration = duration
        self._setup_ui(message, toast_type)

    def _setup_ui(self, message: str, toast_type: str):
        colors = {
            'info': theme_engine.colors.info,
            'success': theme_engine.colors.success,
            'warning': theme_engine.colors.warning,
            'error': theme_engine.colors.error,
        }
        color = colors.get(toast_type, theme_engine.colors.info)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme_engine.colors.surface};
                border-left: 4px solid {color};
                border-radius: 8px;
                padding: 16px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        icon_map = {'info': 'ℹ️', 'success': '✓', 'warning': '⚠️', 'error': '✕'}
        icon = QLabel(icon_map.get(toast_type, 'ℹ️'))
        icon.setStyleSheet(f"color: {color}; font-size: 18px;")
        layout.addWidget(icon)

        label = QLabel(message)
        label.setStyleSheet(f"color: {theme_engine.colors.text_primary};")
        layout.addWidget(label)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def show_at(self, x: int, y: int):
        """Show toast at position."""
        self.move(x, y)
        self.show()

        # Auto-close timer
        QTimer.singleShot(self._duration, self._fade_out)

    def _fade_out(self):
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(self.close)
        anim.start()


class ToastManager:
    """Manages toast notifications."""

    _toasts: List[Toast] = []
    _parent: Optional[QWidget] = None

    @classmethod
    def set_parent(cls, parent: QWidget):
        cls._parent = parent

    @classmethod
    def show(cls, message: str, toast_type: str = "info", duration: int = 3000):
        if not cls._parent:
            return

        toast = Toast(message, toast_type, duration, cls._parent)

        # Position in bottom-right
        parent_rect = cls._parent.rect()
        x = parent_rect.width() - toast.sizeHint().width() - 24
        y = parent_rect.height() - toast.sizeHint().height() - 24 - (len(cls._toasts) * 80)

        toast.show_at(cls._parent.mapToGlobal(QPoint(x, y)).x(),
                     cls._parent.mapToGlobal(QPoint(x, y)).y())

        cls._toasts.append(toast)
        toast.destroyed.connect(lambda: cls._toasts.remove(toast) if toast in cls._toasts else None)
```

---

## Glassmorphism Effects (Optional)

```python
# Location: sagemtl_desktop/ui/effects/glassmorphism.py

from PySide6.QtWidgets import QWidget, QGraphicsBlurEffect
from PySide6.QtCore import Qt
import platform


class GlassPanel(QWidget):
    """Widget with glassmorphism effect."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_effect()

    def _setup_effect(self):
        if platform.system() == 'Windows':
            # Use Windows Acrylic effect via DWM
            try:
                from ctypes import windll, byref, c_int
                hwnd = int(self.winId())
                # Enable blur behind
                # This is simplified - real implementation needs DWM API
            except:
                pass

        # Fallback: CSS blur simulation
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme_engine.colors.glass_background};
                border: 1px solid {theme_engine.colors.glass_border};
                border-radius: 8px;
            }}
        """)
```

---

## Testing

```python
# Location: tests/test_ui_components.py

import pytest
from PySide6.QtWidgets import QApplication
from sagemtl_desktop.ui.theme_engine import ThemeEngine, ThemeMode
from sagemtl_desktop.ui.sidebar import Sidebar, NavItem

@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])

def test_theme_engine_singleton(app):
    """Theme engine should be singleton."""
    engine1 = ThemeEngine()
    engine2 = ThemeEngine()
    assert engine1 is engine2

def test_theme_switching(app):
    """Theme should switch correctly."""
    engine = ThemeEngine()
    engine.mode = ThemeMode.LIGHT
    assert engine.effective_theme == 'light'

    engine.mode = ThemeMode.DARK
    assert engine.effective_theme == 'dark'

def test_sidebar_navigation(app):
    """Sidebar navigation should emit signals."""
    sidebar = Sidebar()
    sidebar.add_nav_item(NavItem("test", "🔧", "Test"))

    received = []
    sidebar.navigation_changed.connect(lambda x: received.append(x))

    sidebar._on_nav_clicked("test")
    assert received == ["test"]
```
