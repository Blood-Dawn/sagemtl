import sys, argparse, pathlib
from .clean.text_normalize import basic_clean

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="sagemtl",
        description="Clean MT output: normalize whitespace, quotes, and dashes."
    )
    p.add_argument("paths", nargs="*", help="Files or folders; if none, read STDIN")
    p.add_argument("--ascii", action="store_true", help="ASCII-fold output")
    p.add_argument("-o", "--out", help="Write to file (default: print)")

    args = p.parse_args(argv)
    data = ""

    if args.paths:
        texts = []
        for raw in args.paths:
            pth = pathlib.Path(raw)
            if pth.is_dir():
                for f in pth.rglob("*.txt"):
                    texts.append(f.read_text(encoding="utf-8", errors="ignore"))
            elif pth.exists():
                texts.append(pth.read_text(encoding="utf-8", errors="ignore"))
            else:
                print(f"[sagemtl] Skipping missing: {pth}", file=sys.stderr)
        data = "\n\n".join(texts)
    else:
        print("Paste text then Ctrl+Z+Enter (Windows) — I’ll pretend not to judge 😄")
        data = sys.stdin.read()

    out = basic_clean(data, fold_ascii=args.ascii)
    if args.out:
        pathlib.Path(args.out).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
