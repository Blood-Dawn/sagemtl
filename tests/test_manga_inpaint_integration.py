"""Phase 4 integration test: erase text on the real JP page A1 (network + detector model).

Marked ``integration``. Run:
    python -m pytest tests/test_manga_inpaint_integration.py -m integration -v

Gate: the cleaned page has no residual text (dark glyph coverage inside the mask
drops sharply) and a before/after debug image is saved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_UA = "SageMTL/0.1 (manga inpaint tests; kheivendhaiti@gmail.com)"
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


def test_inpaint_removes_text_on_a1():
    import cv2
    import numpy as np

    from sagemtl_desktop.core.manga import inpaint
    from sagemtl_desktop.core.manga.detect import Detector, default_debug_dir, load_image_rgb

    image = load_image_rgb(_fetch(*A1_JP))
    try:
        regions, _ = Detector(conf_threshold=0.30).detect(image)
    except Exception as exc:  # pragma: no cover - network/model dependent
        pytest.skip(f"detector unavailable: {exc}")

    mask = inpaint.build_mask(image, regions)
    assert int(mask.max()) == 255, "mask should cover some text"

    clean = inpaint.run(image, regions, mask=mask)
    assert clean.shape == image.shape

    gray_before = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    gray_after = cv2.cvtColor(clean, cv2.COLOR_RGB2GRAY)
    selected = mask > 0
    before_dark = float((gray_before[selected] < 100).mean())
    after_dark = float((gray_after[selected] < 100).mean())

    # Text ink inside the mask should drop sharply after erasing.
    assert before_dark > 0.05, "expected dark glyph ink inside the mask before erasing"
    assert after_dark < before_dark * 0.5, (
        f"residual text: dark fraction {after_dark:.3f} vs before {before_dark:.3f}"
    )
    # The page actually changed where the mask is set.
    assert not np.array_equal(clean[selected], image[selected])

    out = inpaint.save_debug_sidebyside(image, clean, default_debug_dir() / "phase4_A1_before_after.png")
    assert out.exists()
