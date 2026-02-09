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
