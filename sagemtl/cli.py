"""Typer-based CLI exposing cleaning, crawling, translation and admin tasks."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Annotated, Optional

import typer

from sagemtl.clean.pipeline import iter_clean_batch
from sagemtl.clean.text import CleanOptions, clean_text_with_meta
from sagemtl.clean.text_normalize import NormalizeOptions
from sagemtl.config import load_config, save_config, update_config
from sagemtl.crawl.http import fetch_text
from sagemtl.crawl.pipeline import CrawlOptions, crawl_html
from sagemtl.datasets.registry import DatasetFormat, get_dataset_registry
from sagemtl.jobs.store import get_job_store
from sagemtl.translate import TranslationRequest, get_translation_queue

app = typer.Typer(help="SageMTL utilities", no_args_is_help=True)
clean_app = typer.Typer(help="Clean text sources", invoke_without_command=True)
crawl_app = typer.Typer(help="Crawl web pages and novels")
datasets_app = typer.Typer(help="Manage local datasets")
jobs_app = typer.Typer(help="Inspect translation jobs")
settings_app = typer.Typer(help="View and edit configuration")
app.add_typer(clean_app, name="clean")
app.add_typer(crawl_app, name="crawl")
app.add_typer(datasets_app, name="datasets")
app.add_typer(jobs_app, name="jobs")
app.add_typer(settings_app, name="settings")


def _read_text(path: Optional[str]) -> str:
    if path and path != "-":
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    stream = getattr(sys.stdin, "buffer", sys.stdin)
    data = stream.read()
    if isinstance(data, str):
        return data
    return data.decode("utf-8", errors="ignore")


def _write_text(text: str, out_path: Optional[Path | str]) -> None:
    if out_path and out_path != Path("-"):
        Path(out_path).write_text(text, encoding="utf-8", newline="\n")
        return
    stream = getattr(sys.stdout, "buffer", sys.stdout)
    try:
        stream.write(text)  # type: ignore[arg-type]
    except TypeError:
        stream.write(text.encode("utf-8"))


def _normalize_options(
    *,
    smart_quotes: bool,
    em_dash: bool,
    minus_sign: bool,
    zero_width: bool,
    nbsp_to_space: bool,
    collapse_blank_lines: bool,
    ensure_trailing_lf: bool,
) -> NormalizeOptions:
    return NormalizeOptions(
        smart_quotes=smart_quotes,
        em_dash=em_dash,
        minus_sign=minus_sign,
        zero_width=zero_width,
        nbsp_to_space=nbsp_to_space,
        collapse_blank_lines=collapse_blank_lines,
        ensure_trailing_lf=ensure_trailing_lf,
    )


def clean_run(
    inp: Annotated[str, typer.Option("--in", "-i", help="Input path or '-' for stdin")] = "-",
    out: Annotated[Optional[Path], typer.Option("--out", "-o", help="Output path (default stdout)")] = None,
    smart_quotes: Annotated[bool, typer.Option("--smart-quotes/--no-smart-quotes")] = True,
    em_dash: Annotated[bool, typer.Option("--em-dash/--no-em-dash")] = True,
    minus_sign: Annotated[bool, typer.Option("--minus/--no-minus")] = True,
    zero_width: Annotated[bool, typer.Option("--zero-width/--keep-zero-width")] = True,
    nbsp_to_space: Annotated[bool, typer.Option("--nbsp/--keep-nbsp")] = True,
    collapse_blank_lines: Annotated[
        bool,
        typer.Option("--collapse-blank-lines/--keep-blank-lines"),
    ] = True,
    ensure_trailing_lf: Annotated[
        bool,
        typer.Option("--ensure-trailing-lf/--no-ensure-trailing-lf"),
    ] = True,
) -> None:
    options = _normalize_options(
        smart_quotes=smart_quotes,
        em_dash=em_dash,
        minus_sign=minus_sign,
        zero_width=zero_width,
        nbsp_to_space=nbsp_to_space,
        collapse_blank_lines=collapse_blank_lines,
        ensure_trailing_lf=ensure_trailing_lf,
    )
    src = _read_text(inp)
    result = clean_text_with_meta(src, options=CleanOptions(normalize=options))
    _write_text(result.text, out)


@clean_app.callback()
def clean_callback(
    ctx: typer.Context,
    inp: Annotated[str, typer.Option("--in", "-i", help="Input path or '-' for stdin")] = "-",
    out: Annotated[Optional[Path], typer.Option("--out", "-o", help="Output path (default stdout)")] = None,
    smart_quotes: Annotated[bool, typer.Option("--smart-quotes/--no-smart-quotes")] = True,
    em_dash: Annotated[bool, typer.Option("--em-dash/--no-em-dash")] = True,
    minus_sign: Annotated[bool, typer.Option("--minus/--no-minus")] = True,
    zero_width: Annotated[bool, typer.Option("--zero-width/--keep-zero-width")] = True,
    nbsp_to_space: Annotated[bool, typer.Option("--nbsp/--keep-nbsp")] = True,
    collapse_blank_lines: Annotated[
        bool,
        typer.Option("--collapse-blank-lines/--keep-blank-lines"),
    ] = True,
    ensure_trailing_lf: Annotated[
        bool,
        typer.Option("--ensure-trailing-lf/--no-ensure-trailing-lf"),
    ] = True,
) -> None:
    if ctx.invoked_subcommand is None:
        clean_run(
            inp=inp,
            out=out,
            smart_quotes=smart_quotes,
            em_dash=em_dash,
            minus_sign=minus_sign,
            zero_width=zero_width,
            nbsp_to_space=nbsp_to_space,
            collapse_blank_lines=collapse_blank_lines,
            ensure_trailing_lf=ensure_trailing_lf,
        )


@clean_app.command("run", help="Clean a single text input")
def clean_command(**kwargs) -> None:  # type: ignore[no-untyped-def]
    clean_run(**kwargs)  # type: ignore[arg-type]


@clean_app.command("batch", help="Batch clean inputs and emit JSONL")
def clean_batch(
    inputs: Annotated[
        list[Path],
        typer.Argument(help="Input files/directories", exists=True, resolve_path=True),
    ],
    out: Annotated[Path, typer.Option("--out", "-o", help="Output JSONL", resolve_path=True)] = Path("clean.jsonl"),
    smart_quotes: Annotated[bool, typer.Option("--smart-quotes/--no-smart-quotes")] = True,
    em_dash: Annotated[bool, typer.Option("--em-dash/--no-em-dash")] = True,
    minus_sign: Annotated[bool, typer.Option("--minus/--no-minus")] = True,
    zero_width: Annotated[bool, typer.Option("--zero-width/--keep-zero-width")] = True,
    nbsp_to_space: Annotated[bool, typer.Option("--nbsp/--keep-nbsp")] = True,
    collapse_blank_lines: Annotated[
        bool,
        typer.Option("--collapse-blank-lines/--keep-blank-lines"),
    ] = True,
    ensure_trailing_lf: Annotated[
        bool,
        typer.Option("--ensure-trailing-lf/--no-ensure-trailing-lf"),
    ] = True,
) -> None:
    options = _normalize_options(
        smart_quotes=smart_quotes,
        em_dash=em_dash,
        minus_sign=minus_sign,
        zero_width=zero_width,
        nbsp_to_space=nbsp_to_space,
        collapse_blank_lines=collapse_blank_lines,
        ensure_trailing_lf=ensure_trailing_lf,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        for result in iter_clean_batch(inputs, options=CleanOptions(normalize=options)):
            fh.write(json.dumps({"text": result.text, "meta": result.meta}, ensure_ascii=False) + "\n")
    typer.echo(f"Wrote {out}")


@app.command(help="Extract structured text blocks from HTML")
def crawl(
    url: Annotated[Optional[str], typer.Option("--url", help="HTTP(S) URL to crawl")] = None,
    file: Annotated[
        Optional[Path],
        typer.Option("--file", help="HTML file path", exists=True, resolve_path=True),
    ] = None,
    depth: Annotated[int, typer.Option(help="Link depth (currently informational)")] = 0,
    render_js: Annotated[bool, typer.Option("--render-js/--no-render-js")] = False,
    allow_selector: Annotated[
        list[str],
        typer.Option("--allow", help="CSS selector allow-list", show_default=False),
    ] = [],
    block_selector: Annotated[
        list[str],
        typer.Option("--block", help="CSS selector block-list", show_default=False),
    ] = [],
    out: Annotated[Optional[Path], typer.Option("--out", "-o", help="Output JSON path")] = None,
) -> None:
    if bool(url) == bool(file):
        raise typer.BadParameter("Provide exactly one of --url or --file.")
    if url:
        html = fetch_text(url)
        source = url
    else:
        assert file is not None
        html = file.read_text(encoding="utf-8", errors="ignore")
        source = str(file)
    options = CrawlOptions(
        depth=depth,
        render_js=render_js,
        allow_selectors=allow_selector,
        block_selectors=block_selector,
        normalize=NormalizeOptions(ensure_trailing_lf=False),
    )
    result = crawl_html(html, source=source, options=options)
    payload = {
        "source": source,
        "meta": result.meta,
        "blocks": [
            {
                "order": block.order,
                "text": block.text,
                "css_path": block.css_path,
                "xpath": block.xpath,
                "lang": block.lang,
            }
            for block in result.blocks
        ],
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _write_text(data, out)


@app.command(help="Queue a translation job (stub implementation)")
def translate(
    text: Annotated[str, typer.Argument(help="Text to translate")],
    src_lang: Annotated[str, typer.Option("--src-lang", help="Source language code")] = "en",
    tgt_lang: Annotated[str, typer.Option("--tgt-lang", help="Target language code")] = "fr",
    provider: Annotated[Optional[str], typer.Option("--provider", help="Translation backend override")] = None,
    glossary: Annotated[
        Optional[Path],
        typer.Option(
            "--glossary",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
            help="Glossary CSV",
        ),
    ] = None,
    wait: Annotated[bool, typer.Option("--wait/--no-wait", help="Wait for completion")] = False,
) -> None:
    queue = get_translation_queue()
    request = TranslationRequest(
        text=text,
        src_lang=src_lang,
        tgt_lang=tgt_lang,
        provider_name=provider,
        glossary_path=str(glossary) if glossary else None,
        meta={},
    )
    job = queue.enqueue(request)
    typer.echo(f"Queued translation job {job.id} ({job.status})")
    if wait:
        typer.echo("Waiting for completion...")
        while True:
            current = queue.get_job(job.id)
            if current and current.status.lower() not in {"queued", "running"}:
                break
            time.sleep(0.1)
        if current is None:
            raise typer.Exit(code=1)
        if current.status.lower() == "done" and current.result:
            typer.echo(current.result.get("text", ""))
        else:
            typer.echo(f"Job failed: {current.error}", err=True)
            raise typer.Exit(code=1)


@datasets_app.command("list", help="List registered datasets")
def datasets_list() -> None:
    registry = get_dataset_registry()
    for record in registry.list():
        typer.echo(f"{record.name}\t{record.format}\t{record.filename}")


@datasets_app.command("add", help="Register a dataset file")
def datasets_add(
    name: Annotated[str, typer.Argument(help="Dataset name")],
    path: Annotated[Path, typer.Argument(help="Dataset file", exists=True, resolve_path=True)],
    fmt: Annotated[Optional[DatasetFormat], typer.Option("--format", help="Input format override")] = None,
) -> None:
    registry = get_dataset_registry()
    record = registry.add(name, path, fmt=fmt)
    typer.echo(f"Registered {record.name} ({record.format}) -> {record.filename}")


@datasets_app.command("export", help="Export a dataset in a given format")
def datasets_export(
    name: Annotated[str, typer.Argument(help="Dataset name")],
    fmt: Annotated[DatasetFormat, typer.Option("--format", "-f")],
    out: Annotated[Path, typer.Option("--out", "-o", resolve_path=True)],
) -> None:
    registry = get_dataset_registry()
    registry.export(name, fmt, out)
    typer.echo(f"Wrote {out}")


@jobs_app.command("list", help="List known jobs")
def jobs_list() -> None:
    store = get_job_store()
    for job in store.list():
        typer.echo(f"{job.id}\t{job.type}\t{job.status}")


@jobs_app.command("tail", help="Show job logs and result")
def jobs_tail(job_id: Annotated[str, typer.Argument(help="Job identifier")]) -> None:
    store = get_job_store()
    job = store.get(job_id)
    if not job:
        raise typer.BadParameter(f"Unknown job {job_id}")
    if job.log:
        for line in job.log:
            typer.echo(line)
    typer.echo(f"Status: {job.status}")
    if job.result:
        typer.echo(json.dumps(job.result, ensure_ascii=False, indent=2))
    if job.error:
        typer.echo(f"Error: {job.error}", err=True)


@jobs_app.command("purge", help="Remove completed jobs")
def jobs_purge(
    keep_running: Annotated[
        bool,
        typer.Option("--keep-running/--purge-running", help="Keep queued/running jobs"),
    ] = True,
) -> None:
    store = get_job_store()
    statuses = {"queued", "running"} if keep_running else set()
    removed = store.purge(statuses=statuses)
    typer.echo(f"Removed {len(removed)} jobs")


@crawl_app.command("novel", help="Deprecated: SageCrawler removed; use lightnovel-crawler")
def crawl_novel(
    url: Annotated[str, typer.Argument(help="Novel URL")],
    start: Annotated[int, typer.Option("--start", "-s", help="Start chapter")] = 1,
    end: Annotated[Optional[int], typer.Option("--end", "-e", help="End chapter (default: all)")] = None,
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Dataset name")] = None,
    wait: Annotated[bool, typer.Option("--wait/--no-wait", help="Wait for completion")] = True,
) -> None:
    """Deprecated command: SageCrawler has been removed.

    Please use the desktop app (LightNovelCrawler integration) or
    install lightnovel-crawler and use its CLI/library.
    """
    typer.secho(
        "SageCrawler has been removed. Use LightNovelCrawler (desktop app) or lncrawl CLI.",
        fg=typer.colors.YELLOW,
    )
    raise typer.Exit(2)


@settings_app.command("show", help="Show current configuration")
def settings_show() -> None:
    config = load_config()
    typer.echo(json.dumps(config.model_dump(), ensure_ascii=False, indent=2))


@settings_app.command("set", help="Update a configuration value")
def settings_set(
    key: Annotated[str, typer.Argument(help="Setting key")],
    value: Annotated[str, typer.Argument(help="JSON-serialisable value")],
) -> None:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value
    new_settings = update_config({key: parsed})
    save_config(new_settings)
    typer.echo(f"Updated {key}")


@app.command(help="Launch the FastAPI service")
def serve(
    host: Annotated[str, typer.Option("--host", help="Bind address")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="TCP port")] = 8000,
    v2: Annotated[bool, typer.Option("--v2", help="Use v2 API with modular routers")] = True,
) -> None:
    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise typer.BadParameter("uvicorn is required to use the serve command") from exc

    api_module = "sagemtl.serve.api_v2:app" if v2 else "sagemtl.serve.api:app"
    typer.echo(f"Starting SageMTL API {'v2' if v2 else 'v1'} on http://{host}:{port}")
    uvicorn.run(api_module, host=host, port=port)


@app.command(help="Launch the Textual-based terminal UI")
def tui() -> None:
    try:
        from sagemtl.tui.app import SageMTLApp
    except ModuleNotFoundError:
        typer.secho(
            "Textual is required for the TUI. Install with: pip install sagemtl[tui]",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    try:
        SageMTLApp().run()
    except Exception as exc:
        typer.secho(f"TUI error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
