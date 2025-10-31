# Kheiven D'Haiti — tests
from sagemtl.clean.text_normalize import basic_clean

def test_basic():
    s = "“Hello—world”  \n\nThis\u200B is… fine\r\n"
    out = basic_clean(s)
    assert '"' in out and "-" in out
    assert "\r" not in out and "\u200B" not in out
    assert out.endswith("fine\n") or out.endswith("fine")
