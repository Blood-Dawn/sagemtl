"""Tests for glossary manager regex caching behavior."""

from __future__ import annotations

from sagemtl_desktop.core.glossary_manager import GlossaryManager, GlossaryTerm
import sagemtl_desktop.core.glossary_manager as glossary_module


def test_regex_pattern_cache_reused_across_apply_calls(monkeypatch, tmp_path):
    manager = GlossaryManager(storage_dir=tmp_path / "glossaries")
    manager.add_global_term(
        GlossaryTerm(source="Sect Master", target="Patriarch", case_sensitive=False, word_boundary=True)
    )

    compile_calls = {"count": 0}
    original_compile = glossary_module.re.compile

    def counting_compile(pattern, flags=0):
        compile_calls["count"] += 1
        return original_compile(pattern, flags)

    monkeypatch.setattr(glossary_module.re, "compile", counting_compile)

    first = manager.apply_glossary("The Sect Master arrived.")
    second = manager.apply_glossary("A Sect Master should lead.")

    assert "Patriarch" in first
    assert "Patriarch" in second
    assert compile_calls["count"] == 1


def test_apply_glossary_cjk_terms_match_inside_contiguous_text(tmp_path):
    manager = GlossaryManager(storage_dir=tmp_path / "glossaries")
    manager.add_global_term(
        GlossaryTerm(source="云澈", target="Yun Che", case_sensitive=False, word_boundary=True)
    )

    # Regression: \b...\b does not match CJK in continuous text.
    assert manager.apply_glossary("云澈说道") == "Yun Che说道"


def test_word_boundary_still_protects_english_substrings(tmp_path):
    manager = GlossaryManager(storage_dir=tmp_path / "glossaries")
    manager.add_global_term(
        GlossaryTerm(source="Sect", target="Clan", case_sensitive=False, word_boundary=True)
    )

    assert manager.apply_glossary("The Sect leader.") == "The Clan leader."
    assert manager.apply_glossary("Section header") == "Section header"
