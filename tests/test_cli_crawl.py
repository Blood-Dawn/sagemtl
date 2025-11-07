# Kheiven D\'Haiti — CLI crawl test (local file)
import json
import subprocess
import sys

SAMPLE_HTML = """<!DOCTYPE html>\n<html lang=\"en\">\n  <body>\n    <article>\n      <h1>Hello world-smart “quotes”!</h1>\n      <p>Example paragraph.</p>\n    </article>\n  </body>\n</html>\n"""


def run_cli(args):
    p = subprocess.run([sys.executable, "-m", "sagemtl", *args], capture_output=True, check=True)
    return p.stdout.decode()


def test_cli_crawl_file(tmp_path):
    html_file = tmp_path / "sample.html"
    html_file.write_text(SAMPLE_HTML, encoding="utf-8")
    out = run_cli(["crawl", "--file", str(html_file)])
    payload = json.loads(out)
    assert any('Hello world-smart "quotes"!' in block["text"] for block in payload["blocks"])
