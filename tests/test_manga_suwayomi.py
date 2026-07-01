"""Tests for the Suwayomi bridge source + ParsedHttpSource template + build_source."""

from __future__ import annotations

import httpx

from sagemtl_manga_crawler.core.fetch import MangaFetcher
from sagemtl_manga_crawler.core.http_source import ParsedHttpSource
from sagemtl_manga_crawler.core.models import ChapterRef, PageImage, SeriesResult
from sagemtl_manga_crawler.core.registry import build_source
from sagemtl_manga_crawler.sources import suwayomi as sw

SERVER = "http://localhost:4567"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16


def _fetcher(handler):
    return MangaFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)), sleep_fn=lambda d: None)


# --- pure parsers ---


def test_suwayomi_search_parse():
    payload = {"mangaList": [{"id": 7, "title": "Foo", "thumbnailUrl": "/thumb/7"}], "hasNextPage": False}
    res = sw.suwayomi_search_parse(payload, SERVER)
    assert res[0].title == "Foo"
    assert res[0].url == f"{SERVER}/api/v1/manga/7"
    assert res[0].source == "suwayomi"
    assert res[0].cover == f"{SERVER}/thumb/7"


def test_suwayomi_series_parse_list_and_dict():
    meta = {"title": "Foo", "thumbnailUrl": "http://abs/c.jpg", "sourceLang": "ja"}
    chapters_list = [{"index": 1, "chapterNumber": 1.0, "name": "One"}, {"index": 2, "chapterNumber": 2.0, "name": "Two"}]
    info, chapters = sw.suwayomi_series_parse(meta, chapters_list, 7, SERVER)
    assert info["title"] == "Foo" and info["cover"] == "http://abs/c.jpg" and info["lang"] == "ja"
    assert [c.id for c in chapters] == ["1", "2"]
    assert chapters[0].url == f"{SERVER}/api/v1/manga/7/chapter/1"
    # dict form ({"chapters": [...]}) also parses
    _info2, chapters2 = sw.suwayomi_series_parse(meta, {"chapters": chapters_list}, 7, SERVER)
    assert len(chapters2) == 2


def test_suwayomi_page_list():
    pages = sw.suwayomi_page_list({"pageCount": 3}, 7, 2, SERVER)
    assert len(pages) == 3
    assert pages[0].url == f"{SERVER}/api/v1/manga/7/chapter/2/page/0"
    assert pages[2].url.endswith("/page/2")


# --- source over MockTransport ---


def _source(handler):
    return sw.SuwayomiSource(SERVER, source_id="1", fetcher=_fetcher(handler))


def _searched_source():
    """Build a Suwayomi source over a mock server and walk search->pages."""

    def handler(request):
        path = request.url.path
        if path == "/api/v1/source/1/search":
            return httpx.Response(200, json={"mangaList": [{"id": 7, "title": "Foo", "thumbnailUrl": "/t"}]})
        if path == "/api/v1/manga/7/":
            return httpx.Response(200, json={"title": "Foo", "thumbnailUrl": "/t"})
        if path == "/api/v1/manga/7/chapters":
            return httpx.Response(200, json=[{"index": 1, "chapterNumber": 1, "name": "One"}])
        if path == "/api/v1/manga/7/chapter/1":
            return httpx.Response(200, json={"pageCount": 2})
        if "/page/" in path:
            return httpx.Response(200, content=PNG)
        return httpx.Response(404)

    src = _source(handler)
    results = list(src.search("foo"))
    meta, chapters = src.read_series(results[0].url)
    pages = src.fetch_page_list(chapters[0])
    return src, results, meta, chapters, pages


def test_suwayomi_source_search_and_pages():
    _src, results, meta, chapters, pages = _searched_source()
    assert results[0].url == f"{SERVER}/api/v1/manga/7"
    assert meta["title"] == "Foo" and len(chapters) == 1
    assert len(pages) == 2


def test_suwayomi_download_page(tmp_path):
    src, _results, _meta, _chapters, pages = _searched_source()
    out = src.download_page(pages[0], tmp_path / "001.png")
    assert out.read_bytes().startswith(b"\x89PNG")


# --- build_source factory ---


def test_build_source_factory():
    from sagemtl_manga_crawler.sources.mangadex import MangaDexSource

    class Cfg:
        suwayomi_url = SERVER
        suwayomi_source_id = "1"

    assert isinstance(build_source("mangadex"), MangaDexSource)
    assert isinstance(build_source("suwayomi", Cfg()), sw.SuwayomiSource)
    assert isinstance(build_source(""), MangaDexSource)  # default


# --- ParsedHttpSource template ---


class _FakeJsonSource(ParsedHttpSource):
    base_url = "https://x"
    name = "fakejson"
    lang = "en"

    def search_request(self, query):
        return (f"{self.base_url}/search", {"q": query})

    def search_parse(self, payload):
        return [SeriesResult(title=m["t"], url=m["u"], source="fakejson") for m in payload["list"]]

    def series_parse(self, payload, url):
        chapters = [ChapterRef(id=c["id"], number=c["n"], title=c["t"], url=c["u"], lang="en") for c in payload["chapters"]]
        return {"title": payload["title"]}, chapters

    def page_list_parse(self, payload, chapter):
        return [PageImage(index=i, url=u) for i, u in enumerate(payload["pages"])]


def test_parsed_http_source_template():
    def handler(request):
        if request.url.path == "/search":
            return httpx.Response(200, json={"list": [{"t": "Foo", "u": "https://x/m/1"}]})
        if request.url.path == "/m/1":
            return httpx.Response(200, json={"title": "Foo", "chapters": [{"id": "c1", "n": "1", "t": "One", "u": "https://x/c/1"}]})
        if request.url.path == "/c/1":
            return httpx.Response(200, json={"pages": ["https://x/p/0", "https://x/p/1"]})
        return httpx.Response(404)

    src = _FakeJsonSource(fetcher=_fetcher(handler))
    assert list(src.search("foo"))[0].title == "Foo"
    meta, chapters = src.read_series("https://x/m/1")
    assert meta["title"] == "Foo" and chapters[0].id == "c1"
    pages = src.fetch_page_list(chapters[0])
    assert len(pages) == 2 and pages[1].url == "https://x/p/1"
