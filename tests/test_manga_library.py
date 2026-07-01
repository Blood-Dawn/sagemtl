"""Phase 8 unit tests: MangaLibrary persistence (no Qt)."""

from __future__ import annotations

from dataclasses import dataclass

from sagemtl_desktop.core.manga.library import MangaLibrary
from sagemtl_desktop.core.manga.models import MangaSeries


@dataclass
class FakeRef:
    id: str
    number: str
    title: str
    url: str
    lang: str


def test_add_get_persist(tmp_path):
    lib = MangaLibrary(tmp_path)
    saved = lib.add_series(MangaSeries(series_id="", title="T", source_url="u", source_name="mangadex"))
    assert saved.series_id
    assert lib.get_series(saved.series_id).title == "T"
    assert lib.get_series_by_url("u").series_id == saved.series_id

    # a fresh instance reloads from disk
    reloaded = MangaLibrary(tmp_path)
    assert reloaded.get_series(saved.series_id).title == "T"


def test_upsert_resume_merges_and_respects_title_lock(tmp_path):
    lib = MangaLibrary(tmp_path)
    refs = [FakeRef("c1", "1", "One", "https://m/ch/c1", "en")]
    series = lib.upsert_series_from_crawled(
        {"title": "Orig", "cover": "cov", "lang": "ja"}, refs, "https://m/title/x", "mangadex"
    )
    assert len(series.chapters) == 1

    lib.set_title(series.series_id, "MyName", lock=True)

    refs2 = refs + [FakeRef("c2", "2", "Two", "https://m/ch/c2", "en")]
    again = lib.upsert_series_from_crawled({"title": "NewTitle"}, refs2, "https://m/title/x", "mangadex")
    assert again.series_id == series.series_id      # resumed, same series
    assert len(again.chapters) == 2                 # merged, no duplicate of c1
    assert again.title == "MyName"                  # title lock preserved


def test_upsert_dedups_when_refs_lack_url_and_id(tmp_path):
    # A scraper source emitting only number+title (no stable url/id) must still
    # dedup on resume -- the merge key uses durable fields, not a minted uuid.
    lib = MangaLibrary(tmp_path)
    refs = [
        FakeRef("", "1", "One", "", "en"),
        FakeRef("", "2", "Two", "", "en"),
    ]
    first = lib.upsert_series_from_crawled({"title": "S"}, refs, "https://m/s", "scraper")
    assert len(first.chapters) == 2
    again = lib.upsert_series_from_crawled({"title": "S"}, refs, "https://m/s", "scraper")
    assert len(again.chapters) == 2  # no duplicates on identical re-crawl


def test_save_page_image_paths(tmp_path):
    lib = MangaLibrary(tmp_path)
    out = lib.save_page_image("sid", "cid", 0, b"\x89PNGdata", ext="png", kind="out")
    assert out.exists() and out.name == "001.png"
    assert "out" in out.parts
    raw = lib.save_page_image("sid", "cid", 4, b"jpgdata", ext="jpg", kind="raw")
    assert raw.name == "005.jpg" and "raw" in raw.parts


def test_remove_series(tmp_path):
    lib = MangaLibrary(tmp_path)
    lib.add_series(MangaSeries(series_id="abc", title="T", source_url="u"))
    assert lib.remove_series("abc") is True
    assert lib.get_series("abc") is None
    assert lib.remove_series("abc") is False
