"""Manual correction editor: fix OCR/translation, nudge placement, re-render a page.

Given a cleaned page image + its detected regions, the user can edit each region's
recognized text and translation and nudge its position, then re-render just that
page (typeset only -- no models, so it is sub-second). Thin UI: the actual
re-render is ``core.manga.jobs.rerender_page``. See spec section 11.5.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from sagemtl_desktop.core.manga import jobs as manga_jobs
from sagemtl_desktop.core.manga.models import TextRegion

from ..i18n import tr

_COLUMNS = ["Class", "Source", "Translation", "X", "Y"]


class TypesetEditor(QDialog):
    """Edit a page's regions and re-render the page."""

    def __init__(
        self,
        clean_image: bytes,
        regions,
        *,
        font_path: Optional[str] = None,
        target_lang: str = "en",
        language: str = "en",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._clean_image = clean_image
        self._font_path = font_path
        self._target_lang = target_lang
        self._language = language
        # Work on copies so a cancel leaves the originals untouched.
        self._regions = [self._as_region(r) for r in regions]
        self._rendered: bytes = b""
        self.setWindowTitle(tr(language, "action.manga_open_reader"))
        self.resize(820, 560)
        self._build_ui()
        self._rerender()

    @staticmethod
    def _as_region(region) -> TextRegion:
        if isinstance(region, TextRegion):
            return TextRegion(
                box=tuple(region.box), polygon=list(region.polygon), cls=region.cls,
                source_text=region.source_text, target_text=region.target_text,
                lang=region.lang, conf=region.conf,
            )
        return TextRegion.from_dict(region)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        content = QHBoxLayout()

        self._table = QTableWidget(len(self._regions), len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for row, region in enumerate(self._regions):
            x1, y1, _x2, _y2 = region.box
            cells = [region.cls, region.source_text, region.target_text, str(x1), str(y1)]
            for col, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if col == 0:  # class is read-only
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self._table.setItem(row, col, item)
        content.addWidget(self._table, stretch=1)

        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setMinimumSize(320, 420)
        content.addWidget(self._preview, stretch=1)
        layout.addLayout(content)

        self._rerender_btn = QPushButton("Re-render")
        self._rerender_btn.clicked.connect(self._rerender)
        layout.addWidget(self._rerender_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _collect_regions(self) -> list[TextRegion]:
        """Read edits from the table back into the region list (preserving size)."""
        for row, region in enumerate(self._regions):
            region.source_text = self._table.item(row, 1).text()
            region.target_text = self._table.item(row, 2).text()
            x1, y1, x2, y2 = region.box
            width, height = x2 - x1, y2 - y1
            new_x = _to_int(self._table.item(row, 3).text(), x1)
            new_y = _to_int(self._table.item(row, 4).text(), y1)
            region.box = (new_x, new_y, new_x + width, new_y + height)
        return self._regions

    def _rerender(self) -> None:
        regions = self._collect_regions()
        self._rendered = manga_jobs.rerender_page(
            self._clean_image, regions, font_path=self._font_path, target_lang=self._target_lang
        )
        pixmap = QPixmap.fromImage(QImage.fromData(self._rendered))
        if not pixmap.isNull():
            self._preview.setPixmap(
                pixmap.scaled(self._preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    # -- results for the caller --------------------------------------------

    def get_rendered_bytes(self) -> bytes:
        return self._rendered

    def get_regions(self) -> list[TextRegion]:
        return self._regions


def _to_int(text: str, default: int) -> int:
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return default
