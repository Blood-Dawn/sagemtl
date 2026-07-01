"""Phase 6 unit tests: webtoon split / restitch / dedup (deterministic, no model)."""

from __future__ import annotations

import numpy as np

from sagemtl_desktop.core.manga import webtoon
from sagemtl_desktop.core.manga.models import TextRegion

# Bubble y-ranges on a synthetic tall strip; everything else is a white gutter.
BUBBLES = [(100, 200), (500, 600), (900, 1000), (1300, 1400)]
STRIP_H, STRIP_W = 1500, 200


def _make_strip():
    strip = np.full((STRIP_H, STRIP_W, 3), 255, np.uint8)
    for top, bottom in BUBBLES:
        strip[top:bottom, 50:150] = 0  # dark "bubble" content (high row variance)
    return strip


def test_is_strip():
    assert webtoon.is_strip((1500, 200)) is True
    assert webtoon.is_strip((800, 600)) is False
    assert webtoon.is_strip((0, 0)) is False


def test_split_never_cuts_through_a_bubble():
    strip = _make_strip()
    tiles = webtoon.split(strip, max_tile_h=400, min_tile_h=100)
    # Tile boundaries (y_offset of each tile after the first) are the cut rows.
    cut_rows = [y for _tile, y in tiles[1:]]
    assert cut_rows, "expected the strip to be split into multiple tiles"
    for cut in cut_rows:
        for top, bottom in BUBBLES:
            assert not (top < cut < bottom), f"cut {cut} falls inside bubble {(top, bottom)}"


def test_split_tiles_are_height_bounded():
    strip = _make_strip()
    tiles = webtoon.split(strip, max_tile_h=400, min_tile_h=100)
    # Fallback tiles can overlap by `overlap` on both sides of a cut.
    for tile, _y in tiles:
        assert tile.shape[0] <= 400 + 2 * webtoon._DEFAULT_OVERLAP


def test_restitch_is_lossless_for_gutter_cuts():
    strip = _make_strip()
    tiles = webtoon.split(strip, max_tile_h=400, min_tile_h=100)
    rebuilt = webtoon.restitch(tiles, strip.shape)
    assert np.array_equal(rebuilt, strip)


def test_split_short_image_single_tile():
    short = np.full((300, 200, 3), 255, np.uint8)
    tiles = webtoon.split(short, max_tile_h=400)
    assert len(tiles) == 1
    assert tiles[0][1] == 0


def test_split_overlap_fallback_produces_overlapping_tiles():
    # A fully dense strip (no low-variance rows) forces hard cuts; tiles must overlap.
    rng = np.random.RandomState(0)
    dense = rng.randint(0, 256, (1200, 200, 3), dtype=np.uint8)
    tiles = webtoon.split(dense, max_tile_h=400, min_tile_h=100, overlap=64)
    assert len(tiles) >= 3
    spans = [(y, y + t.shape[0]) for t, y in tiles]
    assert any(spans[i][1] > spans[i + 1][0] for i in range(len(spans) - 1))


def test_split_fallback_keeps_bubbles_whole_via_low_activity():
    # Bubbles separated by THIN 3px gaps -> no gutter BAND (min_band=6) -> fallback
    # path. The lowest-activity cut must land in a gap, so every bubble stays whole
    # in at least one tile (the gate: no bubble cut across a seam).
    h, w = 1300, 200
    strip = np.full((h, w, 3), 255, np.uint8)
    bubbles = [(50, 250), (253, 453), (456, 656), (659, 859), (862, 1062), (1065, 1265)]
    for top, bottom in bubbles:
        strip[top:bottom, 30:170] = 0
    tiles = webtoon.split(strip, max_tile_h=400, min_tile_h=100, overlap=20, min_band=6)
    assert len(tiles) >= 3  # actually split (fallback path exercised)
    for top, bottom in bubbles:
        whole = any(y <= top and (y + tile.shape[0]) >= bottom for tile, y in tiles)
        assert whole, f"bubble {(top, bottom)} was sliced across a seam"


def test_dedup_regions():
    a = TextRegion(box=(10, 10, 50, 50), conf=0.9)
    near_dup = TextRegion(box=(12, 11, 52, 49), conf=0.5)  # high overlap with a
    far = TextRegion(box=(200, 200, 240, 240), conf=0.8)
    kept = webtoon.dedup_regions([a, near_dup, far], iou_threshold=0.5)
    assert len(kept) == 2
    boxes = {r.box for r in kept}
    assert (10, 10, 50, 50) in boxes and (200, 200, 240, 240) in boxes


def test_tiled_detect_offsets_and_merges(monkeypatch):
    strip = _make_strip()

    class FakeDetector:
        def detect(self, tile):
            # one region near the top of every tile, in LOCAL coords
            region = TextRegion(box=(10, 5, 40, 25), cls="text_bubble", conf=0.9)
            mask = np.zeros(tile.shape[:2], np.uint8)
            mask[5:25, 10:40] = 255
            return [region], mask

    regions, mask = webtoon.tiled_detect(FakeDetector(), strip, max_tile_h=400, min_tile_h=100)
    # Each tile contributes one region; offsets make them globally distinct.
    assert len(regions) >= 3
    ys = sorted(r.box[1] for r in regions)
    assert ys[0] == 5            # first tile's region stays at the top
    assert max(ys) > 25          # later tiles offset downward into the strip
    assert mask.shape == strip.shape[:2]
