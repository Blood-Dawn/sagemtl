# Kheiven D'Haiti — sagemtl CLI
import argparse, pathlib, sys, json
from sagemtl.crawl.http import grab
from sagemtl.clean.text import clean_text
from sagemtl.mtl.translate import get_translator

def _p(path: str) -> pathlib.Path:
    return pathlib.Path(path).expanduser().resolve()

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="sagemtl",
        description="Crawl -> Clean -> Translate pipeline"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_crawl = sub.add_parser("crawl", help="Fetch a URL to data/raw")
    p_crawl.add_argument("url", nargs="?", help="Source URL")
    p_crawl.add_argument("-o","--out", default="data/raw/input.txt",
                         help="Output file path")

    p_clean = sub.add_parser("clean", help="Normalize text to data/clean")
    p_clean.add_argument("inp", help="Input text file")
    p_clean.add_argument("-o","--out", default="data/clean/clean.txt")

    p_tx = sub.add_parser("translate", help="Translate text file")
    p_tx.add_argument("inp", help="Input text file")
    p_tx.add_argument("-o","--out", default="data/mtl/output.txt")
    p_tx.add_argument("--backend", choices=["hf","ct2"], default="hf",
                      help="hf=Transformers, ct2=CTranslate2")
    p_tx.add_argument("--model", default="Helsinki-NLP/opus-mt-zh-en",
                      help="HF model name or CT2 dir")
    p_tx.add_argument("--device", default="auto",
                      help="auto, cpu, or cuda")

    args = parser.parse_args(argv)

    if args.cmd == "crawl":
        url = args.url or input("Drop your URL here, brave explorer: ")
        text = grab(url)
        _p(args.out).parent.mkdir(parents=True, exist_ok=True)
        _p(args.out).write_text(text, encoding="utf-8")
        print(f"[crawl] wrote {_p(args.out)}")

    elif args.cmd == "clean":
        text = _p(args.inp).read_text(encoding="utf-8")
        out = clean_text(text)
        _p(args.out).parent.mkdir(parents=True, exist_ok=True)
        _p(args.out).write_text(out, encoding="utf-8")
        print(f"[clean] wrote {_p(args.out)}")

    elif args.cmd == "translate":
        text = _p(args.inp).read_text(encoding="utf-8")
        translator = get_translator(backend=args.backend, model=args.model, device=args.device)
        out = translator.translate(text)
        _p(args.out).parent.mkdir(parents=True, exist_ok=True)
        _p(args.out).write_text(out, encoding="utf-8")
        meta = {"backend": args.backend, "model": args.model, "device": translator.device}
        _p(_p(args.out).with_suffix(".json")).write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"[tx] wrote {_p(args.out)} and meta json")

if __name__ == "__main__":
    main()
