# Blood-Dawn — batch HTML extractor
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from sagemtl.crawl.extract import extract_main_text


def _iter_html(indir: str, glob: str) -> Iterable[Path]:
    base = Path(indir)
    if "**" in glob:
        yield from base.rglob(glob.replace("**/", ""))
    else:
        yield from base.glob(glob)


def process_dir(
    indir: str, outdir: str, glob: str = "*.html", jsonl: bool = False
) -> dict:
    src = Path(indir)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    jfh = (
        (out / "texts.jsonl").open("w", encoding="utf-8", newline="\n")
        if jsonl
        else None
    )
    for p in _iter_html(str(src), glob):
        html = p.read_text(encoding="utf-8", errors="ignore")
        text = extract_main_text(html)
        (out / f"{p.stem}.txt").write_text(text, encoding="utf-8", newline="\n")
        if jfh:
            jfh.write(
                json.dumps({"source": str(p), "text": text}, ensure_ascii=False) + "\n"
            )
        n += 1
    if jfh:
        jfh.close()
    return {"processed": n, "outdir": str(out.resolve())}
