# Kheiven D'Haiti — sagemtl CLI
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sagemtl.clean.text_normalize import normalize_text


def _read_text(p: str | None) -> str:
    if p and p != "-":
        return Path(p).read_text(encoding="utf-8", errors="ignore")
    return sys.stdin.read()


def _write_text(s: str, out_path: str | None) -> None:
    # force LF so tests don't see \r on Windows
    if not s.endswith("\n"):
        s += "\n"
    if out_path:
        Path(out_path).write_text(s, encoding="utf-8", newline="\n")
    else:
        sys.stdout.buffer.write(s.encode("utf-8"))


def cmd_clean(args: argparse.Namespace) -> int:
    src = _read_text(args.inp)
    out = normalize_text(src)
    _write_text(out, args.out)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    try:
        import importlib
        http = importlib.import_module("sagemtl.crawl.http")
        get_text = getattr(http, "get_text", None) or getattr(http, "fetch_text", None)
        if get_text is None:
            raise AttributeError("sagemtl.crawl.http does not provide 'get_text' or 'fetch_text'")
    except Exception as e:
        raise SystemExit("Install crawl extra: pip install -e .[crawl]") from e
    html = get_text(args.url, timeout=args.timeout)
    if args.clean:
        html = normalize_text(html)
    _write_text(html, args.out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sagemtl", description="MTL utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("clean", help="normalize text (stdin or file)")
    pc.add_argument("--in", dest="inp", default="-", help="path or '-' for stdin")
    pc.add_argument("--out", dest="out", default=None, help="output path")
    pc.set_defaults(func=cmd_clean)

    pf = sub.add_parser("fetch", help="HTTP GET (optionally --clean)")
    pf.add_argument("url")
    pf.add_argument("--timeout", type=float, default=20.0)
    pf.add_argument("--clean", action="store_true")
    pf.add_argument("--out", dest="out", default=None)
    pf.set_defaults(func=cmd_fetch)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(bool(args.func(args)))


if __name__ == "__main__":
    raise SystemExit(main())
