"""Tests for shared desktop/CLI settings bridge."""

from sagemtl.config import clear_config_cache, load_config, update_config
from sagemtl_desktop.core.app_settings import DesktopAppSettings, DesktopSettingsStore


def test_desktop_settings_store_round_trip(tmp_path):
    config_path = tmp_path / "config.toml"
    store = DesktopSettingsStore(config_path)

    expected = DesktopAppSettings(
        source_lang="ja",
        target_lang="en",
        glossary_path=str(tmp_path / "glossary.csv"),
        translation_backend="echo",
        max_chunk_size=1400,
        ui_language="es",
    )

    saved = store.save(expected)
    loaded = store.load()

    assert saved == expected
    assert loaded == expected


def test_desktop_settings_store_reads_shared_updates(tmp_path):
    config_path = tmp_path / "config.toml"
    update_config(
        {
            "desktop_source_lang": "zh",
            "desktop_target_lang": "en",
            "desktop_translation_backend": "argos",
            "desktop_max_chunk_size": 1800,
            "desktop_ui_language": "en",
        },
        config_path,
    )
    clear_config_cache()

    store = DesktopSettingsStore(config_path)
    loaded = store.load()

    assert loaded.source_lang == "zh"
    assert loaded.target_lang == "en"
    assert loaded.translation_backend == "argos"
    assert loaded.max_chunk_size == 1800
    assert loaded.ui_language == "en"


def test_desktop_settings_store_normalizes_invalid_values(tmp_path):
    config_path = tmp_path / "config.toml"
    store = DesktopSettingsStore(config_path)

    saved = store.save(
        DesktopAppSettings(
            source_lang="",
            target_lang="",
            glossary_path="   ",
            translation_backend="not-a-backend",
            max_chunk_size=10,
            ui_language="de",
        )
    )

    assert saved.source_lang == "auto"
    assert saved.target_lang == "en"
    assert saved.glossary_path is None
    assert saved.translation_backend == "argos"
    assert saved.max_chunk_size == 100
    assert saved.ui_language == "en"


def test_shared_settings_model_falls_back_from_invalid_backend(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('desktop_translation_backend = "invalid"\n', encoding="utf-8")

    loaded = load_config(config_path, use_cache=False)
    assert loaded.desktop_translation_backend == "argos"
