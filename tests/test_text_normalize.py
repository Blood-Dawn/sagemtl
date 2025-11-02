from sagemtl.clean.text_normalize import NormalizeOptions, normalize_text


def test_basic_cleanup():
    raw = "Hello\u00a0world—smart “quotes”!\r\n\r\n\r\nNext."
    out = normalize_text(raw)
    assert out == 'Hello world-smart "quotes"!\n\nNext.\n'


def test_toggle_features():
    raw = "“Dash—minus−test”"
    opts = NormalizeOptions(
        smart_quotes=False,
        em_dash=False,
        minus_sign=False,
        collapse_blank_lines=False,
        ensure_trailing_lf=False,
    )
    out = normalize_text(raw, options=opts)
    assert "“" in out and "—" in out and "−" in out
    assert out.endswith("\n") is False
