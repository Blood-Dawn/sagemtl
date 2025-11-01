# Blood-Dawn — sagemtl CLI
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sagemtl.clean.text_normalize import normalize_text
from sagemtl.crawl.extract import extract_main_text


def _read_text(path: str | None) -> str:
    if path and path != "-":
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    # Read raw bytes from stdin and decode as UTF-8 to avoid mojibake on Windows
    data = sys.stdin.buffer.read()
    return data.decode("utf-8", errors="ignore")


def _write_text(s: str, out_path: str | None) -> None:
    if out_path:
        Path(out_path).write_text(s, encoding="utf-8", newline="\n")
    else:
        sys.stdout.buffer.write(s.encode("utf-8"))


def _cmd_clean(inp: str, out: str | None) -> int:
    src = _read_text(inp)
    out_text = normalize_text(src)
    if not out_text.endswith("\n"):
        out_text += "\n"
    _write_text(out_text, out)
    return 0


def _cmd_crawl_file(file: str, out: str | None) -> int:
    html = Path(file).read_text(encoding="utf-8", errors="ignore")
    text = extract_main_text(html)
    _write_text(text, out)
    return 0


def _cmd_crawl_batch(indir: str, glob: str, outdir: str, jsonl: bool) -> int:
    from sagemtl.crawl.batch import process_dir

    stats = process_dir(indir, outdir, glob, jsonl)
    sys.stdout.write(f"Wrote {stats['processed']} files to {stats['outdir']}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sagemtl", description="SageMTL utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_clean = sub.add_parser("clean", help="normalize text (stdin or file)")
    p_clean.add_argument(
        "--in", dest="inp", default="-", help="input path or '-' for stdin"
    )
    p_clean.add_argument(
        "--out", dest="out", default=None, help="output path (default: stdout)"
    )

    p_crawl = sub.add_parser("crawl", help="extract text from a single HTML file")
    p_crawl.add_argument("--file", required=True, help="HTML file path")
    p_crawl.add_argument("--out", default=None, help="output path (default: stdout)")

    p_batch = sub.add_parser("crawl-batch", help="extract text for many HTML files")
    p_batch.add_argument("--indir", required=True, help="directory of HTML files")
    p_batch.add_argument(
        "--glob", default="*.html", help="pattern (e.g., *.html or **\\*.html)"
    )
    p_batch.add_argument(
        "--outdir", required=True, help="where to write .txt (and JSONL)"
    )
    p_batch.add_argument("--jsonl", action="store_true", help="also write texts.jsonl")

    args = p.parse_args(argv)
    if args.cmd == "clean":
        return _cmd_clean(args.inp, args.out)
    if args.cmd == "crawl":
        return _cmd_crawl_file(args.file, args.out)
    if args.cmd == "crawl-batch":
        return _cmd_crawl_batch(args.indir, args.glob, args.outdir, args.jsonl)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
