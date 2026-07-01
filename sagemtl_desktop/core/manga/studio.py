"""Studio model: a manual cleaner + typesetter pass over a translated page.

Qt-free core for the Studio editor. Holds an editable (already inpainted) page
image plus a list of rich, freely-positioned ``TextLayer`` objects, and exposes the
scanlation toolset: cleanup ops that mutate the image (levels/contrast, mask-paint
re-inpaint, clone-stamp redraw, bubble fill, despeckle) and ``render`` which
composites the styled text layers onto the cleaned image. The UI is a thin canvas
on top of this. All heavy imports (numpy, cv2, PIL) are lazy.

Scanlation reference: cleaners level/redraw/erase with brush + clone-stamp +
heal + dust removal; typesetters place fitted, outlined text per bubble.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from .detect import TEXT_CLASSES
from .typeset import _line_height, fit_text, resolve_font_path, wrap_text

__all__ = ["TextLayer", "StudioModel"]


@dataclass
class TextLayer:
    """A freely positioned, richly styled block of text drawn over the page."""

    text: str
    x: int
    y: int
    width: int
    height: int
    font_path: str = ""               # "" -> Studio default (Comic Neue)
    font_size: int = 0                # 0 -> auto-fit to the box
    color: tuple = (0, 0, 0)
    stroke_color: tuple = (255, 255, 255)
    stroke_width: int = 2
    align: str = "center"             # left | center | right
    bold: bool = True
    line_spacing: float = 1.0
    visible: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["color"] = list(self.color)
        data["stroke_color"] = list(self.stroke_color)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TextLayer":
        data = dict(data)
        data["color"] = tuple(data.get("color", (0, 0, 0)))
        data["stroke_color"] = tuple(data.get("stroke_color", (255, 255, 255)))
        return cls(**data)


@dataclass
class StudioModel:
    """Editable page + text layers with cleanup ops and a compositing renderer."""

    base: Any                         # HxWx3 RGB uint8 (mutated by cleanup ops)
    layers: list[TextLayer] = field(default_factory=list)
    default_font: Optional[str] = None
    _original: Any = None             # pristine copy for reset

    def __post_init__(self) -> None:
        import numpy as np

        self.base = np.ascontiguousarray(self.base.copy())
        self._original = self.base.copy()

    # -- construction -------------------------------------------------------

    @classmethod
    def from_regions(cls, clean_rgb, regions, *, default_font: Optional[str] = None) -> "StudioModel":
        """Build a Studio from a cleaned page + translated text regions."""

        layers: list[TextLayer] = []
        for region in regions:
            cls_name = getattr(region, "cls", "text_bubble")
            if cls_name not in TEXT_CLASSES:
                continue
            text = (getattr(region, "target_text", "") or "").strip()
            if not text:
                continue
            x1, y1, x2, y2 = region.box
            layers.append(TextLayer(text=text, x=int(x1), y=int(y1), width=int(x2 - x1), height=int(y2 - y1)))
        return cls(base=clean_rgb, layers=layers, default_font=default_font)

    # -- layer ops ----------------------------------------------------------

    def add_layer(self, layer: TextLayer) -> int:
        self.layers.append(layer)
        return len(self.layers) - 1

    def remove_layer(self, index: int) -> None:
        if 0 <= index < len(self.layers):
            del self.layers[index]

    def move_layer(self, index: int, x: int, y: int) -> None:
        if 0 <= index < len(self.layers):
            self.layers[index].x = int(x)
            self.layers[index].y = int(y)

    # -- cleanup ops (mutate self.base) -------------------------------------

    def reset_image(self) -> None:
        self.base = self._original.copy()

    def apply_levels(self, black: int = 0, white: int = 255, gamma: float = 1.0) -> None:
        """Photoshop-style input levels + gamma (contrast cleanup)."""

        import numpy as np

        black = max(0, min(int(black), 254))
        white = max(black + 1, min(int(white), 255))
        gamma = max(0.05, float(gamma))
        scale = np.arange(256, dtype=np.float32)
        scale = np.clip((scale - black) / (white - black), 0.0, 1.0)
        lut = np.clip((scale ** (1.0 / gamma)) * 255.0, 0, 255).astype(np.uint8)
        self.base = lut[self.base]

    def inpaint_mask(self, mask, radius: int = 3, method: str = "telea") -> None:
        """Erase/redraw under a painted mask (uint8, 255 = paint)."""

        import cv2

        flag = cv2.INPAINT_NS if method == "ns" else cv2.INPAINT_TELEA
        bgr = self.base[:, :, ::-1]
        out = cv2.inpaint(bgr, mask, radius, flag)
        self.base = out[:, :, ::-1].copy()

    def clone_stamp(self, src_x: int, src_y: int, dst_x: int, dst_y: int, width: int, height: int) -> None:
        """Copy a source patch over a destination (redraw art under text)."""

        h, w = self.base.shape[:2]
        width = max(1, min(int(width), w))
        height = max(1, min(int(height), h))
        sx, sy = max(0, min(int(src_x), w - width)), max(0, min(int(src_y), h - height))
        dx, dy = max(0, min(int(dst_x), w - width)), max(0, min(int(dst_y), h - height))
        patch = self.base[sy:sy + height, sx:sx + width].copy()
        self.base[dy:dy + height, dx:dx + width] = patch

    def fill_rect(self, x: int, y: int, width: int, height: int, color: tuple) -> None:
        """Flat-fill a rectangle (white/black bubble fill)."""

        h, w = self.base.shape[:2]
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(w, x1 + int(width)), min(h, y1 + int(height))
        if x2 > x1 and y2 > y1:
            self.base[y1:y2, x1:x2] = tuple(int(c) for c in color)

    def despeckle(self, ksize: int = 3) -> None:
        """Median-blur dust removal (odd ksize)."""

        import cv2

        ksize = max(3, int(ksize) | 1)  # force odd >= 3
        self.base = cv2.medianBlur(self.base, ksize)

    # -- render -------------------------------------------------------------

    def _font_for(self, layer: TextLayer):
        path = layer.font_path or resolve_font_path(self.default_font)
        if not layer.font_path and not layer.bold:
            regular = resolve_font_path(str(path).replace("ComicNeue-Bold", "ComicNeue-Regular"))
            path = regular
        return path

    def render_layer(self, layer: TextLayer):
        """Render one text layer to a box-sized RGBA PIL image (transparent bg)."""

        from PIL import Image, ImageDraw, ImageFont

        avail_w = max(1, int(layer.width))
        avail_h = max(1, int(layer.height))
        box = Image.new("RGBA", (avail_w, avail_h), (0, 0, 0, 0))
        text = (layer.text or "").strip()
        if not text:
            return box

        font_path = self._font_for(layer)
        if layer.font_size and layer.font_size > 0:
            font = ImageFont.truetype(font_path, int(layer.font_size))
            lines = wrap_text(text, font, avail_w)
        else:
            _size, lines, font = fit_text(text, font_path, avail_w, avail_h)

        draw = ImageDraw.Draw(box)
        line_h = int(_line_height(font) * max(0.5, layer.line_spacing))
        block_h = line_h * len(lines)
        cursor_y = max(0, (avail_h - block_h) // 2)
        for line in lines:
            line_w = font.getlength(line)
            if layer.align == "left":
                cursor_x = 0.0
            elif layer.align == "right":
                cursor_x = max(0.0, avail_w - line_w)
            else:
                cursor_x = max(0.0, (avail_w - line_w) / 2)
            draw.text(
                (cursor_x, cursor_y), line, font=font,
                fill=tuple(layer.color) + (255,),
                stroke_width=max(0, int(layer.stroke_width)),
                stroke_fill=tuple(layer.stroke_color) + (255,),
            )
            cursor_y += line_h
        return box

    def render(self) -> Any:
        """Composite all visible text layers onto the cleaned image (RGB array)."""

        import numpy as np
        from PIL import Image

        image = Image.fromarray(np.ascontiguousarray(self.base.copy())).convert("RGB")
        page_w, page_h = image.size
        for layer in self.layers:
            if not layer.visible or not (layer.text or "").strip():
                continue
            box = self.render_layer(layer)
            px = max(0, min(int(layer.x), page_w - 1))
            py = max(0, min(int(layer.y), page_h - 1))
            image.paste(box, (px, py), box)
        return np.asarray(image.convert("RGB"))

    # -- persistence (layers only; image bytes live on disk) ----------------

    def layers_to_list(self) -> list[dict]:
        return [layer.to_dict() for layer in self.layers]

    @staticmethod
    def layers_from_list(data: list[dict]) -> list[TextLayer]:
        return [TextLayer.from_dict(item) for item in data]
