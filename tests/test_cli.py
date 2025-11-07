"""CLI tests for the Typer-based interface."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sagemtl.cli import app


runner = CliRunner()


def run_module(args: list[str], stdin: str = "") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "sagemtl", *args],
        input=stdin.encode(),
        capture_output=True,
        check=False,
    )


def test_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in [
        "clean",
        "crawl",
        "datasets",
        "jobs",
        "settings",
        "serve",
        "translate",
        "gui",
    ]:
        assert command in result.stdout


def test_clean_stdin_stdout():
    result = runner.invoke(app, ["clean"], input="A—B  \r\n\r\n\r\nC")
    assert result.exit_code == 0
    assert result.stdout == "A-B\n\nC\n"


def test_clean_file(tmp_path: Path):
    source = tmp_path / "x.txt"
    source.write_text("“Yo—yo”\r\n", encoding="utf-8", newline="\r\n")
    result = runner.invoke(app, ["clean", "--in", str(source)])
    assert result.exit_code == 0
    assert result.stdout == '"Yo-yo"\n'


def test_module_entrypoint(tmp_path: Path):
    source = tmp_path / "x.txt"
    source.write_text("Alpha", encoding="utf-8")
    completed = run_module(["clean", "--in", str(source)])
    assert completed.returncode == 0
    assert completed.stdout.decode() == "Alpha\n"


def test_crawl_requires_single_source(tmp_path: Path):
    html = tmp_path / "page.html"
    html.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    result = runner.invoke(app, ["crawl", "--file", str(html), "--url", "https://example.com"])
    assert result.exit_code != 0
    assert "Provide exactly one" in result.stdout or "Provide exactly one" in result.stderr


def test_crawl_file_uses_extract(tmp_path: Path):
    html = tmp_path / "page.html"
    html.write_text("<html><body><main>Hi there</main></body></html>", encoding="utf-8")
    result = runner.invoke(app, ["crawl", "--file", str(html)])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["blocks"][0]["text"].startswith("Hi there")


def test_clean_batch_command(tmp_path: Path):
    text_file = tmp_path / "doc.txt"
    text_file.write_text("“Hello”", encoding="utf-8")
    out_path = tmp_path / "clean.jsonl"
    result = runner.invoke(app, ["clean", "batch", str(text_file), "--out", str(out_path)])
    assert result.exit_code == 0
    assert out_path.exists()
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["text"].startswith('"Hello"')


def test_translate_stub():
    result = runner.invoke(
        app,
        [
            "translate",
            "hello",
            "--src-lang",
            "en",
            "--tgt-lang",
            "fr",
            "--provider",
            "echo",
            "--wait",
        ],
    )
    assert result.exit_code == 0
    assert "Queued translation job" in result.stdout
    assert "hello" in result.stdout


@pytest.mark.parametrize("exit_code", [0, 5])
def test_gui_respects_launch_exit_code(monkeypatch: pytest.MonkeyPatch, exit_code: int):
    calls: list[int] = []

    def fake_launch() -> int:
        calls.append(1)
        return exit_code

    monkeypatch.setattr("sagemtl.cli._launch_gui", fake_launch)
    result = runner.invoke(app, ["gui"])
    assert calls == [1]
    if exit_code == 0:
        assert result.exit_code == 0
    else:
        assert result.exit_code == exit_code
