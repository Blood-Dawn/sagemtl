"""Translated manga export: CBZ (+ ComicInfo.xml), PDF, and page folder.

CBZ and folder reuse the crawler's exporter (one implementation of the
ComicInfo/zip layout); PDF stitches one image per page via Pillow. ``pages`` is a
list of image ``bytes`` (or ``(bytes, ext)`` tuples). All heavy imports are lazy.

See ``MANGA_MODULE_BUILD_SPEC.md`` sections 9.5 and 14 (Phase 9).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional, Sequence

__all__ = ["to_cbz", "to_pdf", "to_folder"]


def to_cbz(pages: Sequence, dest: Path, *, comic_info: Optional[dict] = None) -> Path:
    """Write a translated chapter to CBZ (with a ComicInfo.xml sidecar)."""

    from sagemtl_manga_crawler.exporters import cbz_exporter

    return cbz_exporter.write_cbz(pages, Path(dest), comic_info=comic_info)


def to_folder(pages: Sequence, dest: Path, *, comic_info: Optional[dict] = None) -> Path:
    """Write a translated chapter to a per-page folder (with ComicInfo.xml)."""

    from sagemtl_manga_crawler.exporters import cbz_exporter

    return cbz_exporter.write_folder(pages, Path(dest), comic_info=comic_info)


def to_pdf(pages: Sequence, dest: Path, *, comic_info: Optional[dict] = None) -> Path:
    """Write a translated chapter to a PDF (one image per page)."""

    from PIL import Image

    images = []
    for page in pages:
        data = page[0] if isinstance(page, (tuple, list)) else page
        images.append(Image.open(io.BytesIO(data)).convert("RGB"))
    if not images:
        raise ValueError("no pages to export")

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    title = (comic_info or {}).get("title")
    save_kwargs = {"format": "PDF", "save_all": True, "append_images": images[1:]}
    if title:
        save_kwargs["title"] = str(title)
    images[0].save(str(dest), **save_kwargs)
    return dest
