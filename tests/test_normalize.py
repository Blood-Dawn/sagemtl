# Blood-Dawn — tests
from sagemtl.clean.text_normalize import basic_clean


def test_basic():
    s = "“Hello—world”  \n\nThis\u200b is… fine\r\n"
    out = basic_clean(s)
    assert '"' in out and "-" in out
    assert "\r" not in out and "\u200b" not in out
    assert out.endswith("\n") is False  # normalizer shouldn't force final LF
