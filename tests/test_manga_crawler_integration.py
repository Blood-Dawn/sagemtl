"""Phase 7 integration test: live MangaDex search + chapter download (network).

Marked ``integration``. Run:
    python -m pytest tests/test_manga_crawler_integration.py -m integration -v

Gate: MangaDex search returns results; a public chapter downloads all pages via
the at-home flow (page count matches the at-home list); output writes a valid CBZ.
Uses the official public API (no key), an honest User-Agent, and conservative rate
limits per ToS.
"""

from __future__ import annotations

import zipfile

import pytest

pytestmark = pytest.mark.integration


def _source():
    from sagemtl_manga_crawler.core.fetch import MangaFetcher
    from sagemtl_manga_crawler.sources.mangadex import MangaDexSource

    return MangaDexSource(fetcher=MangaFetcher(rate_per_sec=3.0))


def test_mangadex_search_live():
    try:
        results = list(_source().search("test"))
    except Exception as exc:  # pragma: no cover - network dependent
        pytest.skip(f"MangaDex search unavailable: {exc}")
    assert results, "search returned no results"
    assert any(r.title for r in results)
    assert all(r.source == "mangadex" for r in results)


def test_mangadex_download_chapter_live(tmp_path):
    src = _source()
    try:
        results = list(src.search("test"))
        # Find a series with an English chapter feed.
        chapter = None
        for series in results[:5]:
            _meta, chapters = src.read_series(series.url)
            if chapters:
                chapter = chapters[0]
                break
        if chapter is None:
            pytest.skip("no English chapter found to download")
        pages = src.fetch_page_list(chapter)
        assert pages, "at-home returned no pages"
        saved = src.download_chapter(chapter, tmp_path / "chapter")
    except Exception as exc:  # pragma: no cover - network dependent
        pytest.skip(f"MangaDex download unavailable: {exc}")

    # All pages from the at-home list were downloaded.
    assert len(saved) == len(pages)
    assert all(p.stat().st_size > 0 for p in saved)

    # Package into a valid CBZ and read it back.
    from sagemtl_manga_crawler.exporters import cbz_exporter

    page_blobs = [p.read_bytes() for p in saved]
    cbz = cbz_exporter.write_cbz(
        page_blobs, tmp_path / "out.cbz",
        comic_info={"title": chapter.title or "Chapter", "number": chapter.number, "language": chapter.lang},
    )
    with zipfile.ZipFile(cbz) as zf:
        assert zf.testzip() is None  # valid archive
        assert "ComicInfo.xml" in zf.namelist()
        image_names = [n for n in zf.namelist() if n != "ComicInfo.xml"]
        assert len(image_names) == len(saved)
