"""Tests for desktop UI localization catalog."""

from sagemtl_desktop.ui.i18n import tr


def test_i18n_returns_english_by_default():
    assert tr("en", "menu.file") == "&File"


def test_i18n_returns_spanish_translation():
    assert tr("es", "menu.file") == "&Archivo"


def test_i18n_falls_back_to_english_for_unknown_language():
    assert tr("xx", "menu.file") == "&File"


def test_i18n_supports_format_parameters():
    text = tr("es", "msg.ui_language_changed.body", language_name="Espanol")
    assert "Espanol" in text
