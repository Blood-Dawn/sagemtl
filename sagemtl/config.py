"""Application configuration helpers.

This module provides a typed :class:`Settings` object describing the user
configuration for SageMTL along with helpers to load and persist the
``~/.sagemtl/config.toml`` file.  The configuration is intentionally tiny –
defaults for CLI commands, newline preferences and the preferred thread count –
but it centralises the state so both the CLI and the (optional) TUI can share
the same values.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Literal

import tomllib
from pydantic import BaseModel, ConfigDict, Field, ValidationError

__all__ = [
    "CONFIG_ENV_VAR",
    "Settings",
    "clear_config_cache",
    "default_config_path",
    "load_config",
    "resolve_newline",
    "save_config",
    "update_config",
]


CONFIG_ENV_VAR = "SAGEMTL_CONFIG"
"""Environment variable that overrides the config file location."""

_CONFIG_DIRNAME = ".sagemtl"
_CONFIG_FILENAME = "config.toml"


def _default_thread_count() -> int:
    cpu_count = os.cpu_count() or 0
    return max(1, cpu_count)


class Settings(BaseModel):
    """Global configuration for SageMTL."""

    newline_mode: Literal["lf", "crlf", "system", "preserve"] = "lf"
    """Preferred newline handling when writing files."""

    clean_input_path: str = "-"
    """Default ``--in`` value for ``sagemtl clean``."""

    clean_output_path: str | None = None
    """Default ``--out`` value for ``sagemtl clean`` (``None`` -> stdout)."""

    crawl_glob: str = "*.html"
    """Default ``--glob`` for ``sagemtl crawl-batch``."""

    crawl_outdir: str = "out"
    """Default ``--outdir`` for ``sagemtl crawl-batch``."""

    crawl_jsonl: bool = False
    """Default ``--jsonl`` flag for ``sagemtl crawl-batch``."""

    thread_count: int = Field(default_factory=_default_thread_count, ge=1)
    """Preferred thread/worker count for CPU heavy tasks."""

    desktop_source_lang: str = "auto"
    """Desktop default source language for translation jobs."""

    desktop_target_lang: str = "en"
    """Desktop default target language for translation jobs."""

    desktop_glossary_path: str | None = None
    """Desktop glossary CSV path loaded at startup."""

    desktop_translation_backend: Literal["argos", "googletrans", "echo"] = "argos"
    """Desktop translation backend selection."""

    desktop_max_chunk_size: int = Field(default=900, ge=100, le=5000)
    """Desktop translation chunk size in characters."""

    desktop_ui_language: str = "en"
    """Desktop UI language code."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    @property
    def newline(self) -> str | None:
        """Return the actual newline string implied by ``newline_mode``."""

        return resolve_newline(self.newline_mode)


_CONFIG_CACHE: Settings | None = None
_CONFIG_CACHE_PATH: Path | None = None


def default_config_path() -> Path:
    """Return the default path to the TOML configuration file."""

    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (Path.home() / _CONFIG_DIRNAME / _CONFIG_FILENAME).resolve()


def resolve_newline(mode: str) -> str | None:
    """Convert a newline mode into the newline parameter for ``Path.write_text``."""

    if mode == "lf":
        return "\n"
    if mode == "crlf":
        return "\r\n"
    if mode == "system":
        return os.linesep
    if mode == "preserve":
        return None
    raise ValueError(f"Unknown newline mode: {mode!r}")


def _parse_settings(data: Dict[str, Any]) -> Settings:
    try:
        return Settings.model_validate(data)
    except ValidationError as exc:
        cleaned = dict(data)
        for err in exc.errors():
            loc = err.get("loc")
            if not loc:
                continue
            key = loc[0]
            cleaned.pop(key, None)
        return Settings.model_validate(cleaned)


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides with SAGEMTL_ prefix.

    Environment variables can use __ to indicate nested keys.
    For example: SAGEMTL_THREAD_COUNT=4 or SAGEMTL_CLEAN__INPUT_PATH=/tmp/input
    """
    result = data.copy()

    for key, value in os.environ.items():
        if not key.startswith("SAGEMTL_"):
            continue

        # Remove prefix and convert to lowercase
        config_key = key[8:].lower()

        # Handle nested keys with __ separator
        if "__" in config_key:
            # For now, we'll flatten it (future enhancement for nested dicts)
            config_key = config_key.replace("__", "_")

        # Try to parse as JSON first, fall back to string
        try:
            parsed_value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            # Try to infer the type
            if value.lower() in ("true", "false"):
                parsed_value = value.lower() == "true"
            elif value.isdigit():
                parsed_value = int(value)
            else:
                parsed_value = value

        result[config_key] = parsed_value

    return result


def load_config(
    path: str | Path | None = None,
    *,
    use_cache: bool = True,
) -> Settings:
    """Load :class:`Settings` from disk and apply environment overrides."""

    global _CONFIG_CACHE, _CONFIG_CACHE_PATH

    cfg_path = Path(path).expanduser().resolve() if path else default_config_path()

    if use_cache and _CONFIG_CACHE is not None and cfg_path == _CONFIG_CACHE_PATH:
        return _CONFIG_CACHE

    data: dict[str, Any] = {}
    if cfg_path.exists():
        try:
            with cfg_path.open("rb") as fh:
                data = tomllib.load(fh)
        except (tomllib.TOMLDecodeError, OSError):
            data = {}

    # Apply environment variable overrides
    data = _apply_env_overrides(data)

    settings = _parse_settings(data)

    if use_cache:
        _CONFIG_CACHE = settings
        _CONFIG_CACHE_PATH = cfg_path

    return settings


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    raise TypeError(f"Unsupported config value type: {type(value)!r}")


def _iter_dump_items(settings: Settings) -> Iterable[tuple[str, Any]]:
    for key, value in settings.model_dump().items():
        if value is None:
            continue
        yield key, value


def save_config(
    settings: Settings | None = None,
    path: str | Path | None = None,
) -> Path:
    """Persist the provided settings to disk and update the cache."""

    global _CONFIG_CACHE, _CONFIG_CACHE_PATH

    cfg_path = Path(path).expanduser().resolve() if path else default_config_path()
    settings = settings or load_config(cfg_path)

    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Auto-generated by sagemtl – edit with care"]
    for key, value in sorted(_iter_dump_items(settings), key=lambda item: item[0]):
        lines.append(f"{key} = {_format_value(value)}")

    cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    _CONFIG_CACHE = settings
    _CONFIG_CACHE_PATH = cfg_path

    return cfg_path


def update_config(
    updates: Dict[str, Any],
    path: str | Path | None = None,
) -> Settings:
    """Apply ``updates`` to the stored settings and persist them immediately."""

    cfg_path = Path(path).expanduser().resolve() if path else default_config_path()
    current = load_config(cfg_path, use_cache=False)
    new_settings = current.model_copy(update=updates)
    save_config(new_settings, cfg_path)
    return new_settings


def clear_config_cache() -> None:
    """Clear the cached configuration so the next load hits the filesystem."""

    global _CONFIG_CACHE, _CONFIG_CACHE_PATH
    _CONFIG_CACHE = None
    _CONFIG_CACHE_PATH = None
