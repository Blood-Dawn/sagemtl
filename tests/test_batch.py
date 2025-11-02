"""Tests for the threaded batch runner."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from sagemtl.batch.runner import run_batch
from sagemtl.clean.text_normalize import normalize_text


def test_run_batch_processes_files_and_jsonl(tmp_path: Path) -> None:
    files: list[Path] = []
    payloads = ["Hello—world", "Line1\r\n\r\nLine2"]
    for idx, content in enumerate(payloads):
        file = tmp_path / f"doc{idx}.txt"
        file.write_text(content, encoding="utf-8")
        files.append(file)

    jsonl_path = tmp_path / "texts.jsonl"
    runner = run_batch(normalize_text, files, jsonl_path, workers=2)
    results = list(runner)

    assert len(results) == len(payloads)
    assert all("source" in r and "text" in r and "sha256" in r for r in results)
    assert all(r["text"].endswith("\n") for r in results)

    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(payloads)
    entries = [json.loads(line) for line in lines]
    assert {entry["source"] for entry in entries} == {str(p) for p in files}

    by_source = {entry["source"]: entry for entry in entries}
    for record in results:
        stored = by_source[record["source"]]
        assert stored["text"] == record["text"]
        assert stored["sha256"] == record["sha256"]


def test_run_batch_deduplicates_inputs(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "texts.jsonl"
    calls = 0

    def uppercase(text: str) -> str:
        nonlocal calls
        calls += 1
        return text.upper()

    inputs = [
        ("a.txt", "same text"),
        ("b.txt", "same text"),
        ("c.txt", "different"),
    ]

    runner = run_batch(uppercase, inputs, jsonl_path, workers=2)
    results = list(runner)

    assert calls == 2  # second identical payload should reuse cached result
    assert runner.stats["duplicates"] == 1
    assert len(results) == len(inputs)

    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(inputs)
    entries = [json.loads(line) for line in lines]
    duplicates = [entry for entry in entries if entry["duplicate"]]
    assert len(duplicates) == 1
    dup_entry = duplicates[0]
    expected = next(r for r in results if r["source"] == dup_entry["source"])
    assert dup_entry["text"] == expected["text"]


def test_run_batch_cancellation(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "texts.jsonl"
    inputs = [(tmp_path / f"f{i}.txt", "payload") for i in range(5)]

    def slow(text: str) -> str:
        time.sleep(0.05)
        return text[::-1]

    runner = run_batch(slow, inputs, jsonl_path, workers=2)
    first = next(runner)
    assert first["text"] == "daolyap"

    runner.close()
    assert runner.cancelled
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["source"] == first["source"]

    with pytest.raises(StopIteration):
        next(runner)
