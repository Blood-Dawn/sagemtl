"""Manga job orchestration (no Qt).

Pure functions that wire the crawler, pipeline, library, and exporter together for
the three manga jobs (add series, translate chapter, export). The UI wraps these
in ``JobManager`` workers; keeping them Qt-free makes them testable with fakes.
Heavy/crawler imports are lazy. Progress is reported as 0..100 via ``progress_cb``.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 11.4.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from .library import MangaLibrary
from .models import MangaChapter, MangaPage, MangaSeries

__all__ = ["add_series_from_url", "translate_chapter", "export_chapter", "rerender_page"]

ProgressCb = Optional[Callable[[float], None]]
LogCb = Optional[Callable[[str], None]]


def _log(log_cb: LogCb, message: str) -> None:
    if log_cb:
        log_cb(message)


def _progress(progress_cb: ProgressCb, pct: float) -> None:
    if progress_cb:
        progress_cb(max(0.0, min(100.0, pct)))


def add_series_from_url(library: MangaLibrary, source, url: str, *, log_cb: LogCb = None) -> MangaSeries:
    """Read a series' metadata + chapter list and upsert it into the library."""

    _log(log_cb, f"[manga] reading series: {url}")
    meta, chapters = source.read_series(url)
    series = library.upsert_series_from_crawled(
        meta, chapters, url, source_name=getattr(source, "name", "manga")
    )
    _log(log_cb, f"[manga] added '{series.title}' with {len(series.chapters)} chapters")
    return series


def _chapter_ref(chapter: MangaChapter):
    from sagemtl_manga_crawler.core.models import ChapterRef

    return ChapterRef(
        id=chapter.chapter_id,
        number=chapter.number,
        title=chapter.title,
        url=chapter.source_url,
        lang=chapter.lang,
    )


def _ext_from_url(url: str) -> str:
    name = url.rsplit("/", 1)[-1]
    return ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ".jpg"


def translate_chapter(
    library: MangaLibrary,
    source,
    pipeline,
    series_id: str,
    chapter_id: str,
    *,
    source_lang: str = "auto",
    progress_cb: ProgressCb = None,
    log_cb: LogCb = None,
) -> MangaChapter:
    """Download a chapter's pages, run the pipeline, save rendered output, persist."""

    series = library.get_series(series_id)
    if series is None:
        raise ValueError(f"unknown series {series_id!r}")
    chapter = next((c for c in series.chapters if c.chapter_id == chapter_id), None)
    if chapter is None:
        raise ValueError(f"unknown chapter {chapter_id!r} in series {series_id!r}")

    _log(log_cb, f"[manga] fetching page list for chapter {chapter.number or chapter_id}")
    pages = source.fetch_page_list(_chapter_ref(chapter))
    if not pages:
        raise RuntimeError("no pages returned for chapter")

    raw_dir = library.raw_chapter_dir(series_id, chapter_id)
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_paths: list[Path] = []
    raw_blobs: list[bytes] = []
    total = len(pages)
    for n, page in enumerate(pages):
        dest = raw_dir / f"{page.index + 1:03d}{_ext_from_url(page.url)}"
        source.download_page(page, dest)
        raw_paths.append(dest)
        raw_blobs.append(dest.read_bytes())
        _progress(progress_cb, (n + 1) / total * 40.0)  # download = first 40%
    _log(log_cb, f"[manga] downloaded {len(raw_blobs)} pages; translating")

    def pipeline_progress(pct: float) -> None:
        _progress(progress_cb, 40.0 + pct * 0.6)  # pipeline = remaining 60%

    results = pipeline.process_chapter(
        raw_blobs, source_lang=source_lang, series_id=series_id,
        progress_cb=pipeline_progress, log_cb=log_cb,
    )

    manga_pages: list[MangaPage] = []
    for i, result in enumerate(results):
        out_path = library.save_page_image(
            series_id, chapter_id, i, result.rendered_image, ext="png", kind="out"
        )
        clean_path = ""
        if getattr(result, "clean_image", b""):
            clean_dir = library.out_chapter_dir(series_id, chapter_id)
            clean_dir.mkdir(parents=True, exist_ok=True)
            clean_file = clean_dir / f"{i + 1:03d}_clean.png"
            clean_file.write_bytes(result.clean_image)
            clean_path = str(clean_file)
        manga_pages.append(
            MangaPage(
                index=i,
                source_image_path=str(raw_paths[i]) if i < len(raw_paths) else "",
                clean_image_path=clean_path,
                rendered_image_path=str(out_path),
                regions=[r.to_dict() for r in result.regions],
                status="done",
            )
        )

    chapter.pages = manga_pages
    library.update_series(series)
    _progress(progress_cb, 100.0)
    _log(log_cb, f"[manga] chapter done: {len(manga_pages)} pages rendered")
    return chapter


def rerender_page(clean_image, regions, *, font_path=None, target_lang: str = "en") -> bytes:
    """Re-typeset one page from its cleaned image + (edited) regions -> PNG bytes.

    No detection/OCR/translation/inpaint -- just typeset, so a manual-correction
    re-render is sub-second on already-loaded models (the Phase 10 gate). ``regions``
    is a list of ``TextRegion`` (with possibly edited ``target_text``/``box``).
    """

    import io

    from PIL import Image

    from . import detect, typeset

    if isinstance(clean_image, (bytes, bytearray)):
        rgb = detect.load_image_rgb(bytes(clean_image))
    else:
        rgb = clean_image
    rendered = typeset.render(rgb, regions, font_path=font_path, target_lang=target_lang)
    buffer = io.BytesIO()
    Image.fromarray(rendered).save(buffer, format="PNG")
    return buffer.getvalue()


def export_chapter(
    library: MangaLibrary,
    series_id: str,
    chapter_id: str,
    dest: Path,
    *,
    fmt: str = "cbz",
    use_rendered: bool = True,
    log_cb: LogCb = None,
) -> Path:
    """Export a translated (or raw) chapter to CBZ/PDF/folder."""

    series = library.get_series(series_id)
    if series is None:
        raise ValueError(f"unknown series {series_id!r}")
    chapter = next((c for c in series.chapters if c.chapter_id == chapter_id), None)
    if chapter is None:
        raise ValueError(f"unknown chapter {chapter_id!r}")

    paths: list[Path] = []
    for page in sorted(chapter.pages, key=lambda p: p.index):
        candidate = page.rendered_image_path if use_rendered else page.source_image_path
        if candidate and Path(candidate).exists():
            paths.append(Path(candidate))
    if not paths:
        raise RuntimeError("no rendered pages to export; translate the chapter first")

    blobs = [p.read_bytes() for p in paths]
    comic_info = {
        "title": chapter.title or series.title,
        "series": series.title,
        "number": chapter.number,
        "language": series.lang,
    }
    from . import exporter as manga_exporter

    dest = Path(dest)
    if fmt == "pdf":
        result = manga_exporter.to_pdf(blobs, dest, comic_info=comic_info)
    elif fmt == "folder":
        result = manga_exporter.to_folder(blobs, dest, comic_info=comic_info)
    elif fmt == "cbz":
        result = manga_exporter.to_cbz(blobs, dest, comic_info=comic_info)
    else:
        raise ValueError(f"unknown export format {fmt!r}")
    _log(log_cb, f"[manga] exported {len(blobs)} pages to {result}")
    return result
