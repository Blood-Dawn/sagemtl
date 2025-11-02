"""Glue code between the Textual UI and the persisted settings."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Iterable

from sagemtl.config import Settings, clear_config_cache, load_config, save_config

Listener = Callable[[Settings], None]

__all__ = ["SettingsController"]


class SettingsController:
    """Small helper used by the TUI settings tab.

    The controller provides a simple observer pattern that lets widgets update
    the configuration and get notified whenever new values are persisted.  It
    intentionally mirrors a minimal subset of what a full application might
    require so that tests can exercise the behaviour without pulling in a UI
    dependency.
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._path = Path(config_path).expanduser() if config_path else None
        self._listeners: list[Listener] = []
        self._settings = load_config(self._path)

    @property
    def settings(self) -> Settings:
        return self._settings

    def reload(self) -> Settings:
        clear_config_cache()
        self._settings = load_config(self._path, use_cache=False)
        self._emit()
        return self._settings

    def update(self, **changes: Any) -> Settings:
        self._settings = self._settings.model_copy(update=changes)
        save_config(self._settings, self._path)
        self._emit()
        return self._settings

    # -- listener management -------------------------------------------------
    def add_listener(self, callback: Listener) -> None:
        self._listeners.append(callback)

    def remove_listener(self, callback: Listener) -> None:
        try:
            self._listeners.remove(callback)
        except ValueError:
            pass

    def _emit(self) -> None:
        for listener in list(self._listeners):
            listener(self._settings)

    def iter_listeners(self) -> Iterable[Listener]:
        return tuple(self._listeners)
