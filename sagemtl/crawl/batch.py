# Blood-Dawn — batch HTML extractor
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from sagemtl.batch.runner import run_batch
from sagemtl.crawl.extract import extract_main_text


def _iter_html(indir: str, glob: str) -> Iterable[Path]:
    base = Path(indir)
    if "**" in glob:
        yield from base.rglob(glob.replace("**/", ""))
    else:
        yield from base.glob(glob)


def process_dir(
    indir: str,
    outdir: str,
    glob: str = "*.html",
    jsonl: bool = False,
    *,
    workers: int = 4,
) -> dict:
    src = Path(indir)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    jsonl_path = out / "texts.jsonl" if jsonl else None

    def _load_inputs():
        for path in _iter_html(str(src), glob):
            html = path.read_text(encoding="utf-8", errors="ignore")
            yield str(path), html

    runner = run_batch(extract_main_text, _load_inputs(), jsonl_path, workers=workers)
    for record in runner:
        src_path = Path(record["source"])
        text = record["text"]
        (out / f"{src_path.stem}.txt").write_text(text, encoding="utf-8", newline="\n")

    stats = runner.stats.copy()
    stats["outdir"] = str(out.resolve())
    stats["jsonl"] = str(jsonl_path) if jsonl_path else None
    return stats
