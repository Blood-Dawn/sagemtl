from sagemtl.clean.text_normalize import normalize_text


def test_basic_cleanup():
    raw = "Hello\u00a0world—smart “quotes”!\r\n\r\n\r\nNext."
    out = normalize_text(raw)
    assert out == 'Hello world-smart "quotes"!\n\nNext.\n'
