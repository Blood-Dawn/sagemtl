"""SageMTL manga module.

Heavy ML dependencies (torch, onnxruntime, paddle, opencv, transformers, numpy)
are isolated inside this package and imported lazily within function bodies. This
package init only re-exports the dependency-light data models so that importing
``sagemtl_desktop.core.manga`` (and the novel path) never triggers a heavy import.
"""

from __future__ import annotations

from .models import (
    MangaChapter,
    MangaConfig,
    MangaPage,
    MangaSeries,
    PageResult,
    TextRegion,
)

__all__ = [
    "MangaChapter",
    "MangaConfig",
    "MangaPage",
    "MangaSeries",
    "PageResult",
    "TextRegion",
]
