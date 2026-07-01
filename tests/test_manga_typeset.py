"""Phase 5 unit tests: typeset fit/wrap/color/render (deterministic, no model)."""

from __future__ import annotations

import numpy as np

from sagemtl_desktop.core.manga import typeset
from sagemtl_desktop.core.manga.models import TextRegion
from sagemtl_desktop.core.manga.typeset import (
    DEFAULT_FONT_PATH,
    fit_text,
    render,
    resolve_font_path,
    wrap_text,
)


def test_default_font_exists():
    assert DEFAULT_FONT_PATH.is_file()


def test_resolve_font_path():
    assert resolve_font_path(None).endswith("ComicNeue-Bold.ttf")
    assert resolve_font_path("core/manga/fonts/ComicNeue-Bold.ttf").endswith("ComicNeue-Bold.ttf")
    assert resolve_font_path("/nope/missing.ttf").endswith("ComicNeue-Bold.ttf")  # fallback


def test_wrap_text_wraps_to_width():
    from PIL import ImageFont

    font = ImageFont.truetype(str(DEFAULT_FONT_PATH), 20)
    lines = wrap_text("one two three four five six", font, 60)
    assert len(lines) >= 2
    assert all(font.getlength(line) <= 60 for line in lines)


def test_fit_text_larger_box_gets_larger_font():
    fp = str(DEFAULT_FONT_PATH)
    small = fit_text("Hello", fp, 60, 30)[0]
    big = fit_text("Hello", fp, 300, 200)[0]
    assert big > small


def test_fit_text_wraps_long_text_within_width():
    fp = str(DEFAULT_FONT_PATH)
    size, lines, font = fit_text("the quick brown fox jumps over the lazy dog", fp, 120, 200)
    assert len(lines) >= 2
    assert all(font.getlength(line) <= 120 for line in lines)


def test_estimate_colors():
    white = np.full((10, 10, 3), 255, np.uint8)
    text, stroke = typeset._estimate_colors(white, (0, 0, 10, 10))
    assert text == (0, 0, 0) and stroke == (255, 255, 255)
    black = np.zeros((10, 10, 3), np.uint8)
    text, stroke = typeset._estimate_colors(black, (0, 0, 10, 10))
    assert text == (255, 255, 255) and stroke == (0, 0, 0)


def test_render_draws_text_within_box_no_overflow():
    clean = np.full((200, 300, 3), 255, np.uint8)
    region = TextRegion(
        box=(50, 40, 250, 160), cls="text_bubble",
        target_text="Hello there friend, this is a longer test sentence to wrap",
    )
    out = render(clean, [region])
    changed = np.any(out != clean, axis=2)
    ys, xs = np.where(changed)
    assert xs.size > 0, "expected text to be drawn"
    # All drawn pixels stay inside the region box -> no overflow (the gate).
    assert xs.min() >= 50 and xs.max() <= 250
    assert ys.min() >= 40 and ys.max() <= 160


def test_render_tiny_box_does_not_overflow():
    # Text that cannot fit even at min_font must be clipped to the box, not spill.
    clean = np.full((140, 140, 3), 255, np.uint8)
    region = TextRegion(
        box=(40, 50, 80, 70), cls="text_bubble",
        target_text="This is a very long sentence that cannot possibly fit in this tiny bubble",
    )
    out = render(clean, [region])
    changed = np.any(out != clean, axis=2)
    ys, xs = np.where(changed)
    assert xs.size > 0, "expected some text to be drawn"
    assert xs.min() >= 40 and xs.max() <= 80, "horizontal overflow outside the box"
    assert ys.min() >= 50 and ys.max() <= 70, "vertical overflow outside the box"


def test_render_empty_target_leaves_page_unchanged():
    clean = np.full((50, 50, 3), 255, np.uint8)
    region = TextRegion(box=(0, 0, 50, 50), cls="text_bubble", target_text="")
    out = render(clean, [region])
    assert np.array_equal(out, clean)


def test_render_skips_non_text_classes():
    clean = np.full((60, 60, 3), 255, np.uint8)
    region = TextRegion(box=(0, 0, 60, 60), cls="bubble", target_text="ignored")
    out = render(clean, [region])
    assert np.array_equal(out, clean)
