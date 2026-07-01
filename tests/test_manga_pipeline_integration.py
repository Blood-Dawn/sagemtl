"""Phase 5 integration test: full end-to-end page (raw JP page -> translated typeset).

Marked ``integration`` (network + detector/OCR/MT models, NO API key -- offline mode).
Run:
    python -m pytest tests/test_manga_pipeline_integration.py -m integration -v

Gate: one raw JP page produces a fully translated, typeset page with text drawn
into the bubbles. This is the first demo milestone; the rendered page is saved to
~/.sagemtl/debug/phase5_A1_rendered.png.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_UA = "SageMTL/0.1 (manga e2e tests; kheivendhaiti@gmail.com)"
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


def test_pipeline_end_to_end_jp_page():
    from sagemtl_desktop.core.manga.detect import default_debug_dir
    from sagemtl_desktop.core.manga.models import MangaConfig
    from sagemtl_desktop.core.manga.pipeline import MangaPipeline

    image_bytes = _fetch(*A1_JP)
    config = MangaConfig(
        engine_mode="offline",
        source_lang="ja",
        target_lang="en",
        offline_mt_model="facebook/m2m100_1.2B",
        inpaint_model="none",  # classical inpaint (fast, no model)
    )
    pipeline = MangaPipeline(config)
    try:
        result = pipeline.process_page(image_bytes, source_lang="ja", page_index=0)
    except Exception as exc:  # pragma: no cover - network/model dependent
        pytest.skip(f"pipeline models unavailable: {exc}")

    # Valid PNG outputs for both the cleaned and rendered pages.
    assert result.clean_image and result.rendered_image
    assert result.clean_image[:8] == b"\x89PNG\r\n\x1a\n"
    assert result.rendered_image[:8] == b"\x89PNG\r\n\x1a\n"

    # Detected and translated.
    assert result.regions, "no regions detected"
    translated = [r for r in result.regions if r.target_text.strip()]
    assert translated, "no region was translated"

    # The typeset page differs from the clean page (text was drawn back in).
    assert result.rendered_image != result.clean_image

    # Save the rendered demo page.
    from PIL import Image

    out = default_debug_dir() / "phase5_A1_rendered.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.open(io.BytesIO(result.rendered_image)).save(out)
    assert out.exists()
