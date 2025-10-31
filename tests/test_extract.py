# Kheiven D\'Haiti — extractor unit test
from pathlib import Path

from sagemtl.crawl.extract import extract_main_text


def test_extract_from_sample():
    html = Path("tests/data/sample.html").read_text(encoding="utf-8")
    out = extract_main_text(html)
    assert 'Hello world-smart "quotes"!' in out
    assert out.endswith("\n")
