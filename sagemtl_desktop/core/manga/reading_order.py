"""Stage 1b: reading order.

Pure-Python heuristic, no learned model and no heavy imports. Implements a
layered recursive cut in the spirit of the Kovanen & Aizawa / manga109
panel-order estimator:

  1. Try a horizontal cut (a clean vertical gap between regions) and recurse the
     resulting tiers top-to-bottom.
  2. Otherwise try a vertical cut and recurse the resulting columns: right-to-left
     for Japanese (RTL), left-to-right for Korean/Chinese/webtoons (LTR).
  3. If no clean gap exists (overlapping cluster), fall back to a banded sort:
     top-to-bottom, then right-to-left (JP) or left-to-right (others).

Without panel boxes the algorithm operates directly on text regions, which is a
best effort: a single tall panel with two stacked bubbles is indistinguishable
from two side-by-side panels using bubble boxes alone. Pass ``panels`` (from a
panel detector) for accurate multi-panel ordering; then regions are grouped by
panel first and ordered within each panel.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 4.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from .models import TextRegion

__all__ = ["sort", "is_rtl"]

Box = tuple[int, int, int, int]


def is_rtl(source_lang: str) -> bool:
    """Return True for right-to-left reading order (Japanese)."""

    lang = (source_lang or "").strip().lower()
    return lang.startswith("ja") or lang.startswith("jp")


def _center(box: Box) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def _split_by_gap(items: list, get_box: Callable[[Any], Box], axis: int) -> list[list]:
    """Split items into contiguous groups along an axis (0=x, 1=y).

    Groups are returned in increasing-coordinate order. A new group starts wherever
    there is a clean gap (no item spans across it). Returns a single group when no
    gap exists.
    """

    lo_idx, hi_idx = (0, 2) if axis == 0 else (1, 3)
    spans = sorted(
        items, key=lambda it: (get_box(it)[lo_idx], get_box(it)[hi_idx])
    )
    groups: list[list] = []
    current: list = [spans[0]]
    max_hi = get_box(spans[0])[hi_idx]
    for item in spans[1:]:
        box = get_box(item)
        if box[lo_idx] > max_hi:  # clean gap -> start a new group
            groups.append(current)
            current = [item]
        else:
            current.append(item)
        max_hi = max(max_hi, box[hi_idx])
    groups.append(current)
    return groups


def _order_items(items: list, rtl: bool, get_box: Callable[[Any], Box]) -> list:
    """Recursively order items in reading order via layered cuts."""

    if len(items) <= 1:
        return list(items)

    # Horizontal cut first -> tiers top-to-bottom.
    rows = _split_by_gap(items, get_box, axis=1)
    if len(rows) > 1:
        ordered: list = []
        for row in rows:
            ordered.extend(_order_items(row, rtl, get_box))
        return ordered

    # Vertical cut -> columns; right-to-left for JP, left-to-right otherwise.
    cols = _split_by_gap(items, get_box, axis=0)
    if len(cols) > 1:
        sequence = list(reversed(cols)) if rtl else cols
        ordered = []
        for col in sequence:
            ordered.extend(_order_items(col, rtl, get_box))
        return ordered

    # Overlapping cluster with no clean gap: banded fallback sort.
    def key(item: Any) -> tuple[float, float]:
        cx, cy = _center(get_box(item))
        return (cy, -cx if rtl else cx)

    return sorted(items, key=key)


def _box_of(panel: Any) -> Box:
    """Normalize a panel into an (x1, y1, x2, y2) box."""

    if hasattr(panel, "box"):
        box = panel.box
    elif isinstance(panel, dict):
        box = panel.get("box", panel)
    else:
        box = panel
    return (int(box[0]), int(box[1]), int(box[2]), int(box[3]))


def _overlap_area(a: Box, b: Box) -> float:
    ox = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    oy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return float(ox * oy)


def _best_panel(region: TextRegion, panels: list) -> Optional[Any]:
    """Choose the panel containing the region center, else the max-overlap panel."""

    cx, cy = _center(region.box)
    for panel in panels:
        px1, py1, px2, py2 = _box_of(panel)
        if px1 <= cx <= px2 and py1 <= cy <= py2:
            return panel
    best, best_area = None, 0.0
    for panel in panels:
        area = _overlap_area(region.box, _box_of(panel))
        if area > best_area:
            best, best_area = panel, area
    return best


def _sort_with_panels(regions: list[TextRegion], panels: list, rtl: bool) -> list[TextRegion]:
    ordered_panels = _order_items(list(panels), rtl, _box_of)
    buckets: dict[int, list[TextRegion]] = {id(p): [] for p in ordered_panels}
    leftovers: list[TextRegion] = []
    for region in regions:
        panel = _best_panel(region, ordered_panels)
        if panel is None:
            leftovers.append(region)
        else:
            buckets[id(panel)].append(region)

    ordered: list[TextRegion] = []
    for panel in ordered_panels:
        ordered.extend(_order_items(buckets[id(panel)], rtl, lambda r: r.box))
    if leftovers:
        ordered.extend(_order_items(leftovers, rtl, lambda r: r.box))
    return ordered


def sort(
    regions: Sequence[TextRegion],
    panels: Optional[Sequence] = None,
    source_lang: str = "ja",
) -> list[TextRegion]:
    """Return ``regions`` ordered for human reading.

    ``panels`` (optional) are panel boxes from a panel detector; when provided,
    regions are grouped by panel before ordering. ``source_lang`` selects RTL
    (Japanese) vs LTR (Korean/Chinese/webtoon) order.
    """

    region_list = list(regions)
    if not region_list:
        return []
    rtl = is_rtl(source_lang)
    if panels:
        return _sort_with_panels(region_list, list(panels), rtl)
    return _order_items(region_list, rtl, lambda r: r.box)
