from __future__ import annotations
import sys, argparse, pathlib
from sagemtl.clean.text_normalize import normalize_text


def _resolve_in(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return pathlib.Path(path).read_text(encoding="utf-8", errors="replace")


def _write_out(text: str, out_path: str | None) -> None:
    if not out_path or out_path == "-":
        sys.stdout.write(text)
    else:
        pathlib.Path(out_path).write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sagemtl", description="SageMTL toolchain CLI")
    sp = p.add_subparsers(dest="cmd", required=True)

    p_clean = sp.add_parser("clean", help="normalize text for MTL pipelines")
    p_clean.add_argument("--in", dest="inp", default="-", help="input file or '-' (stdin)")
    p_clean.add_argument("--out", dest="out", default="-", help="output file or '-' (stdout)")
    p_clean.add_argument("--no-smart", action="store_true", help="strip smart quotes/dashes")
    p_clean.add_argument("--collapse-ws", action="store_true", help="collapse whitespace")

    args = p.parse_args(argv)

    if args.cmd == "clean":
        raw = _resolve_in(args.inp)
        out = normalize_text(
            raw,
            strip_smart=args.no_smart,
            collapse_ws=args.collapse_ws,
        )
        _write_out(out, args.out)
        return 0

    p.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
