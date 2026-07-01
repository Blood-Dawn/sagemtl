"""Phase 2 unit tests: OCR routing + escalation + script detection (no models).

CJK sample strings use \\u escapes to keep this file ASCII.
"""

from __future__ import annotations

import numpy as np

from sagemtl_desktop.core.manga import ocr
from sagemtl_desktop.core.manga.models import TextRegion

JA = "\u3053\u3093\u306b\u3061\u306f"      # konnichiwa (hiragana)
KO = "\uc548\ub155\ud558\uc138\uc694"      # annyeonghaseyo (hangul)
ZH = "\u4f60\u597d\u4e16\u754c"            # ni hao shijie (han only)


class FakeEngine(ocr.OcrEngine):
    def __init__(self, name, text, conf=ocr._NO_CONF):
        self.name = name
        self._text = text
        self._conf = conf
        self.calls = 0

    def recognize(self, crop_rgb):
        self.calls += 1
        return ocr.OcrResult(text=self._text, conf=self._conf, engine=self.name)


def _page():
    return np.zeros((200, 200, 3), dtype=np.uint8)


def _region(lang="", cls="text_bubble", box=(10, 10, 60, 60)):
    return TextRegion(box=box, cls=cls, lang=lang)


# ---------------------------------------------------------------------------
# script detection + lang normalization
# ---------------------------------------------------------------------------


def test_detect_script():
    assert ocr.detect_script(JA) == "ja"
    assert ocr.detect_script(KO) == "ko"
    assert ocr.detect_script(ZH) == "zh"
    assert ocr.detect_script("hello world") == "en"
    assert ocr.detect_script("") == ""


def test_detect_script_prioritizes_kana_over_han():
    # Japanese mixes kanji (Han) with kana; must classify as ja, not zh.
    mixed = "\u79c1\u306f\u732b"  # watashi-wa-neko (kanji + kana)
    assert ocr.detect_script(mixed) == "ja"


def test_normalize_lang():
    assert ocr.normalize_lang("ja") == "ja"
    assert ocr.normalize_lang("jpn") == "ja"
    assert ocr.normalize_lang("ko") == "ko"
    assert ocr.normalize_lang("kr") == "ko"
    assert ocr.normalize_lang("zh-Hans") == "zh"
    assert ocr.normalize_lang("ch") == "zh"
    assert ocr.normalize_lang("en") == "en"
    assert ocr.normalize_lang("") == ""


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------


def test_routing_picks_engine_by_region_lang():
    ja, ko, zh = FakeEngine("ja", JA), FakeEngine("ko", KO), FakeEngine("zh", ZH)
    engines = {"ja": ja, "ko": ko, "zh": zh}
    regions = [_region(lang="ja"), _region(lang="ko"), _region(lang="zh")]
    out = ocr.run(regions, _page(), source_lang="auto", escalate=False, engines=engines)
    assert out[0].source_text == JA and ja.calls == 1
    assert out[1].source_text == KO and ko.calls == 1
    assert out[2].source_text == ZH and zh.calls == 1


def test_routing_falls_back_to_source_lang():
    ko = FakeEngine("ko", KO)
    engines = {"ko": ko}
    regions = [_region(lang="")]
    out = ocr.run(regions, _page(), source_lang="ko", escalate=False, engines=engines)
    assert out[0].source_text == KO
    assert ko.calls == 1


def test_lang_is_set_from_detected_script_when_unknown():
    # source 'auto' defaults routing to ja, but the recognized text is Korean,
    # so region.lang should be corrected to 'ko' from the output.
    ja = FakeEngine("ja", KO)
    out = ocr.run([_region(lang="")], _page(), source_lang="auto", escalate=False, engines={"ja": ja})
    assert out[0].lang == "ko"


# ---------------------------------------------------------------------------
# escalation
# ---------------------------------------------------------------------------


def test_escalates_on_empty_primary_result():
    primary = FakeEngine("ja", "")
    vlm = FakeEngine("vlm", JA)
    out = ocr.run([_region(lang="ja")], _page(), escalate=True, engines={"ja": primary}, vlm=vlm)
    assert out[0].source_text == JA
    assert vlm.calls == 1


def test_escalates_on_text_free_region():
    primary = FakeEngine("ja", "x")
    vlm = FakeEngine("vlm", JA)
    out = ocr.run(
        [_region(lang="ja", cls="text_free")], _page(), escalate=True,
        engines={"ja": primary}, vlm=vlm,
    )
    assert out[0].source_text == JA
    assert vlm.calls == 1


def test_escalates_on_low_confidence():
    primary = FakeEngine("zh", ZH, conf=0.30)  # below DEFAULT_CONF_THRESHOLD
    vlm = FakeEngine("vlm", ZH + ZH)
    out = ocr.run([_region(lang="zh")], _page(), escalate=True, engines={"zh": primary}, vlm=vlm)
    assert out[0].source_text == ZH + ZH
    assert vlm.calls == 1


def test_no_escalation_for_confident_bubble():
    primary = FakeEngine("zh", ZH, conf=0.95)
    vlm = FakeEngine("vlm", "SHOULD-NOT-BE-USED")
    out = ocr.run([_region(lang="zh")], _page(), escalate=True, engines={"zh": primary}, vlm=vlm)
    assert out[0].source_text == ZH
    assert vlm.calls == 0


def test_no_escalation_for_nonempty_noconf_bubble():
    # manga-ocr JP happy path: non-empty text, NO confidence score (_NO_CONF),
    # plain text_bubble. The _NO_CONF guard is the sole decider here, so this must
    # NOT escalate. Pins the invariant against a regression that treats the -1.0
    # sentinel as "low confidence" (which would escalate every JP region).
    primary = FakeEngine("ja", JA)  # default conf == _NO_CONF
    vlm = FakeEngine("vlm", "SHOULD-NOT-BE-USED")
    out = ocr.run([_region(lang="ja", cls="text_bubble")], _page(), escalate=True,
                  engines={"ja": primary}, vlm=vlm)
    assert out[0].source_text == JA
    assert vlm.calls == 0


def test_escalation_disabled():
    primary = FakeEngine("ja", "")
    vlm = FakeEngine("vlm", JA)
    out = ocr.run([_region(lang="ja", cls="text_free")], _page(), escalate=False,
                  engines={"ja": primary}, vlm=vlm)
    assert out[0].source_text == ""
    assert vlm.calls == 0


# ---------------------------------------------------------------------------
# misc
# ---------------------------------------------------------------------------


def test_degenerate_box_yields_empty_text():
    primary = FakeEngine("ja", JA)
    out = ocr.run([_region(lang="ja", box=(10, 10, 10, 10))], _page(), escalate=False,
                  engines={"ja": primary})
    assert out[0].source_text == ""
    assert primary.calls == 0


def test_build_engine_selects_by_config():
    class Cfg:
        cjk_ocr_engine = "easyocr"

    assert isinstance(ocr.build_engine("ja"), ocr.MangaOcrEngine)
    assert isinstance(ocr.build_engine("zh"), ocr.PaddleOcrEngine)
    assert isinstance(ocr.build_engine("ko", Cfg()), ocr.EasyOcrEngine)
