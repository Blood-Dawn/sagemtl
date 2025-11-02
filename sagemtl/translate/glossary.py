"""Glossary helpers for post-translation replacements."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(slots=True)
class GlossaryEntry:
    source: str
    target: str


def load_glossary(path: str | Path | None) -> List[GlossaryEntry]:
    if not path:
        return []
    glossary_path = Path(path).expanduser()
    entries: List[GlossaryEntry] = []
    if not glossary_path.exists():
        return entries
    with glossary_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if len(row) < 2:
                continue
            src, tgt = row[0].strip(), row[1].strip()
            if not src:
                continue
            entries.append(GlossaryEntry(source=src, target=tgt))
    return entries


def apply_glossary(text: str, entries: Iterable[GlossaryEntry]) -> str:
    output = text
    for entry in entries:
        output = output.replace(entry.source, entry.target)
    return output
