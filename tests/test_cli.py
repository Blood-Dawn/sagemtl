# Kheiven D'Haiti — CLI tests
import subprocess
import sys
from pathlib import Path


def run_cli(args, stdin=""):
    p = subprocess.run(
        [sys.executable, "-m", "sagemtl", *args],
        input=stdin.encode(),
        capture_output=True,
        check=True,
    )
    return p.stdout.decode()

def test_clean_stdin_stdout(tmp_path: Path):
    out = run_cli(["clean"], "A—B  \r\n\r\n\r\nC")
    assert out == "A-B\n\nC\n"

def test_clean_file(tmp_path: Path):
    f = tmp_path / "x.txt"
    f.write_text("“Yo—yo”\r\n", encoding="utf-8", newline="\r\n")
    out = run_cli(["clean", "--in", str(f)])
    assert out == "\"Yo-yo\"\n"
