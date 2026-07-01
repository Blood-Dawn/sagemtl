"""Source registry and discovery.

Mirrors the lightnovel-crawler convention: source plugins live under ``sources/``
and are discovered dynamically; concrete ``MangaSource`` subclasses with a valid
``base_url`` are kept. A prebuilt ``sources/_index.json`` carries lightweight
metadata (name, lang, is_webtoon, nsfw, base_urls) and ``sources/_rejected.json``
maps dead hosts to a reason so they can be disabled without deleting code.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 9.2.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
from pathlib import Path

from .source_base import MangaSource

__all__ = ["discover_sources", "load_index", "load_rejected", "build_source"]


def build_source(name: str, config=None, fetcher=None):
    """Construct a configured source by name (mangadex default; suwayomi bridge).

    ``config`` is an optional MangaConfig-like object (read for the Suwayomi server
    URL / source id). Concrete scraper sources, if a user adds them under
    ``sources/``, are reachable via :func:`discover_sources`.
    """

    key = (name or "mangadex").strip().lower()
    if key == "suwayomi":
        from ..sources.suwayomi import SuwayomiSource

        return SuwayomiSource(
            getattr(config, "suwayomi_url", "") if config else "",
            getattr(config, "suwayomi_source_id", "") if config else "",
            fetcher=fetcher,
        )
    from ..sources.mangadex import MangaDexSource

    return MangaDexSource(fetcher=fetcher) if fetcher is not None else MangaDexSource()


def _sources_package():
    from .. import sources

    return sources


def discover_sources() -> dict[str, type]:
    """Import the source plugins and return ``{name: MangaSource subclass}``."""

    package = _sources_package()
    found: dict[str, type] = {}
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{package.__name__}.{module_info.name}")
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, MangaSource)
                and value is not MangaSource
                and getattr(value, "base_url", "")
            ):
                found[getattr(value, "name", value.__name__)] = value
    return found


def _index_path(name: str) -> Path:
    package = _sources_package()
    return Path(package.__path__[0]) / name


def load_index() -> dict:
    """Load the prebuilt ``sources/_index.json``."""

    path = _index_path("_index.json")
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"version": "1.0", "sources": []}


def load_rejected() -> dict:
    """Load the ``sources/_rejected.json`` host->reason map."""

    path = _index_path("_rejected.json")
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"version": "1.0", "rejected": {}}
