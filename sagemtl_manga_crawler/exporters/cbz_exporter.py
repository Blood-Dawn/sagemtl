"""CBZ exporter for crawled pages.

Writes ``NNN.<ext>`` page images plus a ``ComicInfo.xml`` sidecar into a ``.cbz``
(ZIP), and supports a raw folder-per-chapter layout. CBZ with ``ComicInfo.xml`` is
the native manga target. Pure stdlib (zipfile + xml); preserves the original image
format (no re-encode).

See ``MANGA_MODULE_BUILD_SPEC.md`` section 9.5.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional, Sequence

__all__ = ["write_cbz", "write_folder", "build_comicinfo_xml", "infer_ext"]


def infer_ext(data: bytes) -> str:
    """Infer an image extension from magic bytes (default 'jpg')."""

    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return "jpg"


def _normalize_pages(pages: Sequence) -> list[tuple[bytes, str]]:
    """Accept ``[bytes, ...]`` or ``[(bytes, ext), ...]`` -> ``[(bytes, ext), ...]``."""

    out: list[tuple[bytes, str]] = []
    for page in pages:
        if isinstance(page, (tuple, list)):
            data, ext = page[0], page[1]
        else:
            data, ext = page, infer_ext(page)
        out.append((bytes(data), str(ext).lstrip(".").lower()))
    return out


def build_comicinfo_xml(info: Optional[dict] = None) -> str:
    """Build a minimal valid ComicInfo.xml string from a metadata dict."""

    info = info or {}
    root = ET.Element("ComicInfo")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")

    field_map = [
        ("Title", "title"),
        ("Series", "series"),
        ("Number", "number"),
        ("Count", "count"),
        ("Summary", "summary"),
        ("Writer", "writer"),
        ("Translator", "translator"),
        ("LanguageISO", "language"),
        ("Manga", "manga"),
        ("Web", "web"),
    ]
    for tag, key in field_map:
        if key in info and info[key] not in (None, ""):
            ET.SubElement(root, tag).text = str(info[key])
    page_count = info.get("page_count")
    if page_count is not None:
        ET.SubElement(root, "PageCount").text = str(page_count)

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def write_cbz(pages: Sequence, dest: Path, *, comic_info: Optional[dict] = None) -> Path:
    """Write pages + ComicInfo.xml into a ``.cbz`` (ZIP). Returns the path."""

    normalized = _normalize_pages(pages)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    info = dict(comic_info or {})
    info.setdefault("page_count", len(normalized))

    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for index, (data, ext) in enumerate(normalized, start=1):
            zf.writestr(f"{index:03d}.{ext}", data)
        zf.writestr("ComicInfo.xml", build_comicinfo_xml(info))
    return dest


def write_folder(pages: Sequence, dest_dir: Path, *, comic_info: Optional[dict] = None) -> Path:
    """Write pages (and ComicInfo.xml) into a folder-per-chapter layout."""

    normalized = _normalize_pages(pages)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    for index, (data, ext) in enumerate(normalized, start=1):
        (dest_dir / f"{index:03d}.{ext}").write_bytes(data)
    info = dict(comic_info or {})
    info.setdefault("page_count", len(normalized))
    (dest_dir / "ComicInfo.xml").write_text(build_comicinfo_xml(info), encoding="utf-8")
    return dest_dir
