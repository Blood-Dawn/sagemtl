"""Phase 7 unit tests: MangaDex crawler (parsing, URL build, fetch via MockTransport)."""

from __future__ import annotations

import zipfile

import httpx
import pytest

from sagemtl_manga_crawler.core import registry
from sagemtl_manga_crawler.core.fetch import MangaFetcher
from sagemtl_manga_crawler.core.models import ChapterRef, PageImage
from sagemtl_manga_crawler.core.rate_limit import TokenBucket
from sagemtl_manga_crawler.exporters import cbz_exporter
from sagemtl_manga_crawler.sources import mangadex

# Recorded MangaDex response shapes (verified live).
AT_HOME = {
    "result": "ok",
    "baseUrl": "https://cmdxd98sb0x3yprd.mangadex.network",
    "chapter": {
        "hash": "f78a4c9987d7410af3068dd41dffe4d8",
        "data": ["x1-aaa.png", "x2-bbb.png"],
        "dataSaver": ["x1-aaa.jpg", "x2-bbb.jpg"],
    },
}
SEARCH_JSON = {
    "result": "ok",
    "data": [{
        "id": "manga-1", "type": "manga",
        "attributes": {"title": {"en": "Test Manga"}, "altTitles": []},
        "relationships": [{"id": "c", "type": "cover_art", "attributes": {"fileName": "cover.jpg"}}],
    }],
    "total": 1,
}
FEED_JSON = {
    "result": "ok",
    "data": [{
        "id": "ch-1", "type": "chapter",
        "attributes": {"chapter": "1", "title": "Start", "translatedLanguage": "en"},
    }],
    "total": 1,
}

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def _source(handler, **kw):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return mangadex.MangaDexSource(fetcher=MangaFetcher(client=client, sleep_fn=lambda d: None), **kw)


# --- pure parsers / URL build ---


def test_build_page_urls():
    full = mangadex.build_page_urls(AT_HOME)
    assert full == [
        "https://cmdxd98sb0x3yprd.mangadex.network/data/f78a4c9987d7410af3068dd41dffe4d8/x1-aaa.png",
        "https://cmdxd98sb0x3yprd.mangadex.network/data/f78a4c9987d7410af3068dd41dffe4d8/x2-bbb.png",
    ]
    saver = mangadex.build_page_urls(AT_HOME, data_saver=True)
    assert saver[0].endswith("/data-saver/f78a4c9987d7410af3068dd41dffe4d8/x1-aaa.jpg")


def test_search_parse():
    res = mangadex.search_parse(SEARCH_JSON)
    assert len(res) == 1
    assert res[0].title == "Test Manga"
    assert res[0].url == "https://mangadex.org/title/manga-1"
    assert res[0].source == "mangadex"
    assert res[0].cover == "https://uploads.mangadex.org/covers/manga-1/cover.jpg"


def test_feed_parse():
    chapters = mangadex.feed_parse(FEED_JSON)
    assert len(chapters) == 1
    ch = chapters[0]
    assert (ch.id, ch.number, ch.title, ch.lang) == ("ch-1", "1", "Start", "en")
    assert ch.url == "https://mangadex.org/chapter/ch-1"


def test_extract_id():
    assert mangadex.extract_id("https://mangadex.org/title/abc-123/some-slug") == "abc-123"
    assert mangadex.extract_id("https://mangadex.org/chapter/xyz-9") == "xyz-9"
    assert mangadex.extract_id("plain-id") == "plain-id"


# --- rate limiter ---


def test_token_bucket_waits_when_empty():
    clock = [0.0]
    slept = []

    def sleep(d):
        slept.append(d)
        clock[0] += d

    tb = TokenBucket(rate=2.0, capacity=2.0, time_fn=lambda: clock[0], sleep_fn=sleep)
    assert tb.acquire() == 0.0          # token 1
    assert tb.acquire() == 0.0          # token 2
    waited = tb.acquire()               # token 3 -> wait 1 token / 2 per sec = 0.5s
    assert waited == pytest.approx(0.5)
    assert slept == [pytest.approx(0.5)]


# --- CBZ / ComicInfo ---


def test_cbz_round_trip(tmp_path):
    dest = tmp_path / "out.cbz"
    cbz_exporter.write_cbz(
        [PNG, (b"\xff\xd8\xff" + b"0" * 20, "jpg")], dest,
        comic_info={"title": "T", "series": "S", "number": "1"},
    )
    with zipfile.ZipFile(dest) as zf:
        names = zf.namelist()
        assert "001.png" in names and "002.jpg" in names and "ComicInfo.xml" in names
        info = zf.read("ComicInfo.xml").decode("utf-8")
        assert "<Title>T</Title>" in info
        assert "<PageCount>2</PageCount>" in info


def test_comicinfo_xml():
    xml = cbz_exporter.build_comicinfo_xml({"title": "X", "language": "en", "page_count": 3})
    assert "<Title>X</Title>" in xml
    assert "<LanguageISO>en</LanguageISO>" in xml
    assert "<PageCount>3</PageCount>" in xml


def test_write_folder(tmp_path):
    out = cbz_exporter.write_folder([PNG], tmp_path / "ch1")
    assert (out / "001.png").exists()
    assert (out / "ComicInfo.xml").exists()


# --- registry ---


def test_registry_discovers_mangadex():
    sources = registry.discover_sources()
    assert "mangadex" in sources
    assert sources["mangadex"] is mangadex.MangaDexSource


def test_load_index():
    index = registry.load_index()
    names = [s["name"] for s in index["sources"]]
    assert "mangadex" in names


# --- source over MockTransport (no network) ---


def test_source_search_over_mock():
    def handler(request):
        assert request.url.path == "/manga"
        return httpx.Response(200, json=SEARCH_JSON)

    res = list(_source(handler).search("test"))
    assert res[0].title == "Test Manga"


def test_source_fetch_page_list_over_mock():
    def handler(request):
        if "/at-home/server/" in request.url.path:
            return httpx.Response(200, json=AT_HOME)
        return httpx.Response(404)

    src = _source(handler)
    chapter = ChapterRef(id="ch-1", number="1", title="", url="https://mangadex.org/chapter/ch-1", lang="en")
    pages = src.fetch_page_list(chapter)
    assert len(pages) == 2
    assert pages[0].referer == "https://mangadex.org/chapter/ch-1"
    assert pages[0].url.endswith("x1-aaa.png")


def test_download_page_reports_for_cdn(tmp_path):
    calls = {"img": 0, "report": 0}

    def handler(request):
        if request.url.host == "api.mangadex.network" and request.url.path == "/report":
            calls["report"] += 1
            return httpx.Response(200, json={"result": "ok"})
        if request.url.host == "cmdxd98sb0x3yprd.mangadex.network":
            calls["img"] += 1
            return httpx.Response(200, content=PNG)
        return httpx.Response(404)

    src = _source(handler)
    page = PageImage(
        index=0,
        url="https://cmdxd98sb0x3yprd.mangadex.network/data/h/x1-aaa.png",
        referer="https://mangadex.org/chapter/ch-1",
    )
    out = src.download_page(page, tmp_path / "001.png")
    assert calls["img"] == 1
    assert calls["report"] == 1  # report fired for the volunteer CDN host
    assert out.read_bytes().startswith(b"\x89PNG")


def test_download_page_no_report_for_mangadex_org(tmp_path):
    calls = {"report": 0}

    def handler(request):
        if request.url.path == "/report":
            calls["report"] += 1
            return httpx.Response(200, json={})
        return httpx.Response(200, content=PNG)

    src = _source(handler)
    page = PageImage(index=0, url="https://s1.mangadex.org/data/h/x1.png", referer="r")
    src.download_page(page, tmp_path / "p.png")
    assert calls["report"] == 0  # never report mangadex.org-hosted images


def test_download_chapter_rerequests_athome_on_403(tmp_path):
    state = {"athome": 0}

    def handler(request):
        path = request.url.path
        if "/at-home/server/" in path:
            state["athome"] += 1
            base = "https://stale.example.network" if state["athome"] == 1 else "https://fresh.example.network"
            return httpx.Response(200, json={
                "result": "ok", "baseUrl": base,
                "chapter": {"hash": "h", "data": ["x1-a.png"], "dataSaver": []},
            })
        if request.url.host == "stale.example.network":
            return httpx.Response(403)  # expired baseUrl
        if request.url.host == "fresh.example.network":
            return httpx.Response(200, content=PNG)
        if path == "/report":
            return httpx.Response(200, json={})
        return httpx.Response(404)

    src = _source(handler)
    chapter = ChapterRef(id="ch-1", number="1", title="", url="https://mangadex.org/chapter/ch-1", lang="en")
    saved = src.download_chapter(chapter, tmp_path)
    assert len(saved) == 1
    assert state["athome"] == 2  # re-requested at-home after the stale 403
    assert saved[0].read_bytes().startswith(b"\x89PNG")


def test_download_chapter_survives_multiple_athome_expirations(tmp_path):
    # Each baseUrl serves exactly one page, then "expires" (403) -- so a 3-page
    # chapter requires TWO separate at-home re-fetches. With max_athome_refresh=1
    # this only succeeds because the budget resets after each successful page.
    state = {"athome": 0, "served_this_gen": 0}

    def handler(request):
        path = request.url.path
        if "/at-home/server/" in path:
            state["athome"] += 1
            state["served_this_gen"] = 0
            base = f"https://h{state['athome']}.ex.network"
            return httpx.Response(200, json={
                "result": "ok", "baseUrl": base,
                "chapter": {"hash": "h", "data": ["a.png", "b.png", "c.png"], "dataSaver": []},
            })
        if path == "/report":
            return httpx.Response(200, json={})
        if request.url.host == f"h{state['athome']}.ex.network" and state["served_this_gen"] < 1:
            state["served_this_gen"] += 1
            return httpx.Response(200, content=PNG)
        return httpx.Response(403)  # stale / expired baseUrl

    src = _source(handler)
    chapter = ChapterRef(id="ch-1", number="1", title="", url="https://mangadex.org/chapter/ch-1", lang="en")
    saved = src.download_chapter(chapter, tmp_path, max_athome_refresh=1)
    assert len(saved) == 3
    assert state["athome"] == 3  # initial + 2 refreshes across the chapter


def test_crawler_import_is_light():
    import subprocess
    import sys
    from pathlib import Path

    code = (
        "import sys, sagemtl_manga_crawler.sources.mangadex\n"
        "print('httpx' in sys.modules)\n"
    )
    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(repo))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"  # httpx import stays lazy
