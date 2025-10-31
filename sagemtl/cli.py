# Kheiven D''Haiti — sagemtl CLI (Windows-safe)
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sagemtl.clean.text_normalize import normalize_text
from sagemtl.crawl.extract import extract_main_text


def _read_text(path: str | None) -> str:
    if path and path != "-":
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    # Read raw bytes from stdin, decode as UTF-8 to avoid mojibake on Windows
    data = sys.stdin.buffer.read()
    return data.decode("utf-8", "replace")


def _write_text(s: str, out_path: str | None) -> None:
    # Always emit LF newlines, UTF-8 bytes
    if not s.endswith("\n"):
        s += "\n"
    if out_path:
        Path(out_path).write_text(s, encoding="utf-8", newline="\n")
    else:
        sys.stdout.buffer.write(s.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sagemtl", description="Text cleaning / crawl utils")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_clean = sub.add_parser("clean", help="normalize text (stdin or file)")
    p_clean.add_argument("--in", dest="inp", default="-", help="input path or '-' for stdin")
    p_clean.add_argument("--out", dest="out", default=None, help="output path (default: stdout)")

    p_crawl = sub.add_parser("crawl", help="extract main text from HTML")
    g = p_crawl.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", dest="file", help="local HTML file path")
    g.add_argument("--url", dest="url", help="URL to fetch (basic httpx)")

    args = p.parse_args(argv)

    if args.cmd == "clean":
        src = _read_text(args.inp)
        out = normalize_text(src)
        _write_text(out, args.out)
        return 0

    if args.cmd == "crawl":
        if args.file:
            html = Path(args.file).read_text(encoding="utf-8", errors="ignore")
        else:
            # Lazy fetch to avoid adding deps; basic urllib
            import urllib.request
            with urllib.request.urlopen(args.url) as r:
                raw = r.read()
            html = raw.decode("utf-8", "replace")

        out = extract_main_text(html)
        _write_text(out, None)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
