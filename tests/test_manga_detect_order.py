"""Phase 1 unit tests: reading order heuristic + text mask (no model, no network)."""

from __future__ import annotations

from sagemtl_desktop.core.manga import reading_order
from sagemtl_desktop.core.manga.detect import build_text_mask
from sagemtl_desktop.core.manga.models import TextRegion


def _region(x1, y1, x2, y2, tag, cls="text_bubble"):
    return TextRegion(box=(x1, y1, x2, y2), cls=cls, source_text=tag)


def _tags(regions):
    return [r.source_text for r in regions]


# ---------------------------------------------------------------------------
# Reading order
# ---------------------------------------------------------------------------


def test_jp_two_panel_same_row_right_before_left():
    """The Phase 1 gate: a 2-panel JP page reads right-to-left."""
    left = _region(50, 50, 150, 150, "L")
    right = _region(550, 50, 650, 150, "R")
    ordered = reading_order.sort([left, right], source_lang="ja")
    assert _tags(ordered) == ["R", "L"]


def test_ko_two_panel_same_row_left_before_right():
    left = _region(50, 50, 150, 150, "L")
    right = _region(550, 50, 650, 150, "R")
    ordered = reading_order.sort([right, left], source_lang="ko")
    assert _tags(ordered) == ["L", "R"]


def test_jp_panel_aware_is_column_major():
    """With panel boxes, JP order is per-panel right-to-left, top-to-bottom inside."""
    panels = [(500, 0, 700, 400), (0, 0, 200, 400)]  # right panel, left panel
    r_top = _region(550, 40, 650, 140, "Rt")
    r_bot = _region(550, 250, 650, 350, "Rb")
    l_top = _region(40, 40, 140, 140, "Lt")
    l_bot = _region(40, 250, 140, 350, "Lb")
    ordered = reading_order.sort([l_bot, r_top, l_top, r_bot], panels=panels, source_lang="ja")
    assert _tags(ordered) == ["Rt", "Rb", "Lt", "Lb"]


def test_jp_two_tiers_no_panels_is_row_major():
    """Without panels, two tiers read top-to-bottom, right-to-left within a tier."""
    r_top = _region(550, 40, 650, 140, "Rt")
    r_bot = _region(550, 250, 650, 350, "Rb")
    l_top = _region(40, 40, 140, 140, "Lt")
    l_bot = _region(40, 250, 140, 350, "Lb")
    ordered = reading_order.sort([l_bot, r_top, l_top, r_bot], source_lang="ja")
    assert _tags(ordered) == ["Rt", "Lt", "Rb", "Lb"]


def test_webtoon_strip_orders_top_to_bottom():
    a = _region(0, 0, 100, 50, "A")
    b = _region(0, 200, 100, 250, "B")
    c = _region(0, 400, 100, 450, "C")
    ordered = reading_order.sort([c, a, b], source_lang="ko")
    assert _tags(ordered) == ["A", "B", "C"]


def test_empty_and_single():
    assert reading_order.sort([]) == []
    one = _region(0, 0, 10, 10, "only")
    assert _tags(reading_order.sort([one], source_lang="ja")) == ["only"]


def test_is_rtl():
    assert reading_order.is_rtl("ja") is True
    assert reading_order.is_rtl("jp") is True
    assert reading_order.is_rtl("ko") is False
    assert reading_order.is_rtl("zh") is False
    assert reading_order.is_rtl("") is False


# ---------------------------------------------------------------------------
# Text mask
# ---------------------------------------------------------------------------


def test_build_text_mask_covers_text_classes_only():
    regions = [
        _region(10, 10, 30, 30, "tb", cls="text_bubble"),
        _region(40, 40, 60, 60, "tf", cls="text_free"),
        _region(0, 0, 5, 5, "bub", cls="bubble"),  # excluded from text mask
    ]
    mask = build_text_mask(regions, (100, 100))
    assert mask.shape == (100, 100)
    assert mask[15, 15] == 255   # inside text_bubble
    assert mask[50, 50] == 255   # inside text_free
    assert mask[2, 2] == 0       # bubble class not in text mask
    assert mask[80, 80] == 0     # empty area


def test_build_text_mask_clips_out_of_bounds_boxes():
    regions = [_region(-20, -20, 9999, 9999, "huge", cls="text_free")]
    mask = build_text_mask(regions, (50, 40))
    assert mask.shape == (50, 40)
    assert int(mask.min()) == 255  # whole page covered, no index error
