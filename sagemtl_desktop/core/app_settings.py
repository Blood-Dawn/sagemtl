"""Desktop settings bridge backed by shared ``sagemtl.config.Settings``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sagemtl.config import load_config, update_config


_VALID_BACKENDS = {"argos", "googletrans", "echo"}
_VALID_UI_LANGUAGES = {"en", "es"}


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
