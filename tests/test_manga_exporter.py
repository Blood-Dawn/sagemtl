"""Phase 9 unit tests: translated CBZ / PDF / folder export (round-trip)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from sagemtl_desktop.core.manga import exporter


def _png(color, size=(40, 60)):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_to_cbz_round_trip(tmp_path):
    pages = [_png((255, 0, 0)), _png((0, 255, 0))]
    out = exporter.to_cbz(pages, tmp_path / "c.cbz", comic_info={"title": "T", "number": "1"})
    with zipfile.ZipFile(out) as zf:
        assert zf.testzip() is None
        names = zf.namelist()
        assert "ComicInfo.xml" in names
        assert len([n for n in names if n != "ComicInfo.xml"]) == 2
        assert "<Title>T</Title>" in zf.read("ComicInfo.xml").decode("utf-8")


def test_to_pdf_has_one_page_per_image(tmp_path):
    pages = [_png((255, 0, 0)), _png((0, 255, 0)), _png((0, 0, 255))]
    out = exporter.to_pdf(pages, tmp_path / "c.pdf", comic_info={"title": "T"})
    data = Path(out).read_bytes()
    assert data[:5] == b"%PDF-"
    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(out))
        try:
            assert len(doc) == 3  # one PDF page per image
        finally:
            doc.close()
    except ImportError:  # pragma: no cover - pdf reader optional
        single = Path(exporter.to_pdf([pages[0]], tmp_path / "one.pdf")).read_bytes()
        assert len(data) > len(single)  # multi-page is larger than single-page


def test_to_folder(tmp_path):
    out = exporter.to_folder([_png((1, 2, 3))], tmp_path / "folder")
    assert (out / "001.png").exists()
    assert (out / "ComicInfo.xml").exists()


def test_to_pdf_empty_raises(tmp_path):
    with pytest.raises(ValueError):
        exporter.to_pdf([], tmp_path / "x.pdf")
