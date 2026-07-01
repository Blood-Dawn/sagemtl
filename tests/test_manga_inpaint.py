"""Phase 4 unit tests: mask build + flat-fill + inpaint routing (deterministic, no model)."""

from __future__ import annotations

import numpy as np

from sagemtl_desktop.core.manga import inpaint
from sagemtl_desktop.core.manga.models import TextRegion


def _white_page_with_text():
    """White page with a black 'text' block inside a text region box."""
    img = np.full((100, 200, 3), 255, np.uint8)
    img[40:60, 60:140] = 0  # black glyphs
    region = TextRegion(box=(50, 30, 150, 70), cls="text_bubble")
    return img, region


def test_build_mask_covers_text():
    img, region = _white_page_with_text()
    mask = inpaint.build_mask(img, [region], dilate=0)
    assert mask[50, 100] == 255          # inside the black text -> masked
    assert mask[31, 51] == 0             # white background near box corner -> not masked


def test_build_mask_dilation_expands():
    img, region = _white_page_with_text()
    tight = inpaint.build_mask(img, [region], dilate=0)
    grown = inpaint.build_mask(img, [region], dilate=4)
    assert int(grown.sum()) > int(tight.sum())


def test_run_flatfills_solid_bubble_no_residual_no_halo():
    img, region = _white_page_with_text()
    clean = inpaint.run(img, [region])
    erased = clean[40:60, 60:140]
    assert int(erased.min()) > 200       # no dark residual text
    assert float(erased.std()) < 5.0     # uniform fill, no halo


def test_run_ignores_non_text_classes():
    img = np.full((50, 50, 3), 255, np.uint8)
    img[10:20, 10:20] = 0
    region = TextRegion(box=(0, 0, 50, 50), cls="bubble")  # not a text class
    clean = inpaint.run(img, [region])
    assert np.array_equal(clean, img)


def test_run_uses_inpainter_for_text_over_art():
    rng = np.random.RandomState(0)
    img = rng.randint(0, 255, (80, 80, 3), dtype=np.uint8)  # noisy "artwork"
    region = TextRegion(box=(0, 0, 80, 80), cls="text_free")

    class FakeInpainter(inpaint.Inpainter):
        def __init__(self):
            self.called = False

        def inpaint(self, image_rgb, mask):
            self.called = True
            return image_rgb

    fake = FakeInpainter()
    inpaint.run(img, [region], inpainter=fake)
    assert fake.called


def test_run_inpaints_text_over_art_drops_ink():
    """The text-over-art half of the gate, end-to-end through run() with the real
    default ClassicalInpainter (deterministic, no model/network)."""
    import cv2

    rng = np.random.RandomState(1)
    img = rng.randint(90, 200, (120, 200, 3)).astype(np.uint8)  # high-variance artwork
    img[40:43, 20:180] = 5   # thin dark strokes (minority -> not a solid bubble)
    img[70:73, 20:180] = 5
    region = TextRegion(box=(10, 30, 190, 90), cls="text_free")

    mask = inpaint.build_mask(img, [region], dilate=2)
    x1, y1, x2, y2 = 10, 30, 190, 90
    # This crop must route to the inpaint branch, not flat-fill.
    assert not inpaint._is_solid_bubble(img[y1:y2, x1:x2], mask[y1:y2, x1:x2])

    gray_before = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    clean = inpaint.run(img, [region], mask=mask)
    gray_after = cv2.cvtColor(clean, cv2.COLOR_RGB2GRAY)
    selected = mask > 0
    before = float((gray_before[selected] < 100).mean())
    after = float((gray_after[selected] < 100).mean())
    assert before > 0.05
    assert after < before * 0.5  # ink removed by cv2.inpaint, not just routed


def test_is_solid_bubble():
    white = np.full((30, 30, 3), 255, np.uint8)
    glyph = np.zeros((30, 30), np.uint8)
    glyph[10:20, 10:20] = 255
    assert inpaint._is_solid_bubble(white, glyph) is True

    rng = np.random.RandomState(1)
    noisy = rng.randint(0, 255, (30, 30, 3), dtype=np.uint8)
    assert inpaint._is_solid_bubble(noisy, glyph) is False


def test_light_text_on_dark_polarity():
    img = np.zeros((60, 120, 3), np.uint8)   # black background
    img[20:40, 50:80] = 255                  # white 'text'
    region = TextRegion(box=(40, 10, 90, 50), cls="text_bubble")
    mask = inpaint.build_mask(img, [region], dilate=0)
    assert mask[30, 65] == 255               # light glyph on dark bg is masked


def test_classical_inpainter_changes_masked_area():
    img = np.full((40, 40, 3), 255, np.uint8)
    img[18:22, 10:30] = 0
    mask = np.zeros((40, 40), np.uint8)
    mask[16:24, 8:32] = 255
    out = inpaint.ClassicalInpainter().inpaint(img, mask)
    assert int(out[18:22, 10:30].min()) > 150  # the black line is inpainted away


def test_save_debug_sidebyside(tmp_path):
    a = np.zeros((10, 10, 3), np.uint8)
    b = np.full((10, 10, 3), 255, np.uint8)
    from PIL import Image

    path = inpaint.save_debug_sidebyside(a, b, tmp_path / "ba.png")
    assert path.exists()
    assert Image.open(path).size == (20, 10)  # width doubled (side by side)


def test_build_inpainter_selection():
    class Cfg:
        device = "cpu"

        def __init__(self, model):
            self.inpaint_model = model

    assert inpaint.build_inpainter(Cfg("dreMaz/AnimeMangaInpainting")) is not None
    assert isinstance(inpaint.build_inpainter(Cfg("dreMaz/AnimeMangaInpainting")), inpaint.LamaInpainter)
    assert inpaint.build_inpainter(Cfg("none")) is None
    assert inpaint.build_inpainter(None) is None
