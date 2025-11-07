"""Persistent job storage backing the translation queue and CLI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, MutableMapping

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
JOBS_ENV = "SAGEMTL_JOBS_PATH"
DEFAULT_DIR = Path.home() / ".sagemtl"
DEFAULT_PATH = DEFAULT_DIR / "jobs.json"


def _now() -> str:
    return datetime.utcnow().strftime(ISO_FORMAT)


@dataclass(slots=True)
class JobRecord:
    id: str
    type: str
    status: str
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    meta: Dict[str, object] = field(default_factory=dict)
    payload: Dict[str, object] = field(default_factory=dict)
    result: Dict[str, object] | None = None
    error: str | None = None
    log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: MutableMapping[str, object]) -> "JobRecord":
        return cls(
            id=str(data.get("id")),
            type=str(data.get("type")),
            status=str(data.get("status")),
            created_at=str(data.get("created_at", _now())),
            updated_at=str(data.get("updated_at", _now())),
            meta=dict(data.get("meta", {})),
            payload=dict(data.get("payload", {})),
            result=dict(data["result"]) if data.get("result") else None,
            error=str(data.get("error")) if data.get("error") else None,
            log=list(data.get("log", [])),
        )


class JobStore:
    """Thread-safe JSON backed job repository."""

    def __init__(self, path: Path | None = None) -> None:
        env_override = os.environ.get(JOBS_ENV)
        self.path = Path(env_override).expanduser() if env_override else path or DEFAULT_PATH
        if self.path.is_dir():
            self.path = self.path / "jobs.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._jobs: Dict[str, JobRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        for raw in jobs:
            record = JobRecord.from_dict(raw)
            self._jobs[record.id] = record

    def _flush(self) -> None:
        payload = [job.to_dict() for job in self._jobs.values()]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def list(self) -> List[JobRecord]:
        with self._lock:
            return [JobRecord.from_dict(job.to_dict()) for job in self._jobs.values()]

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            return JobRecord.from_dict(record.to_dict()) if record else None

    def upsert(self, record: JobRecord) -> None:
        with self._lock:
            record.updated_at = _now()
            self._jobs[record.id] = record
            self._flush()

    def append_log(self, job_id: str, message: str) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.log.append(message)
            record.updated_at = _now()
            self._flush()

    def purge(self, *, statuses: Iterable[str] | None = None) -> List[str]:
        keep_statuses = set(statuses) if statuses else {"queued", "running"}
        removed: List[str] = []
        with self._lock:
            to_delete = [job_id for job_id, job in self._jobs.items() if job.status.lower() not in keep_statuses]
            for job_id in to_delete:
                removed.append(job_id)
                del self._jobs[job_id]
            if to_delete:
                self._flush()
        return removed


_store_singleton: JobStore | None = None


def get_job_store() -> JobStore:
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = JobStore()
    return _store_singleton
