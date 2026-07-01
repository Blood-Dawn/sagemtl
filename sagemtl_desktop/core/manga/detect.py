"""Stage 1: bubble and text detection.

Wraps the default detector ``ogkalu/comic-text-and-bubble-detector`` (RT-DETR-v2,
Apache-2.0) run through ONNX Runtime, so CPU users work out of the box with no
torch dependency. The exported ONNX graph performs its own post-processing: given
``images`` (N,3,640,640 float, RGB, rescaled to [0,1], no mean/std) and
``orig_target_sizes`` ([[width, height]] int64), it returns ``labels``, ``boxes``
(xyxy in original-image coordinates), and ``scores`` for the top queries.

Classes (from the model's ``config.json`` id2label):
    0 -> bubble        (speech balloon region; used for inpaint flat-fill later)
    1 -> text_bubble   (text inside a bubble)
    2 -> text_free     (free / SFX text over artwork)

The full-page text mask in this phase is box-based over the text classes; the
tighter per-glyph segmenter mask (``ogkalu/comic-text-segmenter-yolov8m``) is
added in Phase 4 where inpaint quality depends on it. All heavy imports
(onnxruntime, numpy, cv2, PIL) are lazy and live inside function bodies.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 3.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from . import model_registry
from .models import TextRegion

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np
    import onnxruntime as ort

__all__ = [
    "TextRegion",
    "Detector",
    "build_text_mask",
    "load_image_rgb",
    "save_debug_overlay",
    "default_debug_dir",
    "DEFAULT_CONF_THRESHOLD",
    "TEXT_CLASSES",
]

# Stable class map (model config.json id2label). Read from the snapshot when
# available, with this as the fallback.
_DEFAULT_ID2LABEL = {0: "bubble", 1: "text_bubble", 2: "text_free"}
TEXT_CLASSES = ("text_bubble", "text_free")
_DEFAULT_INPUT_SIZE = 640
DEFAULT_CONF_THRESHOLD = 0.30

# RGB colors per class for debug overlays.
_CLASS_COLORS = {
    "bubble": (0, 128, 255),
    "text_bubble": (0, 200, 0),
    "text_free": (255, 0, 0),
}


@dataclass
class _LoadedDetector:
    session: "ort.InferenceSession"
    id2label: dict
    input_size: int


def _resolve_onnx(snapshot: Path, model_key: str) -> Path:
    """Pick the ONNX weight file from a downloaded snapshot directory."""

    preferred = snapshot / "detector.onnx"
    if preferred.exists():
        return preferred
    candidates = sorted(snapshot.glob("*.onnx"))
    if not candidates:
        raise FileNotFoundError(f"No .onnx file found for model {model_key!r} in {snapshot}")
    return candidates[0]


def _read_id2label(snapshot: Path) -> dict:
    config = snapshot / "config.json"
    if config.exists():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
            mapping = data.get("id2label")
            if mapping:
                return {int(k): str(v) for k, v in mapping.items()}
        except (ValueError, OSError):
            pass
    return dict(_DEFAULT_ID2LABEL)


def _read_input_size(snapshot: Path) -> int:
    pre = snapshot / "preprocessor_config.json"
    if pre.exists():
        try:
            data = json.loads(pre.read_text(encoding="utf-8"))
            size = data.get("size") or {}
            height = int(size.get("height", _DEFAULT_INPUT_SIZE))
            width = int(size.get("width", _DEFAULT_INPUT_SIZE))
            # The model is square; use height (== width for this model).
            return height if height == width else max(height, width)
        except (ValueError, OSError):
            pass
    return _DEFAULT_INPUT_SIZE


def _providers_for_device(device: str) -> list[str]:
    import onnxruntime as ort

    resolved = model_registry.select_device(device)
    available = set(ort.get_available_providers())
    chain = []
    if resolved == "cuda" and "CUDAExecutionProvider" in available:
        chain.append("CUDAExecutionProvider")
    chain.append("CPUExecutionProvider")
    return chain


class Detector:
    """Bubble/text detector facade over the RT-DETR ONNX model."""

    def __init__(
        self,
        model_key: str = "detector",
        device: str = "auto",
        conf_threshold: float = DEFAULT_CONF_THRESHOLD,
    ) -> None:
        self.model_key = model_key
        self.device = device
        self.conf_threshold = conf_threshold

    def _model(self) -> _LoadedDetector:
        return model_registry.load(self.model_key, loader=self._build_model)

    def _build_model(self, spec) -> _LoadedDetector:
        import onnxruntime as ort

        snapshot = Path(model_registry.ensure(spec.key))
        onnx_path = _resolve_onnx(snapshot, spec.key)
        session = ort.InferenceSession(
            str(onnx_path), providers=_providers_for_device(self.device)
        )
        return _LoadedDetector(
            session=session,
            id2label=_read_id2label(snapshot),
            input_size=_read_input_size(snapshot),
        )

    def _preprocess(self, image: "np.ndarray", input_size: int) -> "np.ndarray":
        import cv2
        import numpy as np

        resized = cv2.resize(image, (input_size, input_size), interpolation=cv2.INTER_LINEAR)
        array = resized.astype(np.float32) / 255.0          # rescale, no mean/std
        array = np.transpose(array, (2, 0, 1))[None, ...]   # NCHW
        return np.ascontiguousarray(array)

    def detect(self, image: "np.ndarray") -> "tuple[list[TextRegion], np.ndarray]":
        """Detect regions in an RGB ``HxWx3`` uint8 image.

        Returns ``(regions, full_page_text_mask)`` where the mask is a ``uint8``
        page-sized array (255 inside text regions).
        """

        import numpy as np

        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("Detector.detect expects an RGB HxWx3 image array")

        model = self._model()
        height, width = int(image.shape[0]), int(image.shape[1])
        inputs = {
            "images": self._preprocess(image, model.input_size),
            "orig_target_sizes": np.array([[width, height]], dtype=np.int64),
        }
        labels, boxes, scores = model.session.run(None, inputs)
        labels, boxes, scores = labels[0], boxes[0], scores[0]

        regions: list[TextRegion] = []
        for label, box, score in zip(labels, boxes, scores):
            if float(score) < self.conf_threshold:
                continue
            x1 = max(0, min(int(round(float(box[0]))), width))
            y1 = max(0, min(int(round(float(box[1]))), height))
            x2 = max(0, min(int(round(float(box[2]))), width))
            y2 = max(0, min(int(round(float(box[3]))), height))
            if x2 <= x1 or y2 <= y1:
                continue
            cls = model.id2label.get(int(label), str(int(label)))
            polygon = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
            regions.append(
                TextRegion(box=(x1, y1, x2, y2), polygon=polygon, cls=cls, conf=float(score))
            )

        mask = build_text_mask(regions, (height, width))
        return regions, mask


def build_text_mask(
    regions: "list[TextRegion]",
    shape: tuple[int, int],
    classes: tuple[str, ...] = TEXT_CLASSES,
) -> "np.ndarray":
    """Build a box-based uint8 text mask (255 inside text regions)."""

    import numpy as np

    height, width = shape
    mask = np.zeros((height, width), dtype=np.uint8)
    for region in regions:
        if region.cls not in classes:
            continue
        x1, y1, x2, y2 = region.box
        x1 = max(0, min(int(x1), width))
        x2 = max(0, min(int(x2), width))
        y1 = max(0, min(int(y1), height))
        y2 = max(0, min(int(y2), height))
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 255
    return mask


def load_image_rgb(data: bytes) -> "np.ndarray":
    """Decode image bytes into an RGB ``HxWx3`` uint8 array."""

    import numpy as np
    from PIL import Image

    with Image.open(io.BytesIO(data)) as img:
        return np.asarray(img.convert("RGB"))


def default_debug_dir() -> Path:
    """Return the default debug-overlay directory (``~/.sagemtl/debug``)."""

    return Path.home() / ".sagemtl" / "debug"


def save_debug_overlay(
    image: "np.ndarray",
    regions: "list[TextRegion]",
    mask: "Optional[np.ndarray]",
    dest: "str | Path",
) -> Path:
    """Save the page with class-colored boxes, labels, and a mask tint overlay."""

    import cv2
    import numpy as np
    from PIL import Image

    canvas = np.ascontiguousarray(image.copy())
    if mask is not None:
        selected = mask.astype(bool)
        if selected.any():
            tint = np.zeros_like(canvas)
            tint[..., 0] = 255  # red tint over masked text
            canvas[selected] = (0.5 * canvas[selected] + 0.5 * tint[selected]).astype(np.uint8)

    for region in regions:
        color = _CLASS_COLORS.get(region.cls, (255, 255, 0))
        x1, y1, x2, y2 = region.box
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        label = f"{region.cls} {region.conf:.2f}"
        cv2.putText(
            canvas, label, (x1, max(10, y1 - 3)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA,
        )

    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(canvas).save(str(dest_path))
    return dest_path
