"""High-level cleaning pipeline used by the CLI and HTTP bridge."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from functools import partial
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Sequence

from .text_normalize import NormalizeOptions, normalize_text

__all__ = [
    "CleanOptions",
    "CleanResult",
    "clean_text",
    "iter_clean_batch",
]


@dataclass(slots=True)
class CleanOptions:
    """Options exposed via the CLI and HTTP API."""

    normalize: NormalizeOptions = field(default_factory=NormalizeOptions)


@dataclass(slots=True)
class CleanResult:
    """Result bundle produced by :func:`clean_text`."""

    text: str
    meta: Dict[str, Any]


def clean_text(
    text: str,
    *,
    options: CleanOptions | None = None,
    meta: Dict[str, Any] | None = None,
) -> CleanResult:
    """Clean a single document returning the cleaned text and metadata."""

    opts = options or CleanOptions()
    cleaned = normalize_text(text, options=opts.normalize)
    metadata = dict(meta or {})
    metadata.setdefault("length", len(cleaned))
    return CleanResult(text=cleaned, meta=metadata)


def _load_jsonl(path: Path) -> Iterable[tuple[str, Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            payload = json.loads(line)
            text = payload.get("text", "")
            meta = {k: v for k, v in payload.items() if k != "text"}
            source = meta.setdefault("source", str(path))
            yield source, meta | {"text": text}


def _load_csv(
    path: Path, *, delimiter: str = ","
) -> Iterable[tuple[str, Dict[str, Any]]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        for row in reader:
            if "text" not in row:
                raise ValueError("CSV input must contain a 'text' column")
            meta = {k: v for k, v in row.items() if k != "text"}
            source = meta.get("id") or row.get("id") or str(path)
            meta.setdefault("source", source)
            yield source, meta | {"text": row["text"]}


def _load_directory(path: Path) -> Iterable[tuple[str, Dict[str, Any]]]:
    for entry in sorted(path.rglob("*")):
        if not entry.is_file():
            continue
        text = entry.read_text(encoding="utf-8", errors="ignore")
        meta = {"source": str(entry)}
        yield str(entry), {"text": text, **meta}


def iter_clean_batch(
    inputs: Sequence[Path], *, options: CleanOptions | None = None
) -> Iterator[CleanResult]:
    """Yield :class:`CleanResult` objects for the provided input paths."""

    opts = options or CleanOptions()
    for path in inputs:
        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_dir():
            loader = _load_directory
        elif path.suffix.lower() == ".jsonl":
            loader = _load_jsonl
        elif path.suffix.lower() in {".csv", ".tsv"}:
            delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
            loader = partial(_load_csv, delimiter=delimiter)
        else:
            loader = None

        if loader is None:
            text = path.read_text(encoding="utf-8", errors="ignore")
            meta = {"source": str(path)}
            yield clean_text(text, options=opts, meta=meta)
            continue

        for source, payload in loader(path):
            text = payload.pop("text", "")
            meta = {"source": source} | payload
            yield clean_text(text, options=opts, meta=meta)
