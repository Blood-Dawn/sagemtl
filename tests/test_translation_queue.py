from __future__ import annotations

import time

from sagemtl.jobs import store as store_module
from sagemtl.translate import TranslationRequest, get_translation_queue
from sagemtl.translate import queue as queue_module


def test_translation_queue_glossary(tmp_path, monkeypatch):
    jobs_path = tmp_path / "jobs.json"
    monkeypatch.setenv("SAGEMTL_JOBS_PATH", str(jobs_path))
    store_module._store_singleton = None  # type: ignore[attr-defined]
    queue_module._queue_singleton = None  # type: ignore[attr-defined]
    glossary = tmp_path / "gloss.csv"
    glossary.write_text("hello,bonjour\n", encoding="utf-8")
    queue = get_translation_queue()
    job = queue.enqueue(
        TranslationRequest(
            text="hello world",
            src_lang="en",
            tgt_lang="fr",
            glossary_path=str(glossary),
        )
    )
    for _ in range(20):
        current = queue.get_job(job.id)
        if current and current.status == "done":
            break
        time.sleep(0.1)
    current = queue.get_job(job.id)
    assert current is not None
    assert current.status == "done"
    assert current.result["text"] == "bonjour world"
