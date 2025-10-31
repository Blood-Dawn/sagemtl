# Kheiven D'Haiti — sagemtl CLI
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sagemtl.clean.text_normalize import normalize_text


def _read_text(path: str | None) -> str:
    # Always read as UTF-8 (stdin bytes → decode) to avoid cp1252 garble (Aâ€"B)
    if path and path != "-":
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    data = sys.stdin.buffer.read()
    return data.decode("utf-8", errors="ignore")


def _write_text(s: str, out_path: str | None) -> None:
    if out_path:
        Path(out_path).write_text(s, encoding="utf-8", newline="\n")
    else:
        sys.stdout.buffer.write(s.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sagemtl", description="Text cleaning/normalization utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_clean = sub.add_parser("clean", help="normalize text (stdin or file)")
    p_clean.add_argument("--in", dest="inp", default="-", help="input path or '-' for stdin")
    p_clean.add_argument("--out", dest="out", default=None, help="output path (default: stdout)")

    args = p.parse_args(argv)

    if args.cmd == "clean":
        src = _read_text(args.inp)
        out = normalize_text(src)  # returns LF + single trailing \n
        if not out.endswith("\n"):  # belt & suspenders; should already be true
            out += "\n"
        _write_text(out, args.out)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
