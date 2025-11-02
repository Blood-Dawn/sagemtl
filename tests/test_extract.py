# Kheiven D'Haiti — extractor unit test
from sagemtl.crawl.extract import extract_main_text

SAMPLE_HTML = """<!DOCTYPE html>\n<html lang=\"en\">\n  <body>\n    <article>\n      <h1>Hello world-smart “quotes”!</h1>\n      <p>Example paragraph.</p>\n    </article>\n  </body>\n</html>\n"""


def test_extract_from_sample():
    out = extract_main_text(SAMPLE_HTML)
    assert 'Hello world-smart "quotes"!' in out
    assert out.endswith("\n")
