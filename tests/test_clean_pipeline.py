from __future__ import annotations

import json
from pathlib import Path

from sagemtl.clean.pipeline import CleanOptions, iter_clean_batch
from sagemtl.clean.text_normalize import NormalizeOptions


def test_iter_clean_batch_directory(tmp_path: Path) -> None:
    sample = tmp_path / "doc.txt"
    sample.write_text("“Hello”\r\n\r\n", encoding="utf-8")
    results = list(iter_clean_batch([tmp_path], options=CleanOptions()))
    assert results[0].text.endswith("\n")
    assert results[0].meta["source"].endswith("doc.txt")


def test_iter_clean_batch_jsonl(tmp_path: Path) -> None:
    jsonl = tmp_path / "docs.jsonl"
    jsonl.write_text(json.dumps({"text": "Hi"}) + "\n", encoding="utf-8")
    options = CleanOptions(normalize=NormalizeOptions(ensure_trailing_lf=False))
    results = list(iter_clean_batch([jsonl], options=options))
    assert results[0].text == "Hi"
    assert results[0].meta["source"].endswith("docs.jsonl")
