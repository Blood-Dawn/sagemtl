# Kheiven D'Haiti — tests
from sagemtl.clean.text import clean_text


def test_clean_basic():
    raw = "“Hello—world”\n\n\nNice\u00a0space"
    out = clean_text(raw)
    assert "--" not in out
    assert '"' in out and "  " not in out
