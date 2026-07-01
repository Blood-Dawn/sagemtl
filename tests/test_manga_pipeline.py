"""Phase 5 unit test: pipeline.process_page chains stages 1-5 correctly (no models).

Runs in the default suite (the heavy real-model end-to-end test is integration-only).
Stage functions are monkeypatched so the wiring itself is verified: which region
set goes to which stage, that typeset receives the CLEANED page, that translate
receives the page bytes, and that the PageResult carries PNG bytes + text.
"""

from __future__ import annotations

import numpy as np

from sagemtl_desktop.core.manga import detect, inpaint, ocr, translate, typeset, webtoon
from sagemtl_desktop.core.manga.models import MangaConfig, TextRegion
from sagemtl_desktop.core.manga.pipeline import MangaPipeline


def test_process_page_wires_stages(monkeypatch):
    page = np.full((100, 100, 3), 255, np.uint8)
    monkeypatch.setattr(detect, "load_image_rgb", lambda data: page)

    # 2 text regions + 1 non-text bubble (to prove inpaint gets ALL regions).
    text_a = TextRegion(box=(10, 10, 40, 40), cls="text_bubble")
    text_b = TextRegion(box=(50, 50, 80, 80), cls="text_free")
    bubble = TextRegion(box=(5, 5, 95, 95), cls="bubble")
    all_regions = [text_a, text_b, bubble]

    class FakeDetector:
        def detect(self, image):
            return all_regions, np.zeros((100, 100), np.uint8)

    calls: dict = {}

    def fake_ocr_run(regions, page_image, **kw):
        calls["ocr"] = list(regions)
        for r in regions:
            r.source_text = "src"
        return regions

    def fake_translate_run(regions, page_png=b"", **kw):
        calls["translate"] = list(regions)
        calls["translate_page_png"] = page_png
        for r in regions:
            r.target_text = "EN"
        return regions

    def fake_inpaint_run(rgb, regions, **kw):
        calls["inpaint_regions"] = list(regions)
        out = rgb.copy()
        out[:] = 200  # mark as "cleaned"
        return out

    def fake_typeset_render(clean, regions, **kw):
        calls["typeset"] = list(regions)
        calls["typeset_clean_mean"] = int(clean.mean())
        return clean

    monkeypatch.setattr(ocr, "run", fake_ocr_run)
    monkeypatch.setattr(translate, "run", fake_translate_run)
    monkeypatch.setattr(inpaint, "run", fake_inpaint_run)
    monkeypatch.setattr(typeset, "render", fake_typeset_render)

    pipe = MangaPipeline(MangaConfig(engine_mode="offline", target_lang="en"))
    pipe._detector = FakeDetector()

    result = pipe.process_page(b"rawbytes", source_lang="ja", page_index=3)

    # Text stages see only the 2 text regions; inpaint sees all 3 (for the mask).
    assert len(calls["ocr"]) == 2
    assert len(calls["translate"]) == 2
    assert len(calls["typeset"]) == 2
    assert len(calls["inpaint_regions"]) == 3

    # translate received the raw page bytes; typeset received the CLEANED page.
    assert calls["translate_page_png"] == b"rawbytes"
    assert calls["typeset_clean_mean"] == 200  # cleaned (200), not original (255)

    # PageResult shape: index, PNG bytes, ordered translated regions.
    assert result.index == 3
    assert result.clean_image[:8] == b"\x89PNG\r\n\x1a\n"
    assert result.rendered_image[:8] == b"\x89PNG\r\n\x1a\n"
    assert all(r.target_text == "EN" for r in result.regions)
    assert "detect" in result.debug["timings"]


def test_tall_strip_routes_through_tiled_detect(monkeypatch):
    tall = np.full((1500, 200, 3), 255, np.uint8)  # aspect ratio 7.5 -> strip
    monkeypatch.setattr(detect, "load_image_rgb", lambda data: tall)

    used = {"tiled": False, "single": False}

    def fake_tiled_detect(detector, strip, **kw):
        used["tiled"] = True
        return [TextRegion(box=(10, 10, 40, 40), cls="text_bubble")], np.zeros((1500, 200), np.uint8)

    monkeypatch.setattr(webtoon, "tiled_detect", fake_tiled_detect)
    monkeypatch.setattr(ocr, "run", lambda regions, page_image, **kw: regions)
    monkeypatch.setattr(translate, "run", lambda regions, **kw: regions)
    monkeypatch.setattr(inpaint, "run", lambda rgb, regions, **kw: rgb)
    monkeypatch.setattr(typeset, "render", lambda clean, regions, **kw: clean)

    pipe = MangaPipeline(MangaConfig(engine_mode="offline"))

    class FakeDetector:
        def detect(self, image):
            used["single"] = True
            return [], np.zeros((1500, 200), np.uint8)

    pipe._detector = FakeDetector()
    result = pipe.process_page(b"x", source_lang="ko", page_index=0)

    assert used["tiled"] is True
    assert used["single"] is False  # strip path bypassed the single-image detector
    assert result.debug["is_strip"] is True


def test_process_chapter_threads_rolling_summary(monkeypatch):
    page = np.full((50, 50, 3), 255, np.uint8)
    monkeypatch.setattr(detect, "load_image_rgb", lambda data: page)
    regions = [TextRegion(box=(0, 0, 10, 10), cls="text_bubble")]

    class FakeDetector:
        def detect(self, image):
            return list(regions), np.zeros((50, 50), np.uint8)

    seen = []

    def fake_translate_run(regs, page_png=b"", rolling_summary="", **kw):
        seen.append(rolling_summary)
        for r in regs:
            r.target_text = f"PAGE{len(seen)}"
        return regs

    monkeypatch.setattr(ocr, "run", lambda regs, img, **kw: regs)
    monkeypatch.setattr(translate, "run", fake_translate_run)
    monkeypatch.setattr(inpaint, "run", lambda rgb, regs, **kw: rgb)
    monkeypatch.setattr(typeset, "render", lambda clean, regs, **kw: clean)

    pipe = MangaPipeline(MangaConfig(engine_mode="offline"))
    pipe._detector = FakeDetector()
    pipe.process_chapter([b"p0", b"p1"])

    assert seen[0] == ""             # first page has no prior context
    assert "PAGE1" in seen[1]        # second page receives page 1's summary


def test_get_provider_is_none_offline_and_without_key(monkeypatch):
    monkeypatch.delenv("SAGEMTL_TEST_NO_KEY", raising=False)
    # offline mode -> no provider
    pipe = MangaPipeline(MangaConfig(engine_mode="offline"))
    assert pipe._get_provider("ja") is None
    # cloud mode but the API key env var is unset -> no provider (offline fallback)
    pipe2 = MangaPipeline(
        MangaConfig(engine_mode="cloud", cloud_provider="anthropic", cloud_api_key_env="SAGEMTL_TEST_NO_KEY")
    )
    assert pipe2._get_provider("ja") is None
