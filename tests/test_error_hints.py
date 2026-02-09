"""Tests for actionable error hint generation."""

from sagemtl_desktop.ui.error_hints import build_actionable_error_text, get_error_recovery_hints


def test_error_hints_include_translation_install_steps():
    hints = get_error_recovery_hints(
        "Argos Translate is not installed",
        context="translation",
    )
    assert any("pip install argostranslate" in hint for hint in hints)


def test_error_hints_include_crawl_profile_guidance():
    hints = get_error_recovery_hints(
        "Request timed out while downloading chapter",
        context="crawl_download",
    )
    assert any("delay/retries" in hint for hint in hints)
    assert any("crawl profile" in hint for hint in hints)


def test_actionable_error_text_renders_steps():
    rendered = build_actionable_error_text(
        "Missing translation model",
        context="translation",
        max_hints=2,
    )
    assert "Suggested next steps" in rendered
    assert rendered.count("- ") == 2
