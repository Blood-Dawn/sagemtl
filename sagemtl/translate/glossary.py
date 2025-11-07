"""Glossary helpers for post-translation replacements."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(slots=True)
class GlossaryEntry:
    source: str
    target: str
    case_sensitive: bool = True
    word_boundary: bool = False
    notes: str = ""


def load_glossary(path: str | Path | None) -> List[GlossaryEntry]:
    """Load glossary from CSV or JSON file."""
    if not path:
        return []
    glossary_path = Path(path).expanduser()
    entries: List[GlossaryEntry] = []
    if not glossary_path.exists():
        return entries

    suffix = glossary_path.suffix.lower()

    if suffix == ".json":
        # Load from JSON
        data = json.loads(glossary_path.read_text(encoding="utf-8"))
        for item in data:
            if isinstance(item, dict):
                entries.append(
                    GlossaryEntry(
                        source=item.get("source", ""),
                        target=item.get("target", ""),
                        case_sensitive=item.get("case_sensitive", True),
                        word_boundary=item.get("word_boundary", False),
                        notes=item.get("notes", ""),
                    )
                )
    else:
        # Load from CSV (backward compatible)
        with glossary_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) < 2:
                    continue
                src, tgt = row[0].strip(), row[1].strip()
                if not src:
                    continue
                # Optional columns: case_sensitive, word_boundary, notes
                case_sensitive = row[2].lower() == "true" if len(row) > 2 else True
                word_boundary = row[3].lower() == "true" if len(row) > 3 else False
                notes = row[4] if len(row) > 4 else ""
                entries.append(
                    GlossaryEntry(
                        source=src, target=tgt, case_sensitive=case_sensitive, word_boundary=word_boundary, notes=notes
                    )
                )

    return entries


def save_glossary(path: str | Path, entries: List[GlossaryEntry]) -> None:
    """Save glossary to CSV or JSON file."""
    glossary_path = Path(path).expanduser()
    glossary_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = glossary_path.suffix.lower()

    if suffix == ".json":
        data = [
            {
                "source": entry.source,
                "target": entry.target,
                "case_sensitive": entry.case_sensitive,
                "word_boundary": entry.word_boundary,
                "notes": entry.notes,
            }
            for entry in entries
        ]
        glossary_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        # Save as CSV
        with glossary_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Source", "Target", "Case Sensitive", "Word Boundary", "Notes"])
            for entry in entries:
                writer.writerow(
                    [
                        entry.source,
                        entry.target,
                        str(entry.case_sensitive),
                        str(entry.word_boundary),
                        entry.notes,
                    ]
                )


def apply_glossary(text: str, entries: Iterable[GlossaryEntry]) -> str:
    """Apply glossary replacements with optional case-sensitivity and word boundaries."""
    output = text

    for entry in entries:
        if not entry.source:
            continue

        if entry.word_boundary:
            # Use word boundary regex
            pattern = r"\b" + re.escape(entry.source) + r"\b"
            flags = 0 if entry.case_sensitive else re.IGNORECASE
            output = re.sub(pattern, entry.target, output, flags=flags)
        else:
            # Simple replacement
            if entry.case_sensitive:
                output = output.replace(entry.source, entry.target)
            else:
                # Case-insensitive replace (preserve case of first occurrence)
                pattern = re.compile(re.escape(entry.source), re.IGNORECASE)
                output = pattern.sub(entry.target, output)

    return output
