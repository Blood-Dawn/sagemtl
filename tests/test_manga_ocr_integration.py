"""Phase 2 integration tests: real routed OCR on Tier A images (network + models).

Marked ``integration`` (deselected by default). Run:
    python -m pytest tests/test_manga_ocr_integration.py -m integration -v

Gate (spec/tasklist Phase 2): >= 80% of detected text regions return non-empty
text, and the recognized text is in the expected script.

Language fixtures:
    A1 (JP) -> manga-ocr
    A3 (ZH) -> PaddleOCR ch
    A6 (KR) -> PaddleOCR korean

A5 (KR, 233px) is intentionally NOT used for the OCR gate: at that resolution the
Hangul is below what any OCR can read (~33%). A6 is the higher-resolution Tier A
Korean image (spec 15.3) and is the proper OCR fixture. A5 remains the Phase 1
detection fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_UA = "SageMTL/0.1 (manga ocr tests; kheivendhaiti@gmail.com)"
FIXTURES = Path(__file__).resolve().parent / "manga" / "fixtures"

# (name, source_lang, url) -- spec 15.3 Tier A (public domain).
A1_JP = ("A1_jp.jpg", "ja",
         "https://upload.wikimedia.org/wikipedia/commons/9/94/"
         "Tagosaku_to_Mokube_no_Tokyo_Kenbutsu.jpg")
A3_ZH = ("A3_zh.jpg", "zh",
         "https://upload.wikimedia.org/wikipedia/commons/d/da/"
         "%E8%BF%9E%E7%8E%AF%E5%B9%B4%E7%94%BB_%E7%8E%89%E9%BA%92%E9%BA%9F_%E4%B9%8B%E5%9B%9B.jpg")
A6_KR = ("A6_kr.jpg", "ko",
         "https://upload.wikimedia.org/wikipedia/commons/b/b8/"
         "Manhwa-Yu.Gil-jun-Yahak-01.jpg")


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


def _run_ocr(name, lang, url):
    from sagemtl_desktop.core.manga import ocr
    from sagemtl_desktop.core.manga.detect import Detector, load_image_rgb

    image = load_image_rgb(_fetch(name, url))
    try:
        regions, _ = Detector(conf_threshold=0.30).detect(image)
        text_regions = [r for r in regions if r.cls in ("text_bubble", "text_free")]
        # escalate=False: verify the primary specialized engines meet the gate.
        ocr.run(text_regions, image, source_lang=lang, escalate=False)
    except Exception as exc:  # pragma: no cover - network/model dependent
        pytest.skip(f"OCR engine unavailable ({lang}): {exc}")
    return text_regions, ocr.detect_script


@pytest.mark.parametrize("name,lang,url", [A1_JP, A3_ZH, A6_KR], ids=["A1_jp", "A3_zh", "A6_kr"])
def test_ocr_meets_gate(name, lang, url):
    text_regions, detect_script = _run_ocr(name, lang, url)
    assert text_regions, "no text regions detected"

    nonempty = [r for r in text_regions if r.source_text.strip()]
    fraction = len(nonempty) / len(text_regions)
    assert fraction >= 0.80, (
        f"{name}: only {len(nonempty)}/{len(text_regions)} regions non-empty "
        f"({fraction:.0%}); gate requires >= 80%"
    )

    # Recognized text (page level) must be in the expected script.
    combined = " ".join(r.source_text for r in nonempty)
    assert detect_script(combined) == lang, (
        f"{name}: combined recognized script {detect_script(combined)!r} != {lang!r}"
    )

    # Per-region language was populated for non-empty regions.
    assert all(r.lang for r in nonempty)
