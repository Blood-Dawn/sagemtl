"""Phase 3 integration test: real offline translation with NO API key (m2m100).

Marked ``integration`` (downloads facebook/m2m100_1.2B). Run:
    python -m pytest tests/test_manga_translate_integration.py -m integration -v

Gate: an offline run translates CJK source text to coherent English with no API
key set, and glossary names appear verbatim. Source text here is controlled (the
full detect->ocr->translate chain is exercised end-to-end in Phase 5); this test
isolates the translation + glossary behavior deterministically.

CJK literals use \\u escapes to keep this file ASCII.
"""

from __future__ import annotations

import re

import pytest

from sagemtl_desktop.core.glossary_manager import GlossaryManager, GlossaryTerm
from sagemtl_desktop.core.manga import translate
from sagemtl_desktop.core.manga.models import TextRegion

pytestmark = pytest.mark.integration

# \u4eca\u65e5\u306f\u3044\u3044\u5929\u6c17\u3067\u3059\u306d\u3002 / \u4f50\u85e4\u3055\u3093\u3001\u304a\u306f\u3088\u3046\u3054\u3056\u3044\u307e\u3059\u3002 / \u4f60\u597d\u4e16\u754c
JP_WEATHER = "\u4eca\u65e5\u306f\u3044\u3044\u5929\u6c17\u3067\u3059\u306d\u3002"
JP_SATO = "\u4f50\u85e4\u3055\u3093\u3001\u304a\u306f\u3088\u3046\u3054\u3056\u3044\u307e\u3059\u3002"
ZH_HELLO = "\u4f60\u597d\u4e16\u754c"
SATO = "\u4f50\u85e4"

_CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]")


def _region(text, lang):
    return TextRegion(box=(0, 0, 10, 10), cls="text_bubble", lang=lang, source_text=text)


def test_offline_translation_no_key(tmp_path):
    try:
        engine = translate.M2M100Engine()
        # touch the model once so a download/runtime failure skips cleanly
        engine._ensure()
    except Exception as exc:  # pragma: no cover - network/model dependent
        pytest.skip(f"m2m100 unavailable: {exc}")

    gm = GlossaryManager(storage_dir=tmp_path / "glossaries")
    gm.add_novel_term("series-jp", GlossaryTerm(source=SATO, target="Sato", category="Character"))

    regions = [
        _region(JP_WEATHER, "ja"),
        _region(JP_SATO, "ja"),
        _region(ZH_HELLO, "zh"),
    ]
    out = translate.run(
        regions, source_lang="ja", target_lang="en",
        glossary=gm, series_id="series-jp", offline_engine=engine, mode="offline",
    )

    # Every region produced non-empty English (Latin letters, no residual CJK).
    for r in out:
        assert r.target_text, f"empty translation for {r.source_text!r}"
        assert re.search(r"[A-Za-z]", r.target_text), f"no English in {r.target_text!r}"
        assert not _CJK.search(r.target_text), f"residual CJK in {r.target_text!r}"

    # Coherent (not just Latin): m2m100 deterministically renders the weather line.
    # Guards against a regression to coherent-looking gibberish that still passes
    # the Latin/no-CJK checks above.
    assert "weather" in out[0].target_text.lower()

    # Glossary name appears verbatim in the region that contained it.
    assert "Sato" in out[1].target_text
