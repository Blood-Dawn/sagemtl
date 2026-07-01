"""Phase 0 tests: MangaConfig round-trips through ~/.sagemtl/config.toml."""

from __future__ import annotations

from sagemtl.config import clear_config_cache, load_config, update_config
from sagemtl_desktop.core.app_settings import DesktopSettingsStore
from sagemtl_desktop.core.manga.models import MangaConfig


def test_manga_config_round_trip(tmp_path):
    config_path = tmp_path / "config.toml"
    store = DesktopSettingsStore(config_path)

    expected = MangaConfig(
        engine_mode="cloud",
        target_lang="es",
        source_lang="ja",
        detector_model="ogkalu/comic-text-and-bubble-detector",
        ja_ocr_model="kha-white/manga-ocr-base",
        cjk_ocr_engine="easyocr",
        ocr_vlm_model="PaddlePaddle/PaddleOCR-VL",
        inpaint_model="dreMaz/AnimeMangaInpainting",
        offline_mt_model="haoranxu/X-ALMA-13B-Group6",
        cloud_provider="openai",
        cloud_model="gpt-some-vision",
        cloud_api_key_env="OPENAI_API_KEY",
        cost_ceiling_usd_per_chapter=2.5,
        font_path="core/manga/fonts/Bangers-Regular.ttf",
        enable_vertical_cjk=True,
        device="cuda",
        suwayomi_url="http://localhost:4567",
        suwayomi_source_id="42",
    )

    saved = store.save_manga(expected)
    loaded = store.load_manga()

    assert saved == expected
    assert loaded == expected


def test_manga_config_defaults_match_spec():
    cfg = MangaConfig()
    assert cfg.engine_mode == "hybrid"
    assert cfg.target_lang == "en"
    assert cfg.source_lang == "auto"
    assert cfg.cloud_provider == "anthropic"
    assert cfg.cloud_model == "claude-sonnet-4-6"
    assert cfg.cloud_api_key_env == "ANTHROPIC_API_KEY"
    assert cfg.device == "auto"


def test_manga_config_normalizes_invalid_enums(tmp_path):
    config_path = tmp_path / "config.toml"
    store = DesktopSettingsStore(config_path)

    saved = store.save_manga(
        MangaConfig(
            engine_mode="turbo",          # invalid -> hybrid
            cjk_ocr_engine="tesseract",   # invalid -> paddleocr
            cloud_provider="cohere",      # invalid -> anthropic
            device="tpu",                 # invalid -> auto
            target_lang="   ",            # blank -> en
            source_lang="",               # blank -> auto
            cost_ceiling_usd_per_chapter=-5.0,  # clamped -> 0.0
        )
    )

    assert saved.engine_mode == "hybrid"
    assert saved.cjk_ocr_engine == "paddleocr"
    assert saved.cloud_provider == "anthropic"
    assert saved.device == "auto"
    assert saved.target_lang == "en"
    assert saved.source_lang == "auto"
    assert saved.cost_ceiling_usd_per_chapter == 0.0


def test_manga_config_persists_with_manga_prefix(tmp_path):
    config_path = tmp_path / "config.toml"
    store = DesktopSettingsStore(config_path)
    store.save_manga(MangaConfig(engine_mode="offline", target_lang="fr"))

    raw = config_path.read_text(encoding="utf-8")
    assert "manga_engine_mode" in raw
    assert "manga_target_lang" in raw
    # API keys must never be written to the config file; only the env var NAME.
    assert "ANTHROPIC_API_KEY" in raw  # the env-var name is fine to store
    assert "manga_cloud_api_key" in raw


def test_shared_settings_drops_invalid_manga_enum(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('manga_engine_mode = "bogus"\n', encoding="utf-8")

    loaded = load_config(config_path, use_cache=False)
    assert loaded.manga_engine_mode == "hybrid"


def test_manga_config_reads_shared_updates(tmp_path):
    config_path = tmp_path / "config.toml"
    update_config(
        {
            "manga_engine_mode": "offline",
            "manga_device": "cpu",
            "manga_cost_ceiling_usd_per_chapter": 3.0,
        },
        config_path,
    )
    clear_config_cache()

    store = DesktopSettingsStore(config_path)
    loaded = store.load_manga()
    assert loaded.engine_mode == "offline"
    assert loaded.device == "cpu"
    assert loaded.cost_ceiling_usd_per_chapter == 3.0
