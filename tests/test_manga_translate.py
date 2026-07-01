"""Phase 3 unit tests: offline translation routing + glossary injection (no models).

CJK literals use \\u escapes to keep this file ASCII.
"""

from __future__ import annotations

from sagemtl_desktop.core.glossary_manager import GlossaryManager, GlossaryTerm
from sagemtl_desktop.core.manga import translate
from sagemtl_desktop.core.manga.models import TextRegion

SATO = "\u4f50\u85e4"                       # name in Han
SATO_SENT = SATO + "\u3055\u3093"           # name + honorific (kana)


def _region(text, lang="ja", cls="text_bubble"):
    return TextRegion(box=(0, 0, 10, 10), cls=cls, lang=lang, source_text=text)


class EchoEngine(translate.TranslateEngine):
    name = "echo"

    def translate(self, text, src_lang, tgt_lang):
        return text


class TaggingEngine(translate.TranslateEngine):
    name = "tag"

    def __init__(self):
        self.calls = []

    def translate(self, text, src_lang, tgt_lang):
        self.calls.append((text, src_lang, tgt_lang))
        return "EN:" + text


class FakeLlm(translate.TranslateEngine):
    name = "fakellm"
    is_llm = True

    def __init__(self, outputs):
        self.outputs = outputs
        self.block = None

    def translate_block(self, texts, src_lang, tgt_lang, glossary_text=""):
        self.block = glossary_text
        return list(self.outputs)


class FakeProvider:
    def __init__(self, outputs):
        self.outputs = outputs
        self.args = None

    def translate_page(self, page_png, regions, glossary, target_lang, rolling_summary):
        self.args = (page_png, list(regions), list(glossary), target_lang, rolling_summary)
        return list(self.outputs)


def _glossary(tmp_path, series_id):
    gm = GlossaryManager(storage_dir=tmp_path / "glossaries")
    gm.add_novel_term(series_id, GlossaryTerm(source=SATO, target="Sato", category="Character"))
    return gm


# ---------------------------------------------------------------------------
# offline sentence-level
# ---------------------------------------------------------------------------


def test_offline_assigns_targets():
    engine = TaggingEngine()
    regions = [_region("a"), _region("b")]
    out = translate.run(regions, source_lang="ja", offline_engine=engine, mode="offline")
    assert [r.target_text for r in out] == ["EN:a", "EN:b"]
    assert len(engine.calls) == 2


def test_offline_empty_source_is_skipped():
    engine = TaggingEngine()
    out = translate.run([_region("")], offline_engine=engine, mode="offline")
    assert out[0].target_text == ""
    assert engine.calls == []


def test_offline_glossary_name_appears_verbatim(tmp_path):
    gm = _glossary(tmp_path, "series-1")
    out = translate.run(
        [_region(SATO_SENT)], glossary=gm, series_id="series-1",
        offline_engine=EchoEngine(), mode="offline",
    )
    # pre-applied glossary injects the target rendering into the source, so an
    # identity "translation" still surfaces the name verbatim.
    assert "Sato" in out[0].target_text
    assert SATO not in out[0].target_text


def test_offline_llm_path_uses_glossary_block(tmp_path):
    gm = _glossary(tmp_path, "series-1")
    engine = FakeLlm(["hello", "world"])
    out = translate.run(
        [_region("x"), _region("y")], glossary=gm, series_id="series-1",
        offline_engine=engine, mode="offline",
    )
    assert [r.target_text for r in out] == ["hello", "world"]
    assert "Sato" in engine.block  # glossary block passed to the LLM


# ---------------------------------------------------------------------------
# cloud delegation
# ---------------------------------------------------------------------------


def test_cloud_delegates_to_provider():
    provider = FakeProvider(["P0", "P1"])
    regions = [_region("a"), _region("b")]
    out = translate.run(regions, page_png=b"IMG", mode="cloud", provider=provider, target_lang="en")
    assert [r.target_text for r in out] == ["P0", "P1"]
    assert provider.args[0] == b"IMG"
    assert provider.args[3] == "en"


def test_cloud_output_is_glossary_postapplied(tmp_path):
    gm = _glossary(tmp_path, "series-1")
    provider = FakeProvider([SATO + " is here"])  # provider returned a raw source name
    out = translate.run(
        [_region("z")], mode="cloud", provider=provider, glossary=gm, series_id="series-1",
    )
    assert out[0].target_text == "Sato is here"


def test_cloud_result_length_is_fit_to_regions():
    provider = FakeProvider(["only-one"])  # fewer than regions
    out = translate.run([_region("a"), _region("b")], mode="cloud", provider=provider)
    assert [r.target_text for r in out] == ["only-one", ""]


# ---------------------------------------------------------------------------
# engine selection + LLM prompt helpers
# ---------------------------------------------------------------------------


def test_build_engine_selection():
    class Cfg:
        device = "cpu"

        def __init__(self, model):
            self.offline_mt_model = model

    assert isinstance(translate.build_engine(Cfg("facebook/m2m100_1.2B")), translate.M2M100Engine)
    assert isinstance(translate.build_engine(Cfg("argos")), translate.ArgosEngine)
    assert isinstance(translate.build_engine(Cfg("sugoitoolkit/Sugoi-14B-Ultra-GGUF")), translate.LlamaCppEngine)
    # heavy default (X-ALMA) is not auto-wired -> falls back to m2m100
    assert isinstance(translate.build_engine(Cfg("haoranxu/X-ALMA-13B-Group6")), translate.M2M100Engine)


def test_build_llm_prompt_and_parse_numbered():
    prompt = translate.build_llm_prompt(["aaa", "bbb"], "ja", "en", "X -> Y")
    assert "X -> Y" in prompt
    assert "1. aaa" in prompt and "2. bbb" in prompt

    assert translate.parse_numbered("1. Hello\n2. World", 2) == ["Hello", "World"]
    assert translate.parse_numbered("1. Only", 2) == ["Only", ""]
    assert translate.parse_numbered("2. Second\n1. First", 2) == ["First", "Second"]


def test_glossary_block_render(tmp_path):
    gm = _glossary(tmp_path, "series-1")
    block = translate.glossary_block(gm, "series-1")
    assert "Sato" in block and "->" in block


# ---------------------------------------------------------------------------
# wiring helpers (run by default; a real-model gate runs under -m integration)
# ---------------------------------------------------------------------------


def test_m2m_lang_mapping():
    assert translate._m2m_lang("ja") == "ja"
    assert translate._m2m_lang("jpn") == "ja"
    assert translate._m2m_lang("ko") == "ko"
    assert translate._m2m_lang("zh-Hans") == "zh"
    assert translate._m2m_lang("en") == "en"
    assert translate._m2m_lang("xx") == "ja"  # unknown -> default ja


def test_resolve_src_lang():
    assert translate._resolve_src_lang(_region("t", lang="ko"), "ja") == "ko"  # region wins
    assert translate._resolve_src_lang(_region("t", lang=""), "zh") == "zh"     # source_lang
    # 'auto' with no region lang -> detect from the source text (Hangul -> ko)
    assert translate._resolve_src_lang(_region("\uc548\ub155", lang=""), "auto") == "ko"


# ---------------------------------------------------------------------------
# mode routing
# ---------------------------------------------------------------------------


def test_hybrid_uses_offline_when_no_provider():
    engine = TaggingEngine()
    out = translate.run([_region("a")], mode="hybrid", offline_engine=engine)
    assert out[0].target_text == "EN:a"
    assert len(engine.calls) == 1


def test_hybrid_uses_provider_when_present():
    provider = FakeProvider(["P0"])
    engine = TaggingEngine()
    out = translate.run(
        [_region("a")], page_png=b"x", mode="hybrid", provider=provider, offline_engine=engine
    )
    assert out[0].target_text == "P0"
    assert engine.calls == []  # offline engine not used when a provider is present


def test_run_empty_regions_returns_empty():
    assert translate.run([], mode="offline", offline_engine=TaggingEngine()) == []
