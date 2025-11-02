"""CLI tests for the Typer-based interface."""
from __future__ import annotations

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
    assert "clean" in result.stdout
    assert "crawl" in result.stdout
    assert "batch" in result.stdout
    assert "translate" in result.stdout
    assert "gui" in result.stdout


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
    assert "Hi there" in result.stdout


def test_batch_stub(tmp_path: Path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()
    result = runner.invoke(app, ["batch", "--in", str(in_dir), "--out", str(out_dir), "--op", "noop"])
    assert result.exit_code == 0
    assert "[batch] requested op 'noop'" in result.stdout


def test_translate_stub():
    result = runner.invoke(app, ["translate", "hello", "--src-lang", "en", "--tgt-lang", "fr", "--backend", "hf"])
    assert result.exit_code == 0
    assert "translate stub" in result.stdout
    assert "src=en" in result.stdout
    assert "tgt=fr" in result.stdout
    assert "backend=hf" in result.stdout


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
