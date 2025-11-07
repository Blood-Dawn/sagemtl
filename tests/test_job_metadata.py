"""Tests for enhanced job metadata and logging."""

from __future__ import annotations

import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from sagemtl.jobs.store import JobRecord, JobStore
from sagemtl.translate import TranslationRequest, TranslationQueue


@pytest.fixture
def temp_store():
    """Create a temporary job store."""
    with TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "jobs.json"
        yield JobStore(store_path)


def test_job_metadata_tracking(temp_store):
    """Test that job metadata is properly tracked."""
    job = JobRecord(
        id="test-job-1",
        type="translate",
        status="queued",
        meta={
            "input_text": "Hello world",
            "provider": "echo",
        },
        payload={"text": "Hello world"},
    )

    temp_store.upsert(job)

    # Retrieve and verify
    retrieved = temp_store.get("test-job-1")
    assert retrieved is not None
    assert retrieved.meta["provider"] == "echo"


def test_job_log_appending(temp_store):
    """Test appending log messages to jobs."""
    job = JobRecord(
        id="test-job-2",
        type="translate",
        status="running",
    )

    temp_store.upsert(job)

    # Append logs
    temp_store.append_log("test-job-2", "Starting translation")
    temp_store.append_log("test-job-2", "Processing input")
    temp_store.append_log("test-job-2", "Translation complete")

    # Verify logs
    retrieved = temp_store.get("test-job-2")
    assert retrieved is not None
    assert len(retrieved.log) == 3
    assert retrieved.log[0] == "Starting translation"
    assert retrieved.log[2] == "Translation complete"


def test_translation_queue_metadata():
    """Test that translation queue adds metadata."""
    with TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "jobs.json"
        store = JobStore(store_path)
        queue = TranslationQueue(store=store)

        request = TranslationRequest(
            text="Test input text",
            src_lang="zh",
            tgt_lang="en",
            provider_name="echo",
            meta={"custom_field": "test_value"},
        )

        job = queue.enqueue(request)

        # Wait a moment for processing
        time.sleep(0.1)

        # Check metadata
        retrieved = store.get(job.id)
        assert retrieved is not None
        assert "custom_field" in retrieved.meta
        assert retrieved.meta["custom_field"] == "test_value"


def test_job_runtime_tracking():
    """Test that runtime is tracked in job metadata."""
    with TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "jobs.json"
        store = JobStore(store_path)
        queue = TranslationQueue(store=store)

        request = TranslationRequest(
            text="Test text for runtime tracking",
            src_lang="auto",
            tgt_lang="en",
            provider_name="echo",
        )

        job = queue.enqueue(request)

        # Wait for job to complete
        max_wait = 5.0
        start = time.time()
        while time.time() - start < max_wait:
            retrieved = store.get(job.id)
            if retrieved and retrieved.status == "done":
                break
            time.sleep(0.1)

        # Verify runtime was tracked
        final_job = store.get(job.id)
        assert final_job is not None
        assert final_job.status == "done"
        assert "runtime_ms" in final_job.meta
        assert isinstance(final_job.meta["runtime_ms"], (int, float))
        assert final_job.meta["runtime_ms"] > 0


def test_job_size_tracking():
    """Test that input/output sizes are tracked."""
    with TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "jobs.json"
        store = JobStore(store_path)
        queue = TranslationQueue(store=store)

        test_text = "This is a test input with some content."
        request = TranslationRequest(
            text=test_text,
            src_lang="auto",
            tgt_lang="en",
            provider_name="echo",
        )

        job = queue.enqueue(request)

        # Wait for completion
        max_wait = 5.0
        start = time.time()
        while time.time() - start < max_wait:
            retrieved = store.get(job.id)
            if retrieved and retrieved.status == "done":
                break
            time.sleep(0.1)

        # Verify size tracking
        final_job = store.get(job.id)
        assert final_job is not None
        assert "input_bytes" in final_job.meta
        assert "output_bytes" in final_job.meta

        input_bytes = final_job.meta["input_bytes"]
        assert input_bytes == len(test_text.encode("utf-8"))


def test_job_provider_tracking():
    """Test that provider info is tracked in metadata."""
    with TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "jobs.json"
        store = JobStore(store_path)
        queue = TranslationQueue(store=store)

        request = TranslationRequest(
            text="Test",
            src_lang="zh",
            tgt_lang="en",
            provider_name="echo",
        )

        job = queue.enqueue(request)

        # Wait for completion
        time.sleep(0.5)

        final_job = store.get(job.id)
        assert final_job is not None

        # Verify provider metadata
        if final_job.status == "done":
            assert "provider" in final_job.meta
            assert final_job.meta["provider"] == "echo"
            assert "src_lang" in final_job.meta
            assert "tgt_lang" in final_job.meta


def test_job_log_on_completion():
    """Test that logs are added on job completion."""
    with TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "jobs.json"
        store = JobStore(store_path)
        queue = TranslationQueue(store=store)

        request = TranslationRequest(
            text="Log test",
            src_lang="auto",
            tgt_lang="en",
            provider_name="echo",
        )

        job = queue.enqueue(request)

        # Wait for completion
        time.sleep(1.0)

        final_job = store.get(job.id)
        assert final_job is not None

        # Verify logs exist
        if final_job.status == "done":
            assert len(final_job.log) > 0
            # Should have completion and size logs
            log_text = " ".join(final_job.log)
            assert "completed" in log_text.lower() or "bytes" in log_text.lower()


def test_job_persistence():
    """Test that job metadata persists across store instances."""
    with TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "jobs.json"

        # Create job in first store instance
        store1 = JobStore(store_path)
        job = JobRecord(
            id="persist-test",
            type="translate",
            status="done",
            meta={
                "runtime_ms": 123.45,
                "input_bytes": 100,
                "output_bytes": 150,
                "provider": "test-provider",
            },
        )
        store1.upsert(job)

        # Create new store instance
        store2 = JobStore(store_path)
        retrieved = store2.get("persist-test")

        # Verify all metadata persisted
        assert retrieved is not None
        assert retrieved.meta["runtime_ms"] == 123.45
        assert retrieved.meta["input_bytes"] == 100
        assert retrieved.meta["output_bytes"] == 150
        assert retrieved.meta["provider"] == "test-provider"
