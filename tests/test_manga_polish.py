"""Phase 10 unit tests: re-render speed, per-region caches, rolling summary."""

from __future__ import annotations

import io
import time

import numpy as np

from sagemtl_desktop.core.manga import jobs, ocr, translate
from sagemtl_desktop.core.manga.models import PageResult, TextRegion
from sagemtl_desktop.core.manga.pipeline import _summarize_page


def _clean_png(color=(255, 255, 255), size=(300, 200)):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


# --- re-render (the Phase 10 gate) ---


def test_rerender_page_is_fast_and_draws_edits():
    clean_png = _clean_png()
    from PIL import Image

    base = np.asarray(Image.open(io.BytesIO(clean_png)).convert("RGB"))
    regions = [TextRegion(box=(50, 40, 250, 160), cls="text_bubble", target_text="Hello world")]

    start = time.perf_counter()
    out = jobs.rerender_page(clean_png, regions, target_lang="en")
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"re-render took {elapsed:.2f}s (gate: < 1s)"
    assert out[:8] == b"\x89PNG\r\n\x1a\n"
    rendered = np.asarray(Image.open(io.BytesIO(out)).convert("RGB"))
    assert not np.array_equal(rendered, base)  # text was drawn


def test_rerender_reflects_edited_text():
    clean_png = _clean_png()
    empty = jobs.rerender_page(clean_png, [TextRegion(box=(50, 40, 250, 160), cls="text_bubble", target_text="")])
    edited = jobs.rerender_page(clean_png, [TextRegion(box=(50, 40, 250, 160), cls="text_bubble", target_text="Now has text")])
    assert empty != edited  # editing the translation changes the render


# --- per-region caches ---


class CountingOcr(ocr.OcrEngine):
    name = "counting"

    def __init__(self):
        self.calls = 0

    def recognize(self, crop_rgb):
        self.calls += 1
        return ocr.OcrResult("X", ocr._NO_CONF, "counting")


def test_ocr_cache_avoids_recompute():
    page = np.zeros((50, 50, 3), np.uint8)
    engine = CountingOcr()
    cache: dict = {}
    region = TextRegion(box=(0, 0, 20, 20), cls="text_bubble", lang="ja")
    ocr.run([region], page, escalate=False, engines={"ja": engine}, cache=cache)
    assert engine.calls == 1
    again = TextRegion(box=(0, 0, 20, 20), cls="text_bubble", lang="ja")
    ocr.run([again], page, escalate=False, engines={"ja": engine}, cache=cache)
    assert engine.calls == 1          # identical crop -> served from cache
    assert again.source_text == "X"

    # Two different-SHAPED crops with byte-identical flat buffers (both 4*6*3 ==
    # 6*4*3 == 72 zero bytes) must NOT collide -- the key includes the shape.
    wide = TextRegion(box=(0, 0, 6, 4), cls="text_bubble", lang="ja")   # (4,6,3) crop
    tall = TextRegion(box=(0, 0, 4, 6), cls="text_bubble", lang="ja")   # (6,4,3) crop
    ocr.run([wide], page, escalate=False, engines={"ja": engine}, cache=cache)
    assert engine.calls == 2
    ocr.run([tall], page, escalate=False, engines={"ja": engine}, cache=cache)
    assert engine.calls == 3          # distinct shape -> recomputed, no collision


class CountingMt(translate.TranslateEngine):
    name = "counting"

    def __init__(self):
        self.calls = 0

    def translate(self, text, src_lang, tgt_lang):
        self.calls += 1
        return "EN:" + text


def test_translate_cache_avoids_recompute():
    engine = CountingMt()
    cache: dict = {}
    region = TextRegion(box=(0, 0, 1, 1), cls="text_bubble", lang="ja", source_text="abc")
    translate.run([region], mode="offline", offline_engine=engine, cache=cache)
    assert engine.calls == 1 and region.target_text == "EN:abc"
    again = TextRegion(box=(0, 0, 1, 1), cls="text_bubble", lang="ja", source_text="abc")
    translate.run([again], mode="offline", offline_engine=engine, cache=cache)
    assert engine.calls == 1          # identical source -> served from cache
    assert again.target_text == "EN:abc"


# --- rolling summary ---


def test_summarize_page():
    result = PageResult(
        index=0,
        regions=[
            TextRegion(box=(0, 0, 1, 1), target_text="Hello"),
            TextRegion(box=(0, 0, 1, 1), target_text="World"),
        ],
    )
    assert _summarize_page(result) == "Hello World"
    long = PageResult(index=0, regions=[TextRegion(box=(0, 0, 1, 1), target_text="x" * 1000)])
    assert len(_summarize_page(long, max_chars=400)) == 400
