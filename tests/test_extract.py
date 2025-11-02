# Kheiven D\'Haiti — extractor unit test
from pathlib import Path

from sagemtl.crawl.extract import extract_main_text


def test_extract_from_sample_drops_boilerplate():
    html = Path("tests/data/sample.html").read_text(encoding="utf-8")
    out = extract_main_text(html)
    assert 'Hello world-smart "quotes"!' in out
    assert "MySite News" not in out
    assert out.endswith("\n")


def test_extract_trims_repeated_wrappers():
    html = """
    <html>
      <body>
        ExampleSite — Daily Edition
        <div><p>Main content keeps going.</p></div>
        ExampleSite — Daily Edition
      </body>
    </html>
    """
    out = extract_main_text(html)
    assert "Main content keeps going." in out
    assert "ExampleSite — Daily Edition" not in out
