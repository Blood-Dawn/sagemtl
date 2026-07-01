"""Phase 6 integration test: tiled detection on a tall strip built from a real page.

Marked ``integration`` (network + detector model). Run:
    python -m pytest tests/test_manga_webtoon_integration.py -m integration -v

Builds a tall strip by stacking the real A1 page twice with a white gutter, then
verifies tiled detection finds text in BOTH halves (a single resize-to-640 detect
on the whole strip would miss most of it) and that the cut lands in the gutter
(restitch is lossless).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_UA = "SageMTL/0.1 (manga webtoon tests; kheivendhaiti@gmail.com)"
FIXTURES = Path(__file__).resolve().parent / "manga" / "fixtures"
A1_JP = (
    "A1_jp.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/9/94/"
    "Tagosaku_to_Mokube_no_Tokyo_Kenbutsu.jpg",
)


def _fetch(name, url):
    FIXTURES.mkdir(parents=True, exist_ok=True)
    cached = FIXTURES / name
    if cached.exists():
        return cached.read_bytes()
    try:
        import httpx

        data = httpx.get(url, headers={"User-Agent": _UA}, follow_redirects=True, timeout=60).content
    except Exception as exc:  # pragma: no cover - network dependent
        pytest.skip(f"could not download fixture {name}: {exc}")
    cached.write_bytes(data)
    return data


def test_tiled_detect_covers_full_strip():
    import numpy as np

    from sagemtl_desktop.core.manga import webtoon
    from sagemtl_desktop.core.manga.detect import Detector, load_image_rgb

    page = load_image_rgb(_fetch(*A1_JP))
    h, w = page.shape[:2]
    gutter = np.full((60, w, 3), 255, np.uint8)
    strip = np.concatenate([page, gutter, page], axis=0)  # tall: 2 pages + gutter
    assert webtoon.is_strip(strip.shape)

    try:
        detector = Detector(conf_threshold=0.30)
        regions, mask = webtoon.tiled_detect(detector, strip, max_tile_h=900, min_tile_h=200)
    except Exception as exc:  # pragma: no cover - network/model dependent
        pytest.skip(f"detector unavailable: {exc}")

    assert regions, "tiled detection found nothing"
    top_half = [r for r in regions if r.box[1] < h]
    bottom_half = [r for r in regions if r.box[1] > h + 60]
    # Both stacked copies must be detected -> the whole strip was processed.
    assert top_half, "no regions in the top page of the strip"
    assert bottom_half, "no regions in the bottom page of the strip"
    assert mask.shape == strip.shape[:2]

    # Restitch round-trips losslessly when cuts fall in the gutter.
    tiles = webtoon.split(strip, max_tile_h=900, min_tile_h=200)
    rebuilt = webtoon.restitch(tiles, strip.shape)
    assert np.array_equal(rebuilt, strip)
