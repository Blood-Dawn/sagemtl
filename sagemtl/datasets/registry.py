"""Local dataset registry stored under ``~/.sagemtl/data``."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Sequence

DATA_ENV = "SAGEMTL_DATA_DIR"
DEFAULT_BASE = Path.home() / ".sagemtl" / "data"
REGISTRY_FILENAME = "datasets.json"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

DatasetFormat = Literal["jsonl", "csv"]
REQUIRED_FIELDS = {"id", "src"}


def _now() -> str:
    return datetime.utcnow().strftime(ISO_FORMAT)


def _base_dir() -> Path:
    override = os.environ.get(DATA_ENV)
    base = Path(override).expanduser() if override else DEFAULT_BASE
    base.mkdir(parents=True, exist_ok=True)
    return base


def _registry_path(base: Path) -> Path:
    return base / REGISTRY_FILENAME


@dataclass(slots=True)
class DatasetRecord:
    name: str
    filename: str
    format: DatasetFormat
    created_at: str = field(default_factory=_now)
    meta: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @property
    def path(self) -> Path:
        return _base_dir() / self.filename


class DatasetRegistry:
    """Manage dataset metadata and exports."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or _base_dir()
        self.registry_path = _registry_path(self.base_dir)
        self._datasets: Dict[str, DatasetRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.registry_path.exists():
            return
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        for raw in data.get("datasets", []):
            record = DatasetRecord(
                name=str(raw["name"]),
                filename=str(raw["filename"]),
                format=str(raw["format"]),
                created_at=str(raw.get("created_at", _now())),
                meta=dict(raw.get("meta", {})),
            )
            self._datasets[record.name] = record

    def _flush(self) -> None:
        payload = {"datasets": [record.to_dict() for record in self._datasets.values()]}
        self.registry_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def list(self) -> List[DatasetRecord]:
        return list(self._datasets.values())

    def add(
        self,
        name: str,
        source: Path,
        *,
        fmt: DatasetFormat | None = None,
        meta: Dict[str, object] | None = None,
    ) -> DatasetRecord:
        source = source.expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(source)
        fmt = fmt or self._detect_format(source)
        filename = f"{self._safe_name(name)}.{fmt}"
        target = self.base_dir / filename
        rows = self._load_records(source, fmt)
        self._validate_rows(rows)
        self._write_dataset(rows, target, fmt)
        record = DatasetRecord(
            name=name, filename=filename, format=fmt, meta=meta or {}
        )
        self._datasets[name] = record
        self._flush()
        return record

    def export(self, name: str, fmt: DatasetFormat, out_path: Path) -> Path:
        if name not in self._datasets:
            raise KeyError(name)
        record = self._datasets[name]
        rows = self._load_records(record.path, record.format)
        out_path = out_path.expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_dataset(rows, out_path, fmt)
        return out_path

    def _detect_format(self, path: Path) -> DatasetFormat:
        suffix = path.suffix.lower()
        if suffix == ".jsonl":
            return "jsonl"
        if suffix == ".csv":
            return "csv"
        raise ValueError(f"Unsupported dataset format: {path.suffix}")

    def _safe_name(self, name: str) -> str:
        slug = "".join(
            ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in name.lower()
        )
        return slug.strip("-") or "dataset"

    def _load_records(self, path: Path, fmt: DatasetFormat) -> List[Dict[str, object]]:
        if fmt == "jsonl":
            records: List[Dict[str, object]] = []
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    records.append(payload)
            return records
        if fmt == "csv":
            with path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                return [dict(row) for row in reader]
        raise ValueError(fmt)

    def _write_dataset(
        self, rows: Sequence[Dict[str, object]], path: Path, fmt: DatasetFormat
    ) -> None:
        if fmt == "jsonl":
            with path.open("w", encoding="utf-8", newline="\n") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            return
        if fmt == "csv":
            if not rows:
                headers = sorted(REQUIRED_FIELDS | {"tgt", "meta"})
            else:
                headers = sorted({key for row in rows for key in row.keys()})
            with path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=headers)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            return
        raise ValueError(fmt)

    def _validate_rows(self, rows: Iterable[Dict[str, object]]) -> None:
        for idx, row in enumerate(rows):
            missing = REQUIRED_FIELDS - row.keys()
            if missing:
                raise ValueError(
                    f"Row {idx} missing required fields: {sorted(missing)}"
                )
            meta = row.get("meta")
            if meta is not None and not isinstance(meta, dict):
                raise ValueError(f"Row {idx} has non-dict meta field")


_registry_singleton: DatasetRegistry | None = None


def get_dataset_registry() -> DatasetRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = DatasetRegistry()
    return _registry_singleton
