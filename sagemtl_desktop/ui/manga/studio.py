"""Studio editor: a canvas to clean up and re-letter a translated page/strip.

A thin Qt shell over ``core.manga.studio.StudioModel``: draggable, restyleable text
layers over the cleaned page, plus the scanlation cleanup toolset (mask-paint
re-inpaint, clone-stamp redraw, bubble fill, levels, despeckle). All editing logic
lives in the model; the canvas just turns mouse actions into model calls and
re-renders. See ``MANGA_MODULE_BUILD_SPEC.md`` section 11.5.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sagemtl_desktop.core.manga.studio import StudioModel, TextLayer
from sagemtl_desktop.core.manga.typeset import DEFAULT_FONT_PATH

_FONTS_DIR = DEFAULT_FONT_PATH.parent


def _np_rgb_to_pixmap(rgb) -> QPixmap:
    import numpy as np

    arr = np.ascontiguousarray(rgb)
    h, w = arr.shape[:2]
    image = QImage(arr.data, w, h, 3 * w, QImage.Format_RGB888)
    return QPixmap.fromImage(image.copy())


def _np_rgba_to_pixmap(rgba) -> QPixmap:
    import numpy as np

    arr = np.ascontiguousarray(rgba)
    h, w = arr.shape[:2]
    image = QImage(arr.data, w, h, 4 * w, QImage.Format_RGBA8888)
    return QPixmap.fromImage(image.copy())


class _TextItem(QGraphicsPixmapItem):
    """A movable pixmap of one text layer; writes its position back to the layer."""

    def __init__(self, model: StudioModel, index: int) -> None:
        super().__init__()
        self._model = model
        self.index = index
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.refresh()

    def layer(self) -> TextLayer:
        return self._model.layers[self.index]

    def refresh(self) -> None:
        import numpy as np

        layer = self.layer()
        self.setPixmap(_np_rgba_to_pixmap(np.asarray(self._model.render_layer(layer))))
        self.setPos(layer.x, layer.y)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self._model.move_layer(self.index, int(self.x()), int(self.y()))
        return super().itemChange(change, value)


class StudioCanvas(QGraphicsView):
    """Canvas: background page + movable text items + cleanup tools."""

    layerSelected = Signal(int)

    def __init__(self, model: StudioModel, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model = model
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._bg = QGraphicsPixmapItem()
        self._bg.setZValue(0)
        self._scene.addItem(self._bg)
        self._text_items: list[_TextItem] = []
        self._tool = "select"
        self.brush_size = 14
        self.fill_color = (255, 255, 255)
        self._mask = None
        self._mask_item = QGraphicsPixmapItem()
        self._mask_item.setZValue(5)
        self._scene.addItem(self._mask_item)
        self._drag_start: Optional[QPointF] = None
        self._clone_src: Optional[QPointF] = None
        self.reload()

    # -- model sync ---------------------------------------------------------

    def reload(self) -> None:
        self.refresh_background()
        for item in self._text_items:
            self._scene.removeItem(item)
        self._text_items = []
        for i in range(len(self._model.layers)):
            item = _TextItem(self._model, i)
            item.setZValue(1)
            self._scene.addItem(item)
            self._text_items.append(item)
        self._reset_mask()
        self._scene.setSceneRect(QRectF(self._bg.pixmap().rect()))

    def refresh_background(self) -> None:
        self._bg.setPixmap(_np_rgb_to_pixmap(self._model.base))

    def refresh_layer(self, index: int) -> None:
        if 0 <= index < len(self._text_items):
            self._text_items[index].refresh()

    def _reset_mask(self) -> None:
        import numpy as np

        h, w = self._model.base.shape[:2]
        self._mask = np.zeros((h, w), np.uint8)
        self._mask_item.setPixmap(QPixmap())

    def set_tool(self, tool: str) -> None:
        self._tool = tool
        movable = tool == "select"
        for item in self._text_items:
            item.setFlag(QGraphicsItem.ItemIsMovable, movable)
            item.setFlag(QGraphicsItem.ItemIsSelectable, movable)

    # -- cleanup actions ----------------------------------------------------

    def apply_erase(self) -> None:
        if self._mask is not None and int(self._mask.max()) > 0:
            self._model.inpaint_mask(self._mask)
            self.refresh_background()
        self._reset_mask()

    def _update_mask_overlay(self) -> None:
        import numpy as np

        h, w = self._mask.shape
        rgba = np.zeros((h, w, 4), np.uint8)
        sel = self._mask > 0
        rgba[sel] = (255, 0, 0, 120)
        self._mask_item.setPixmap(_np_rgba_to_pixmap(rgba))

    def _paint_mask(self, point: QPointF) -> None:
        import cv2

        cv2.circle(self._mask, (int(point.x()), int(point.y())), self.brush_size, 255, -1)
        self._update_mask_overlay()

    # -- mouse handling -----------------------------------------------------

    def mousePressEvent(self, event):
        if self._tool == "select":
            super().mousePressEvent(event)
            items = [it for it in self.scene().selectedItems() if isinstance(it, _TextItem)]
            if items:
                self.layerSelected.emit(items[0].index)
            return
        scene_pt = self.mapToScene(event.position().toPoint())
        if self._tool == "erase":
            self._paint_mask(scene_pt)
        elif self._tool == "clone":
            if self._clone_src is None:
                self._clone_src = scene_pt
            else:
                self._drag_start = scene_pt
        elif self._tool == "fill":
            self._drag_start = scene_pt

    def mouseMoveEvent(self, event):
        if self._tool == "select":
            super().mouseMoveEvent(event)
            return
        if self._tool == "erase" and event.buttons():
            self._paint_mask(self.mapToScene(event.position().toPoint()))

    def mouseReleaseEvent(self, event):
        if self._tool == "select":
            super().mouseReleaseEvent(event)
            return
        scene_pt = self.mapToScene(event.position().toPoint())
        if self._tool == "fill" and self._drag_start is not None:
            self._apply_rect(self._drag_start, scene_pt, fill=True)
            self._drag_start = None
        elif self._tool == "clone" and self._clone_src is not None and self._drag_start is not None:
            self._apply_clone(self._clone_src, self._drag_start, scene_pt)
            self._clone_src = None
            self._drag_start = None

    def _apply_rect(self, p1: QPointF, p2: QPointF, *, fill: bool) -> None:
        x, y = int(min(p1.x(), p2.x())), int(min(p1.y(), p2.y()))
        w, h = int(abs(p2.x() - p1.x())), int(abs(p2.y() - p1.y()))
        if w > 0 and h > 0 and fill:
            self._model.fill_rect(x, y, w, h, self.fill_color)
            self.refresh_background()

    def _apply_clone(self, src: QPointF, dst1: QPointF, dst2: QPointF) -> None:
        w, h = int(abs(dst2.x() - dst1.x())), int(abs(dst2.y() - dst1.y()))
        if w > 0 and h > 0:
            self._model.clone_stamp(
                int(src.x()), int(src.y()), int(min(dst1.x(), dst2.x())), int(min(dst1.y(), dst2.y())), w, h
            )
            self.refresh_background()


class StudioWindow(QDialog):
    """Studio editor window: canvas + style/cleanup panels, saves the result."""

    def __init__(
        self,
        model: StudioModel,
        *,
        on_save: Optional[Callable[[bytes], None]] = None,
        language: str = "en",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self._on_save = on_save
        self._language = language
        self._selected = -1
        self.setWindowTitle("Studio")
        self.resize(1100, 720)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        self.canvas = StudioCanvas(self._model)
        self.canvas.layerSelected.connect(self._on_layer_selected)
        outer.addWidget(self.canvas, stretch=1)

        panel = QVBoxLayout()
        outer.addLayout(panel)

        # Tools
        self._tool_group = QButtonGroup(self)
        for label, tool in (("Move/Edit", "select"), ("Erase brush", "erase"), ("Clone", "clone"), ("Fill", "fill")):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _c, t=tool: self.canvas.set_tool(t))
            if tool == "select":
                btn.setChecked(True)
            self._tool_group.addButton(btn)
            panel.addWidget(btn)

        brush_row = QHBoxLayout()
        brush_row.addWidget(QLabel("Brush"))
        self._brush_spin = QSpinBox()
        self._brush_spin.setRange(2, 80)
        self._brush_spin.setValue(self.canvas.brush_size)
        self._brush_spin.valueChanged.connect(lambda v: setattr(self.canvas, "brush_size", v))
        brush_row.addWidget(self._brush_spin)
        panel.addLayout(brush_row)

        for label, handler in (
            ("Apply erase (inpaint)", self.canvas.apply_erase),
            ("Levels...", self._open_levels),
            ("Despeckle", self._despeckle),
            ("Fill color...", self._pick_fill_color),
            ("Reset image", self._reset_image),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            panel.addWidget(btn)

        panel.addWidget(self._build_text_properties())

        for label, handler in (("Add text", self._add_text), ("Delete layer", self._delete_layer)):
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            panel.addWidget(btn)

        panel.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Save).clicked.connect(self.save)
        buttons.rejected.connect(self.reject)
        panel.addWidget(buttons)

    def _build_text_properties(self) -> QWidget:
        box = QWidget()
        form = QFormLayout(box)
        self._font_combo = QComboBox()
        self._font_combo.addItem("Comic Neue Bold", "")
        for ttf in sorted(_FONTS_DIR.glob("*.ttf")):
            self._font_combo.addItem(ttf.stem, str(ttf))
        form.addRow("Font", self._font_combo)
        self._browse_font = QPushButton("Browse font...")
        self._browse_font.clicked.connect(self._browse_font_file)
        form.addRow("", self._browse_font)
        self._size_spin = QSpinBox()
        self._size_spin.setRange(0, 200)
        self._size_spin.setToolTip("0 = auto-fit")
        form.addRow("Size", self._size_spin)
        self._align_combo = QComboBox()
        self._align_combo.addItems(["left", "center", "right"])
        self._align_combo.setCurrentText("center")
        form.addRow("Align", self._align_combo)
        self._stroke_spin = QSpinBox()
        self._stroke_spin.setRange(0, 12)
        self._stroke_spin.setValue(2)
        form.addRow("Stroke", self._stroke_spin)
        self._line_spin = QDoubleSpinBox()
        self._line_spin.setRange(0.5, 3.0)
        self._line_spin.setSingleStep(0.1)
        self._line_spin.setValue(1.0)
        form.addRow("Line spacing", self._line_spin)
        self._text_color_btn = QPushButton("Text color")
        self._text_color_btn.clicked.connect(lambda: self._pick_layer_color("color"))
        form.addRow(self._text_color_btn)
        self._stroke_color_btn = QPushButton("Stroke color")
        self._stroke_color_btn.clicked.connect(lambda: self._pick_layer_color("stroke_color"))
        form.addRow(self._stroke_color_btn)
        apply_btn = QPushButton("Apply style")
        apply_btn.clicked.connect(self._apply_style)
        form.addRow(apply_btn)
        return box

    # -- selection / style --------------------------------------------------

    def _on_layer_selected(self, index: int) -> None:
        self._selected = index
        if 0 <= index < len(self._model.layers):
            layer = self._model.layers[index]
            self._size_spin.setValue(int(layer.font_size))
            self._align_combo.setCurrentText(layer.align)
            self._stroke_spin.setValue(int(layer.stroke_width))
            self._line_spin.setValue(float(layer.line_spacing))

    def _current_layer(self) -> Optional[TextLayer]:
        if 0 <= self._selected < len(self._model.layers):
            return self._model.layers[self._selected]
        return None

    def _apply_style(self) -> None:
        layer = self._current_layer()
        if layer is None:
            return
        layer.font_path = self._font_combo.currentData() or ""
        layer.font_size = int(self._size_spin.value())
        layer.align = self._align_combo.currentText()
        layer.stroke_width = int(self._stroke_spin.value())
        layer.line_spacing = float(self._line_spin.value())
        self.canvas.refresh_layer(self._selected)

    def _pick_layer_color(self, attr: str) -> None:
        layer = self._current_layer()
        if layer is None:
            return
        current = getattr(layer, attr)
        chosen = QColorDialog.getColor(QColor(*current), self)
        if chosen.isValid():
            setattr(layer, attr, (chosen.red(), chosen.green(), chosen.blue()))
            self.canvas.refresh_layer(self._selected)

    # -- cleanup ------------------------------------------------------------

    def _open_levels(self) -> None:
        dialog = _LevelsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            black, white, gamma = dialog.values()
            self._model.apply_levels(black, white, gamma)
            self.canvas.refresh_background()

    def _despeckle(self) -> None:
        self._model.despeckle(3)
        self.canvas.refresh_background()

    def _pick_fill_color(self) -> None:
        chosen = QColorDialog.getColor(QColor(*self.canvas.fill_color), self)
        if chosen.isValid():
            self.canvas.fill_color = (chosen.red(), chosen.green(), chosen.blue())

    def _reset_image(self) -> None:
        self._model.reset_image()
        self.canvas.refresh_background()

    # -- layers -------------------------------------------------------------

    def _add_text(self) -> None:
        h, w = self._model.base.shape[:2]
        layer = TextLayer(text="New text", x=w // 4, y=h // 4, width=max(80, w // 3), height=max(40, h // 8))
        self._model.add_layer(layer)
        self.canvas.reload()

    def _delete_layer(self) -> None:
        if self._selected >= 0:
            self._model.remove_layer(self._selected)
            self._selected = -1
            self.canvas.reload()

    def _browse_font_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose font", "", "Fonts (*.ttf *.otf)")
        if path:
            self._font_combo.addItem(Path(path).stem, path)
            self._font_combo.setCurrentIndex(self._font_combo.count() - 1)

    # -- save ---------------------------------------------------------------

    def render_bytes(self) -> bytes:
        import io

        import numpy as np
        from PIL import Image

        rendered = self._model.render()
        buffer = io.BytesIO()
        Image.fromarray(np.asarray(rendered)).save(buffer, format="PNG")
        return buffer.getvalue()

    def save(self) -> None:
        data = self.render_bytes()
        if self._on_save is not None:
            self._on_save(data)
        self.accept()


class _LevelsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Levels")
        form = QFormLayout(self)
        self._black = QSpinBox()
        self._black.setRange(0, 254)
        self._white = QSpinBox()
        self._white.setRange(1, 255)
        self._white.setValue(255)
        self._gamma = QDoubleSpinBox()
        self._gamma.setRange(0.1, 5.0)
        self._gamma.setSingleStep(0.05)
        self._gamma.setValue(1.0)
        form.addRow("Black point", self._black)
        form.addRow("White point", self._white)
        form.addRow("Gamma", self._gamma)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return self._black.value(), self._white.value(), self._gamma.value()
