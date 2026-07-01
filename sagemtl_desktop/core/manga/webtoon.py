"""Stage 6: webtoon / long-strip handling.

A webtoon is one image thousands of pixels tall; the page detector expects roughly
page-sized inputs, so a strip is cut into model-sized tiles, detected per tile, and
the detections are mapped back to global coordinates. Cuts are placed inside
blank/low-variance gutter bands so a bubble is never sliced across a seam
(ManhwaFormatter approach). When no clean gutter band is available near a needed
cut, the split falls back to cutting at the lowest-activity row in the window
(bubbles are high-variance, so the minimum lands between them where possible) and
the adjacent tiles overlap by ``overlap`` on both sides, so a bubble within the
overlap margin of a forced cut still appears whole in one tile; overlapping
detections are de-duplicated by IoU (det_rearrange_forward spirit). A bubble taller
than a tile cannot be kept whole and is split with overlap and de-duplicated.

All heavy imports (cv2, numpy) are lazy. See ``MANGA_MODULE_BUILD_SPEC.md`` 8.2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from .models import TextRegion

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np

__all__ = [
    "is_strip",
    "split",
    "restitch",
    "dedup_regions",
    "tiled_detect",
    "STRIP_ASPECT_RATIO",
    "DEFAULT_MAX_TILE_H",
]

STRIP_ASPECT_RATIO = 2.5
DEFAULT_MAX_TILE_H = 2000
_DEFAULT_MIN_TILE_H = 256
_DEFAULT_OVERLAP = 128
_DEFAULT_VAR_THRESHOLD = 4.0
_DEFAULT_MIN_BAND = 6


def is_strip(shape, ratio: float = STRIP_ASPECT_RATIO) -> bool:
    """True if an image is a tall vertical strip (height/width >= ratio)."""

    height, width = int(shape[0]), int(shape[1])
    return width > 0 and (height / width) >= ratio


def _gutter_centers(activity, var_threshold: float, min_band: int) -> list[int]:
    """Return the center row of each low-variance band >= min_band tall."""

    low = activity <= var_threshold
    centers: list[int] = []
    i, n = 0, len(low)
    while i < n:
        if low[i]:
            j = i
            while j < n and low[j]:
                j += 1
            if (j - i) >= min_band:
                centers.append((i + j) // 2)
            i = j
        else:
            i += 1
    return centers


def split(
    strip_rgb: "np.ndarray",
    *,
    max_tile_h: int = DEFAULT_MAX_TILE_H,
    min_tile_h: int = _DEFAULT_MIN_TILE_H,
    overlap: int = _DEFAULT_OVERLAP,
    var_threshold: float = _DEFAULT_VAR_THRESHOLD,
    min_band: int = _DEFAULT_MIN_BAND,
) -> "list[tuple[np.ndarray, int]]":
    """Split a tall strip into ``(tile, y_offset)`` chunks, cutting inside gutters."""

    import cv2
    import numpy as np

    height, width = strip_rgb.shape[:2]
    if height <= max_tile_h:
        return [(np.ascontiguousarray(strip_rgb.copy()), 0)]

    gray = cv2.cvtColor(strip_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    activity = gray.std(axis=1)
    centers = _gutter_centers(activity, var_threshold, min_band)

    cuts: list[tuple[int, bool]] = []  # (row, is_fallback)
    y = 0
    while height - y > max_tile_h:
        lo, hi = y + min_tile_h, y + max_tile_h
        candidates = [c for c in centers if lo <= c <= hi]
        if candidates:
            cuts.append((max(candidates), False))      # deepest gutter band <= max_tile_h
        else:
            # No gutter band: cut at the lowest-activity row in the window. Bubbles
            # are high-variance, so the minimum lands between them when any gap
            # exists (avoiding a bubble even when the gap is too thin to be a band).
            lo_c = max(lo, y + 1)
            hi_c = min(hi, height - 1)
            window = activity[lo_c:hi_c + 1]
            cut = lo_c + int(window.argmin()) if window.size else hi_c
            cuts.append((max(cut, y + 1), True))
        y = cuts[-1][0]

    tiles: "list[tuple[np.ndarray, int]]" = []
    start = 0
    for cut, fallback in cuts:
        # Fallback tiles overlap by `overlap` on BOTH sides of the cut so a bubble
        # near the seam survives whole in one tile; gutter cuts abut (lossless).
        end = min(height, cut + overlap) if fallback else cut
        tiles.append((np.ascontiguousarray(strip_rgb[start:end].copy()), start))
        start = max(0, cut - overlap) if fallback else cut
    tiles.append((np.ascontiguousarray(strip_rgb[start:height].copy()), start))
    return tiles


def restitch(tiles: "Sequence[tuple[np.ndarray, int]]", full_shape) -> "np.ndarray":
    """Reassemble processed ``(tile, y_offset)`` chunks into a full strip."""

    import numpy as np

    height, width = int(full_shape[0]), int(full_shape[1])
    out = np.zeros((height, width, 3), dtype=np.uint8)
    for tile, y in tiles:
        th = tile.shape[0]
        usable = min(th, height - y)
        if usable > 0:
            out[y:y + usable] = tile[:usable]
    return out


def _iou(a, b) -> float:
    ox = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    oy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ox * oy
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def dedup_regions(regions: Sequence[TextRegion], iou_threshold: float = 0.5) -> list[TextRegion]:
    """Drop near-duplicate regions (overlap from tile seams), keeping higher conf."""

    kept: list[TextRegion] = []
    for region in sorted(regions, key=lambda r: -r.conf):
        if all(_iou(region.box, k.box) < iou_threshold for k in kept):
            kept.append(region)
    return kept


def tiled_detect(detector, strip_rgb: "np.ndarray", **split_kwargs):
    """Detect across a strip by tiling, mapping boxes to global coords, de-duping.

    Returns ``(regions, full_page_text_mask)`` like ``Detector.detect``.
    """

    import numpy as np

    tiles = split(strip_rgb, **split_kwargs)
    all_regions: list[TextRegion] = []
    full_mask = np.zeros(strip_rgb.shape[:2], dtype=np.uint8)
    for tile, y in tiles:
        regions, mask = detector.detect(tile)
        for region in regions:
            x1, y1, x2, y2 = region.box
            region.box = (x1, y1 + y, x2, y2 + y)
            region.polygon = [(px, py + y) for px, py in region.polygon]
            all_regions.append(region)
        th = mask.shape[0]
        usable = min(th, full_mask.shape[0] - y)
        if usable > 0:
            full_mask[y:y + usable] = np.maximum(full_mask[y:y + usable], mask[:usable])
    return dedup_regions(all_regions), full_mask
