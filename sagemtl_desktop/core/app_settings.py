"""Desktop settings bridge backed by shared ``sagemtl.config.Settings``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from sagemtl.config import load_config, update_config

if TYPE_CHECKING:  # pragma: no cover - typing only; keeps manga import lazy
    from sagemtl_desktop.core.manga.models import MangaConfig


_VALID_BACKENDS = {"argos", "googletrans", "echo"}
_VALID_UI_LANGUAGES = {"en", "es"}

# Manga config enum validation sets (spec 12).
_VALID_ENGINE_MODES = {"offline", "hybrid", "cloud"}
_VALID_CLOUD_PROVIDERS = {"anthropic", "google", "openai", "none"}
_VALID_DEVICES = {"auto", "cpu", "cuda"}
_VALID_CJK_OCR_ENGINES = {"paddleocr", "easyocr"}


@dataclass(slots=True)
class DesktopAppSettings:
    """Desktop-facing subset of the shared config model."""

    source_lang: str = "auto"
    target_lang: str = "en"
    glossary_path: str | None = None
    translation_backend: str = "argos"
    max_chunk_size: int = 900
    ui_language: str = "en"


class DesktopSettingsStore:
    """Load/save desktop settings through the shared TOML config."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path).expanduser().resolve() if config_path else None

    def load(self) -> DesktopAppSettings:
        config = load_config(self._config_path, use_cache=False)
        return self._from_config(config)

    def save(self, settings: DesktopAppSettings) -> DesktopAppSettings:
        normalized = self._normalize(settings)
        updated = update_config(
            {
                "desktop_source_lang": normalized.source_lang,
                "desktop_target_lang": normalized.target_lang,
                "desktop_glossary_path": normalized.glossary_path,
                "desktop_translation_backend": normalized.translation_backend,
                "desktop_max_chunk_size": normalized.max_chunk_size,
                "desktop_ui_language": normalized.ui_language,
            },
            self._config_path,
        )
        return self._from_config(updated)

    def load_manga(self) -> "MangaConfig":
        """Load the manga configuration from the shared TOML config."""

        config = load_config(self._config_path, use_cache=False)
        return self._manga_from_config(config)

    def save_manga(self, settings: "MangaConfig") -> "MangaConfig":
        """Persist the manga configuration (API keys are never stored)."""

        normalized = self._normalize_manga(settings)
        updated = update_config(
            {
                "manga_engine_mode": normalized.engine_mode,
                "manga_target_lang": normalized.target_lang,
                "manga_source_lang": normalized.source_lang,
                "manga_detector_model": normalized.detector_model,
                "manga_ja_ocr_model": normalized.ja_ocr_model,
                "manga_cjk_ocr_engine": normalized.cjk_ocr_engine,
                "manga_ocr_vlm_model": normalized.ocr_vlm_model,
                "manga_inpaint_model": normalized.inpaint_model,
                "manga_offline_mt_model": normalized.offline_mt_model,
                "manga_cloud_provider": normalized.cloud_provider,
                "manga_cloud_model": normalized.cloud_model,
                "manga_cloud_api_key_env": normalized.cloud_api_key_env,
                "manga_cost_ceiling_usd_per_chapter": normalized.cost_ceiling_usd_per_chapter,
                "manga_font_path": normalized.font_path,
                "manga_enable_vertical_cjk": normalized.enable_vertical_cjk,
                "manga_device": normalized.device,
                "manga_suwayomi_url": normalized.suwayomi_url,
                "manga_suwayomi_source_id": normalized.suwayomi_source_id,
            },
            self._config_path,
        )
        return self._manga_from_config(updated)

    @staticmethod
    def _manga_from_config(config) -> "MangaConfig":
        from sagemtl_desktop.core.manga.models import MangaConfig

        engine_mode = (
            config.manga_engine_mode
            if config.manga_engine_mode in _VALID_ENGINE_MODES
            else "hybrid"
        )
        cjk_ocr_engine = (
            config.manga_cjk_ocr_engine
            if config.manga_cjk_ocr_engine in _VALID_CJK_OCR_ENGINES
            else "paddleocr"
        )
        cloud_provider = (
            config.manga_cloud_provider
            if config.manga_cloud_provider in _VALID_CLOUD_PROVIDERS
            else "anthropic"
        )
        device = config.manga_device if config.manga_device in _VALID_DEVICES else "auto"

        return MangaConfig(
            engine_mode=engine_mode,
            target_lang=(config.manga_target_lang or "en").strip() or "en",
            source_lang=(config.manga_source_lang or "auto").strip() or "auto",
            detector_model=config.manga_detector_model,
            ja_ocr_model=config.manga_ja_ocr_model,
            cjk_ocr_engine=cjk_ocr_engine,
            ocr_vlm_model=config.manga_ocr_vlm_model,
            inpaint_model=config.manga_inpaint_model,
            offline_mt_model=config.manga_offline_mt_model,
            cloud_provider=cloud_provider,
            cloud_model=config.manga_cloud_model,
            cloud_api_key_env=config.manga_cloud_api_key_env,
            cost_ceiling_usd_per_chapter=max(0.0, float(config.manga_cost_ceiling_usd_per_chapter)),
            font_path=config.manga_font_path,
            enable_vertical_cjk=bool(config.manga_enable_vertical_cjk),
            device=device,
            suwayomi_url=(config.manga_suwayomi_url or "").strip(),
            suwayomi_source_id=(config.manga_suwayomi_source_id or "").strip(),
        )

    @staticmethod
    def _normalize_manga(settings: "MangaConfig") -> "MangaConfig":
        from sagemtl_desktop.core.manga.models import MangaConfig

        engine_mode = (
            settings.engine_mode if settings.engine_mode in _VALID_ENGINE_MODES else "hybrid"
        )
        cjk_ocr_engine = (
            settings.cjk_ocr_engine
            if settings.cjk_ocr_engine in _VALID_CJK_OCR_ENGINES
            else "paddleocr"
        )
        cloud_provider = (
            settings.cloud_provider
            if settings.cloud_provider in _VALID_CLOUD_PROVIDERS
            else "anthropic"
        )
        device = settings.device if settings.device in _VALID_DEVICES else "auto"

        return MangaConfig(
            engine_mode=engine_mode,
            target_lang=(settings.target_lang or "en").strip() or "en",
            source_lang=(settings.source_lang or "auto").strip() or "auto",
            detector_model=(settings.detector_model or "").strip()
            or "ogkalu/comic-text-and-bubble-detector",
            ja_ocr_model=(settings.ja_ocr_model or "").strip() or "kha-white/manga-ocr-base",
            cjk_ocr_engine=cjk_ocr_engine,
            ocr_vlm_model=(settings.ocr_vlm_model or "").strip() or "PaddlePaddle/PaddleOCR-VL",
            inpaint_model=(settings.inpaint_model or "").strip() or "dreMaz/AnimeMangaInpainting",
            offline_mt_model=(settings.offline_mt_model or "").strip()
            or "haoranxu/X-ALMA-13B-Group6",
            cloud_provider=cloud_provider,
            cloud_model=(settings.cloud_model or "").strip() or "claude-sonnet-4-6",
            cloud_api_key_env=(settings.cloud_api_key_env or "").strip() or "ANTHROPIC_API_KEY",
            cost_ceiling_usd_per_chapter=max(0.0, float(settings.cost_ceiling_usd_per_chapter or 0.0)),
            font_path=(settings.font_path or "").strip()
            or "core/manga/fonts/ComicNeue-Bold.ttf",
            enable_vertical_cjk=bool(settings.enable_vertical_cjk),
            device=device,
            suwayomi_url=(settings.suwayomi_url or "").strip(),
            suwayomi_source_id=(settings.suwayomi_source_id or "").strip(),
        )

    @staticmethod
    def _from_config(config) -> DesktopAppSettings:
        return DesktopAppSettings(
            source_lang=(config.desktop_source_lang or "auto").strip() or "auto",
            target_lang=(config.desktop_target_lang or "en").strip() or "en",
            glossary_path=(config.desktop_glossary_path or None),
            translation_backend=(
                config.desktop_translation_backend
                if config.desktop_translation_backend in _VALID_BACKENDS
                else "argos"
            ),
            max_chunk_size=max(100, min(5000, int(config.desktop_max_chunk_size))),
            ui_language=(
                config.desktop_ui_language
                if config.desktop_ui_language in _VALID_UI_LANGUAGES
                else "en"
            ),
        )

    @staticmethod
    def _normalize(settings: DesktopAppSettings) -> DesktopAppSettings:
        source_lang = (settings.source_lang or "auto").strip() or "auto"
        target_lang = (settings.target_lang or "en").strip() or "en"
        glossary_path = (settings.glossary_path or "").strip() or None
        translation_backend = (
            settings.translation_backend
            if settings.translation_backend in _VALID_BACKENDS
            else "argos"
        )
        max_chunk_size = max(100, min(5000, int(settings.max_chunk_size or 900)))
        ui_language = settings.ui_language if settings.ui_language in _VALID_UI_LANGUAGES else "en"

        return DesktopAppSettings(
            source_lang=source_lang,
            target_lang=target_lang,
            glossary_path=glossary_path,
            translation_backend=translation_backend,
            max_chunk_size=max_chunk_size,
            ui_language=ui_language,
        )
