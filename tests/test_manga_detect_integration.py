"""Phase 1 integration tests: run the real ONNX detector on Tier A test images.

Marked ``integration`` (network + model download), deselected by default. Run:
    python -m pytest tests/test_manga_detect_integration.py -m integration -v

Test images are public-domain (spec 15.3 Tier A): A1 (JP) and A5 (KR). They are
downloaded once and cached under tests/manga/fixtures/ (gitignored).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

# Spec 15.3 Tier A (public domain).
A1_JP = (
    "A1_jp.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/9/94/"
    "Tagosaku_to_Mokube_no_Tokyo_Kenbutsu.jpg",
)
A5_KR = (
    "A5_kr.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/e/e5/"
    "Lee-do-yeong%27s_manhwa_Imitating_Others.jpg",
)

_UA = "SageMTL/0.1 (manga detector tests; kheivendhaiti@gmail.com)"
FIXTURES = Path(__file__).resolve().parent / "manga" / "fixtures"


def _fetch(name: str, url: str) -> bytes:
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


def _detect(name: str, url: str):
    from sagemtl_desktop.core.manga import reading_order
    from sagemtl_desktop.core.manga.detect import (
        Detector,
        default_debug_dir,
        load_image_rgb,
        save_debug_overlay,
    )

    data = _fetch(name, url)
    image = load_image_rgb(data)
    try:
        detector = Detector(conf_threshold=0.30)
        regions, mask = detector.detect(image)
    except Exception as exc:  # pragma: no cover - network/model dependent
        pytest.skip(f"detector unavailable (model download/runtime): {exc}")

    overlay = save_debug_overlay(
        image, regions, mask, default_debug_dir() / f"phase1_{Path(name).stem}.png"
    )
    return image, regions, mask, overlay, reading_order


def test_detector_jp_a1_lands_on_text():
    image, regions, mask, overlay, reading_order = _detect(*A1_JP)
    height, width = image.shape[:2]

    # Gate: rich JP page yields several regions covering the lettering.
    assert len(regions) >= 4
    text_regions = [r for r in regions if r.cls in ("text_bubble", "text_free")]
    assert text_regions, "expected at least one text region"

    # Every box is within image bounds.
    for r in regions:
        x1, y1, x2, y2 = r.box
        assert 0 <= x1 < x2 <= width
        assert 0 <= y1 < y2 <= height

    # Union text mask is non-empty and page-sized.
    assert mask.shape == (height, width)
    assert int(mask.max()) == 255

    # Reading order preserves the region set.
    ordered = reading_order.sort(text_regions, source_lang="ja")
    assert len(ordered) == len(text_regions)

    assert overlay.exists()


def test_detector_kr_a5_finds_text():
    image, regions, mask, overlay, reading_order = _detect(*A5_KR)
    height, width = image.shape[:2]

    # A5 is sparse, but the visible Hangul blocks must be detected AS TEXT
    # (a lone 'bubble' box with no text region must not satisfy the gate).
    text_regions = [r for r in regions if r.cls in ("text_bubble", "text_free")]
    assert len(text_regions) >= 2

    for r in regions:
        x1, y1, x2, y2 = r.box
        assert 0 <= x1 < x2 <= width
        assert 0 <= y1 < y2 <= height

    # Union text mask is non-empty and page-sized.
    assert mask.shape == (height, width)
    assert int(mask.max()) == 255

    ordered = reading_order.sort(text_regions, source_lang="ko")
    assert len(ordered) == len(text_regions)

    assert overlay.exists()
