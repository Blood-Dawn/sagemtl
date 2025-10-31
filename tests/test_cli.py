import subprocess, sys, textwrap, os, pathlib


def run_cli(args, stdin=""):
    p = subprocess.run(
        [sys.executable, "-m", "sagemtl", *args],
        input=stdin.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return p.stdout.decode()


def test_clean_stdin_stdout():
    out = run_cli(["clean"], "A—B  \n\n\nC")
    assert out == "A-B\n\nC\n"
