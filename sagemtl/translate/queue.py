"""In-process threaded translation queue."""

from __future__ import annotations

from dataclasses import dataclass, field
from queue import Queue, Empty
import threading
import uuid
from typing import Dict, Iterable, Optional

from sagemtl.jobs.store import JobRecord, JobStore, get_job_store
from .glossary import apply_glossary, load_glossary
from .providers import NotConfigured, get_provider


@dataclass(slots=True)
class TranslationRequest:
    text: str
    src_lang: str
    tgt_lang: str
    provider_name: str | None = None
    glossary_path: str | None = None
    meta: Dict[str, object] = field(default_factory=dict)


class TranslationQueue:
    """Simple threaded worker that processes translation jobs sequentially."""

    def __init__(self, store: JobStore | None = None) -> None:
        self.store = store or get_job_store()
        self._queue: Queue[str] = Queue()
        self._lock = threading.Lock()
        self._worker = threading.Thread(
            target=self._run, name="sagemtl-translate", daemon=True
        )
        self._worker.start()

    def enqueue(self, request: TranslationRequest) -> JobRecord:
        job_id = str(uuid.uuid4())
        record = JobRecord(
            id=job_id,
            type="translate",
            status="queued",
            meta=request.meta.copy(),
            payload={
                "text": request.text,
                "src_lang": request.src_lang,
                "tgt_lang": request.tgt_lang,
                "provider": request.provider_name or "echo",
                "glossary": request.glossary_path,
            },
        )
        self.store.upsert(record)
        self._queue.put(job_id)
        return record

    def _run(self) -> None:
        while True:
            try:
                job_id = self._queue.get(timeout=0.5)
            except Empty:
                continue
            record = self.store.get(job_id)
            if not record:
                continue
            record.status = "running"
            self.store.upsert(record)
            try:
                payload = record.payload
                provider = get_provider(str(payload.get("provider")))
                text = provider.translate(
                    str(payload.get("text", "")),
                    src=str(payload.get("src_lang", "")),
                    tgt=str(payload.get("tgt_lang", "")),
                )
                glossary_entries = load_glossary(payload.get("glossary"))
                if glossary_entries:
                    text = apply_glossary(text, glossary_entries)
                record.result = {"text": text}
                record.status = "done"
                record.error = None
                self.store.upsert(record)
            except NotConfigured as exc:
                record.status = "failed"
                record.error = str(exc)
                self.store.upsert(record)
            except Exception as exc:  # pragma: no cover - safety net
                record.status = "failed"
                record.error = str(exc)
                self.store.upsert(record)
            finally:
                self._queue.task_done()

    def list_jobs(self) -> Iterable[JobRecord]:
        return self.store.list()

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        return self.store.get(job_id)


_queue_singleton: TranslationQueue | None = None


def get_translation_queue() -> TranslationQueue:
    global _queue_singleton
    if _queue_singleton is None:
        _queue_singleton = TranslationQueue()
    return _queue_singleton
