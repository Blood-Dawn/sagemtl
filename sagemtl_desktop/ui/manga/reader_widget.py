"""Manga reader widget: page view with before/after toggle and region overlay.

Thin presentation only -- it is handed page data (raw + rendered bytes + serialized
regions) and renders it. No business logic. See spec section 11.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr

_CLASS_COLORS = {
    "bubble": QColor(0, 128, 255),
    "text_bubble": QColor(0, 200, 0),
    "text_free": QColor(255, 0, 0),
}


class ReaderWidget(QWidget):
    """Displays one page at a time with a before/after toggle and region overlay."""

    def __init__(self, language: str = "en", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._language = language
        self._pages: list[dict] = []
        self._index = 0
        self._show_after = True
        self._show_regions = False
        self._build_ui()
        self._render()

    def _tr(self, key: str) -> str:
        return tr(self._language, key)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        self._toggle_btn = QPushButton(self._tr("manga.reader.after"))
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.clicked.connect(self._on_toggle)
        bar.addWidget(self._toggle_btn)

        self._regions_cb = QCheckBox(self._tr("manga.reader.show_regions"))
        self._regions_cb.toggled.connect(self._on_regions_toggled)
        bar.addWidget(self._regions_cb)

        bar.addStretch(1)
        self._prev_btn = QPushButton("<")
        self._prev_btn.clicked.connect(self.prev_page)
        bar.addWidget(self._prev_btn)
        self._page_label = QLabel("0 / 0")
        bar.addWidget(self._page_label)
        self._next_btn = QPushButton(">")
        self._next_btn.clicked.connect(self.next_page)
        bar.addWidget(self._next_btn)
        layout.addLayout(bar)

        self._image_label = QLabel(self._tr("manga.empty"))
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setMinimumSize(320, 320)
        layout.addWidget(self._image_label, stretch=1)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

    # -- public API ---------------------------------------------------------

    def set_pages(self, pages: list[dict]) -> None:
        """``pages``: list of {raw: bytes, rendered: bytes, regions: list, status: str}."""
        self._pages = list(pages)
        self._index = 0
        self._render()

    def clear(self) -> None:
        self._pages = []
        self._index = 0
        self._render()

    def current_index(self) -> int:
        return self._index

    def next_page(self) -> None:
        if self._index < len(self._pages) - 1:
            self._index += 1
            self._render()

    def prev_page(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._render()

    # -- internals ----------------------------------------------------------

    def _on_toggle(self, checked: bool) -> None:
        self._show_after = checked
        self._toggle_btn.setText(
            self._tr("manga.reader.after") if checked else self._tr("manga.reader.before")
        )
        self._render()

    def _on_regions_toggled(self, checked: bool) -> None:
        self._show_regions = checked
        self._render()

    def _current(self) -> Optional[dict]:
        if 0 <= self._index < len(self._pages):
            return self._pages[self._index]
        return None

    def _render(self) -> None:
        total = len(self._pages)
        self._page_label.setText(f"{self._index + 1 if total else 0} / {total}")
        page = self._current()
        if page is None:
            self._image_label.setPixmap(QPixmap())
            self._image_label.setText(self._tr("manga.empty"))
            self._status_label.setText("")
            return

        data = page.get("rendered") if self._show_after else page.get("raw")
        if not data:
            data = page.get("raw") or page.get("rendered")
        pixmap = QPixmap()
        if data:
            image = QImage.fromData(data)
            pixmap = QPixmap.fromImage(image)
        if not pixmap.isNull() and self._show_regions:
            pixmap = self._draw_regions(pixmap, page.get("regions", []))
        if pixmap.isNull():
            self._image_label.setText(self._tr("manga.empty"))
        else:
            self._image_label.setText("")
            self._image_label.setPixmap(
                pixmap.scaled(
                    self._image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        self._status_label.setText(str(page.get("status", "")))

    def _draw_regions(self, pixmap: QPixmap, regions: list) -> QPixmap:
        canvas = QPixmap(pixmap)
        painter = QPainter(canvas)
        try:
            for region in regions:
                box = region.get("box") if isinstance(region, dict) else None
                if not box or len(box) != 4:
                    continue
                color = _CLASS_COLORS.get(region.get("cls", ""), QColor(255, 255, 0))
                painter.setPen(QPen(color, 2))
                x1, y1, x2, y2 = (int(v) for v in box)
                painter.drawRect(x1, y1, max(1, x2 - x1), max(1, y2 - y1))
        finally:
            painter.end()
        return canvas
