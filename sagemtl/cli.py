# Blood-Dawn — sagemtl CLI
from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional
from urllib.request import urlopen

import typer

from sagemtl.clean.text_normalize import normalize_text
from sagemtl.crawl.extract import extract_main_text

app = typer.Typer(help="SageMTL utilities")


def _read_text(path: Optional[str]) -> str:
    if path and path != "-":
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    # Read raw bytes from stdin and decode as UTF-8 to avoid mojibake on Windows.
    stream = getattr(sys.stdin, "buffer", sys.stdin)
    data = stream.read()
    if isinstance(data, str):
        return data
    return data.decode("utf-8", errors="ignore")


def _write_text(text: str, out_path: Optional[Path | str]) -> None:
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8", newline="\n")
        return
    stream = getattr(sys.stdout, "buffer", sys.stdout)
    try:
        stream.write(text)  # type: ignore[arg-type]
    except TypeError:
        stream.write(text.encode("utf-8"))


@app.command(help="Normalize text from stdin or a file")
def clean(
    inp: Annotated[str, typer.Option("--in", "-i", help="Input path or '-' for stdin")] = "-",
    out: Annotated[Optional[Path], typer.Option("--out", "-o", help="Output path (default: stdout)")] = None,
) -> None:
    src = _read_text(inp)
    out_text = normalize_text(src)
    if not out_text.endswith("\n"):
        out_text += "\n"
    _write_text(out_text, out)


@app.command(help="Extract text from HTML provided as a file or fetched from a URL")
def crawl(
    url: Annotated[Optional[str], typer.Option("--url", help="HTTP(S) URL to crawl")]=None,
    file: Annotated[Optional[Path], typer.Option("--file", help="HTML file path")]=None,
    out: Annotated[Optional[Path], typer.Option("--out", "-o", help="Output path (default: stdout)")] = None,
) -> None:
    if bool(url) == bool(file):
        raise typer.BadParameter("Provide exactly one of --url or --file.")

    if file is not None:
        html = file.read_text(encoding="utf-8", errors="ignore")
    else:
        assert url is not None
        with urlopen(url) as response:  # type: ignore[arg-type]
            data = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
        html = data.decode(charset, errors="ignore")

    text = extract_main_text(html)
    _write_text(text, out)


@app.command(help="Run a batch operation across a directory of inputs")
def batch(
    in_dir: Annotated[Path, typer.Option("--in", "-i", exists=True, file_okay=False, readable=True, resolve_path=True, help="Input directory")],
    out_dir: Annotated[Path, typer.Option("--out", "-o", file_okay=False, resolve_path=True, help="Output directory")],
    op: Annotated[str, typer.Option("--op", help="Batch operation to run (e.g. crawl)")] = "crawl",
    glob: Annotated[str, typer.Option("--glob", help="Glob pattern for selecting inputs")] = "*.html",
    jsonl: Annotated[
        bool,
        typer.Option(
            "--jsonl/--no-jsonl",
            help="Also write texts.jsonl",
            show_default=False,
        ),
    ] = False,
) -> None:
    operation = op.lower()
    if operation == "crawl":
        from sagemtl.crawl.batch import process_dir

        stats = process_dir(str(in_dir), str(out_dir), glob, jsonl)
        typer.echo(f"Wrote {stats['processed']} files to {stats['outdir']}")
        return

    typer.echo(
        f"[batch] requested op '{op}' with inputs from {in_dir} to {out_dir}"
    )


@app.command(help="Stub translation command that logs provided parameters")
def translate(
    text: Annotated[str, typer.Argument(help="Text to translate")],
    src_lang: Annotated[str, typer.Option("--src-lang", help="Source language code")] = "en",
    tgt_lang: Annotated[str, typer.Option("--tgt-lang", help="Target language code")] = "fr",
    backend: Annotated[Optional[str], typer.Option("--backend", help="Translation backend override")]=None,
) -> None:
    backend_name = backend or "auto"
    typer.echo(
        f"translate stub | src={src_lang} tgt={tgt_lang} backend={backend_name} text={text}"
    )


def _launch_gui() -> int:
    try:
        from textual.app import App, ComposeResult
        from textual.widgets import Static
    except ModuleNotFoundError:
        typer.secho(
            "Textual is required for the GUI. Install textual>=0.44 to use this command.",
            err=True,
            fg=typer.colors.RED,
        )
        return 1

    class SageMTLApp(App):
        TITLE = "SageMTL"

        def compose(self) -> ComposeResult:  # type: ignore[override]
            yield Static("SageMTL GUI stub")

        def on_mount(self) -> None:  # type: ignore[override]
            self.exit(message="SageMTL GUI closed")

    typer.echo("Launching SageMTL Textual GUI...")
    SageMTLApp().run()
    return 0


@app.command(help="Launch the Textual-based SageMTL GUI")
def gui() -> None:
    exit_code = _launch_gui()
    if exit_code != 0:
        raise typer.Exit(exit_code)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
