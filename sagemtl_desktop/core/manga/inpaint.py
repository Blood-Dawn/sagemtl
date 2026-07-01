"""Stage 4: erase and inpaint.

Mask quality dominates inpaint quality, so the work is: build a tight glyph mask,
then fill. The mask is built per text region by thresholding the glyph pixels
(auto-detecting dark-on-light vs light-on-dark from the box border) and dilating a
few pixels so anti-aliased edges and outlines are covered. Filling is hybrid:

  - Solid-color bubbles: flat-fill the masked glyphs with the sampled bubble color
    (fast, flawless, no halo, no ML).
  - Text over artwork: neural inpaint when a neural inpainter is available, else
    classical ``cv2.inpaint`` (Telea). Both are permissive and the classical path
    is always available.

This is fully classical/OpenCV by default (no torch, no AGPL ``ultralytics`` for
masks); the optional ``LamaInpainter`` wraps IOPaint (Apache-2.0) and degrades to
the classical path if unavailable. All heavy imports are lazy.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 7.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Sequence

from .detect import TEXT_CLASSES, default_debug_dir
from .models import TextRegion

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np

__all__ = [
    "build_mask",
    "run",
    "Inpainter",
    "ClassicalInpainter",
    "LamaInpainter",
    "build_inpainter",
    "save_debug_sidebyside",
    "DEFAULT_DILATE",
]

DEFAULT_DILATE = 3
_SOLID_STD_THRESHOLD = 28.0  # max background channel std to treat a bubble as solid
_MIN_BG_PIXELS = 16


def _clip_box(box, width, height):
    x1 = max(0, min(int(box[0]), width))
    y1 = max(0, min(int(box[1]), height))
    x2 = max(0, min(int(box[2]), width))
    y2 = max(0, min(int(box[3]), height))
    return x1, y1, x2, y2


def _glyph_mask(crop_gray: "np.ndarray") -> "np.ndarray":
    """Binary (0/255) glyph mask for a grayscale text crop, polarity auto-detected."""

    import cv2
    import numpy as np

    if crop_gray.size == 0:
        return crop_gray
    border = np.concatenate(
        [crop_gray[0, :], crop_gray[-1, :], crop_gray[:, 0], crop_gray[:, -1]]
    )
    bg_light = float(border.mean()) >= 128.0
    # Use OpenCV's thresholded output directly: INV makes dark glyphs (on a light
    # bubble) the foreground; plain BINARY makes light glyphs (on a dark bubble)
    # the foreground. (A manual `gray < otsu_t` breaks on perfectly bimodal crops
    # where Otsu reports t == 0.)
    flag = (cv2.THRESH_BINARY_INV if bg_light else cv2.THRESH_BINARY) + cv2.THRESH_OTSU
    _, binary = cv2.threshold(crop_gray, 0, 255, flag)
    return binary


def build_mask(
    page_rgb: "np.ndarray",
    regions: Sequence[TextRegion],
    *,
    dilate: int = DEFAULT_DILATE,
    classes: tuple[str, ...] = TEXT_CLASSES,
) -> "np.ndarray":
    """Build a dilated uint8 glyph mask (255 = erase) over the text regions."""

    import cv2
    import numpy as np

    height, width = page_rgb.shape[:2]
    gray = cv2.cvtColor(page_rgb, cv2.COLOR_RGB2GRAY)
    mask = np.zeros((height, width), dtype=np.uint8)
    for region in regions:
        if region.cls not in classes:
            continue
        x1, y1, x2, y2 = _clip_box(region.box, width, height)
        if x2 <= x1 or y2 <= y1:
            continue
        glyph = _glyph_mask(gray[y1:y2, x1:x2])
        mask[y1:y2, x1:x2] = np.maximum(mask[y1:y2, x1:x2], glyph)
    if dilate > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * dilate + 1, 2 * dilate + 1))
        mask = cv2.dilate(mask, kernel)
    return mask


def _is_solid_bubble(crop_rgb: "np.ndarray", glyph_mask: "np.ndarray") -> bool:
    background = crop_rgb[glyph_mask == 0]
    if background.shape[0] < _MIN_BG_PIXELS:
        return False
    return float(background.reshape(-1, crop_rgb.shape[2]).std(axis=0).max()) < _SOLID_STD_THRESHOLD


def _bg_color(crop_rgb: "np.ndarray", glyph_mask: "np.ndarray"):
    import numpy as np

    background = crop_rgb[glyph_mask == 0]
    if background.shape[0] == 0:
        return tuple(int(v) for v in np.median(crop_rgb.reshape(-1, crop_rgb.shape[2]), axis=0))
    return tuple(int(v) for v in np.median(background.reshape(-1, crop_rgb.shape[2]), axis=0))


class Inpainter:
    """Neural/classical inpainter. ``inpaint`` takes RGB image + uint8 mask."""

    name = "base"

    def inpaint(self, image_rgb: "np.ndarray", mask: "np.ndarray") -> "np.ndarray":  # pragma: no cover
        raise NotImplementedError


class ClassicalInpainter(Inpainter):
    """Permissive, always-available inpainting via OpenCV (Telea / Navier-Stokes)."""

    name = "classical"

    def __init__(self, radius: int = 3, method: str = "telea") -> None:
        self.radius = radius
        self.method = method

    def inpaint(self, image_rgb: "np.ndarray", mask: "np.ndarray") -> "np.ndarray":
        import cv2

        flag = cv2.INPAINT_NS if self.method == "ns" else cv2.INPAINT_TELEA
        bgr = image_rgb[:, :, ::-1]
        out = cv2.inpaint(bgr, mask, self.radius, flag)
        return out[:, :, ::-1]


class LamaInpainter(Inpainter):
    """Optional neural inpainting via IOPaint/LaMa (Apache-2.0). Best-effort.

    Falls back to the classical inpainter if IOPaint or the model is unavailable,
    so it never crashes the pipeline.
    """

    name = "lama"

    def __init__(self, model: str = "lama", device: str = "auto") -> None:
        self.model = model
        self.device = device
        self._mgr = None
        self._fallback = ClassicalInpainter()

    def _ensure(self):
        if self._mgr is None:
            from iopaint.model_manager import ModelManager

            from . import model_registry

            self._mgr = ModelManager(name=self.model, device=model_registry.select_device(self.device))
        return self._mgr

    def inpaint(self, image_rgb: "np.ndarray", mask: "np.ndarray") -> "np.ndarray":
        try:
            from iopaint.schema import InpaintRequest

            manager = self._ensure()
            result_bgr = manager(image_rgb[:, :, ::-1], mask, InpaintRequest())
            return result_bgr[:, :, ::-1]
        except Exception:
            return self._fallback.inpaint(image_rgb, mask)


def build_inpainter(config=None) -> Optional[Inpainter]:
    """Return the configured neural inpainter, or None to use the classical path."""

    model = (getattr(config, "inpaint_model", "") if config else "") or ""
    device = getattr(config, "device", "auto") if config else "auto"
    if model.strip().lower() in ("", "none", "classical", "cv2"):
        return None
    return LamaInpainter(device=device)


def run(
    page_rgb: "np.ndarray",
    regions: Sequence[TextRegion],
    *,
    mask: "Optional[np.ndarray]" = None,
    dilate: int = DEFAULT_DILATE,
    inpainter: Optional[Inpainter] = None,
    classes: tuple[str, ...] = TEXT_CLASSES,
) -> "np.ndarray":
    """Return a cleaned RGB page with text erased (flat-fill + inpaint)."""

    import numpy as np

    if mask is None:
        mask = build_mask(page_rgb, regions, dilate=dilate, classes=classes)

    clean = np.ascontiguousarray(page_rgb.copy())
    height, width = clean.shape[:2]
    remaining = mask.copy()

    for region in regions:
        if region.cls not in classes:
            continue
        x1, y1, x2, y2 = _clip_box(region.box, width, height)
        if x2 <= x1 or y2 <= y1:
            continue
        sub = mask[y1:y2, x1:x2]
        if not sub.any():
            continue
        crop = clean[y1:y2, x1:x2]
        if _is_solid_bubble(crop, sub):
            color = _bg_color(crop, sub)
            selected = sub > 0
            crop[selected] = color
            remaining[y1:y2, x1:x2][selected] = 0  # handled by flat-fill

    if remaining.any():
        engine = inpainter or ClassicalInpainter()
        clean = engine.inpaint(clean, remaining)

    return np.ascontiguousarray(clean)


def save_debug_sidebyside(
    original_rgb: "np.ndarray",
    clean_rgb: "np.ndarray",
    dest: "str | Path | None" = None,
) -> Path:
    """Save an original|cleaned side-by-side PNG for visual inspection."""

    import numpy as np
    from PIL import Image

    if dest is None:
        dest = default_debug_dir() / "inpaint_before_after.png"
    combined = np.concatenate([original_rgb, clean_rgb], axis=1)
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(combined).save(str(dest_path))
    return dest_path
