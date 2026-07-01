"""Phase 8 unit tests: manga job orchestration with fakes (no network, no models)."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from sagemtl_desktop.core.manga import jobs
from sagemtl_desktop.core.manga.library import MangaLibrary
from sagemtl_desktop.core.manga.models import PageResult, TextRegion


@dataclass
class FakeRef:
    id: str
    number: str
    title: str
    url: str
    lang: str


@dataclass
class FakePageImage:
    index: int
    url: str
    referer: str = ""
    headers: dict = field(default_factory=dict)


class FakeSource:
    name = "fake"

    def read_series(self, url):
        return ({"title": "T", "cover": "", "lang": "ja"},
                [FakeRef("c1", "1", "One", "https://m/ch/c1", "ja")])

    def fetch_page_list(self, chapter_ref):
        return [FakePageImage(0, "http://x/a.png"), FakePageImage(1, "http://x/b.png")]

    def download_page(self, page, dest):
        Path(dest).write_bytes(b"\x89PNGraw" + bytes([page.index]))
        return Path(dest)


def _png(i):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (i * 30 % 255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


class FakePipeline:
    def process_chapter(self, blobs, *, source_lang, series_id, progress_cb=None, log_cb=None):
        if progress_cb:
            progress_cb(100.0)
        return [
            PageResult(
                index=i,
                regions=[TextRegion(box=(0, 0, 1, 1), source_text="s", target_text="t")],
                clean_image=b"",
                rendered_image=_png(i),
            )
            for i in range(len(blobs))
        ]


def test_add_series_from_url(tmp_path):
    lib = MangaLibrary(tmp_path)
    series = jobs.add_series_from_url(lib, FakeSource(), "https://m/title/x")
    assert series.title == "T"
    assert len(series.chapters) == 1
    assert lib.get_series_by_url("https://m/title/x") is not None


def test_translate_chapter(tmp_path):
    lib = MangaLibrary(tmp_path)
    src = FakeSource()
    series = jobs.add_series_from_url(lib, src, "https://m/title/x")
    chapter_id = series.chapters[0].chapter_id
    progress = []

    chapter = jobs.translate_chapter(
        lib, src, FakePipeline(), series.series_id, chapter_id,
        source_lang="ja", progress_cb=progress.append,
    )

    assert len(chapter.pages) == 2
    assert chapter.pages[0].status == "done"
    rendered = Path(chapter.pages[0].rendered_image_path)
    assert rendered.exists() and rendered.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert Path(chapter.pages[0].source_image_path).exists()
    assert chapter.pages[0].regions[0]["target_text"] == "t"
    assert progress and progress[-1] == 100.0

    # persisted: reload from disk
    reloaded = MangaLibrary(tmp_path)
    assert reloaded.get_series(series.series_id).chapters[0].pages[0].status == "done"


def test_export_chapter_cbz(tmp_path):
    lib = MangaLibrary(tmp_path)
    src = FakeSource()
    series = jobs.add_series_from_url(lib, src, "https://m/title/x")
    chapter_id = series.chapters[0].chapter_id
    jobs.translate_chapter(lib, src, FakePipeline(), series.series_id, chapter_id)

    out = jobs.export_chapter(lib, series.series_id, chapter_id, tmp_path / "out.cbz", fmt="cbz")
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert "ComicInfo.xml" in names
        assert len([n for n in names if n != "ComicInfo.xml"]) == 2

    pdf = jobs.export_chapter(lib, series.series_id, chapter_id, tmp_path / "out.pdf", fmt="pdf")
    assert Path(pdf).read_bytes()[:5] == b"%PDF-"


def test_translate_unknown_series_raises(tmp_path):
    lib = MangaLibrary(tmp_path)
    import pytest

    with pytest.raises(ValueError):
        jobs.translate_chapter(lib, FakeSource(), FakePipeline(), "nope", "nope")
