# Kheiven D\'Haiti — CLI crawl test (local file)
import subprocess
import sys


def run_cli(args):
    p = subprocess.run(
        [sys.executable, "-m", "sagemtl", *args], capture_output=True, check=True
    )
    return p.stdout.decode()


def test_cli_crawl_file():
    out = run_cli(["crawl", "--file", "tests/data/sample.html"])
    assert 'Hello world-smart "quotes"!' in out
