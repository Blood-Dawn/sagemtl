"""Tests for job log API endpoints."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from sagemtl.jobs.store import JobRecord, JobStore, get_job_store
from sagemtl.serve.api_v2 import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def test_store(monkeypatch):
    """Create a temporary job store for testing."""
    with TemporaryDirectory() as tmpdir:
        store = JobStore(Path(tmpdir) / "jobs.json")

        # Monkeypatch get_job_store to return our test store
        monkeypatch.setattr("sagemtl.serve.routers.jobs.get_job_store", lambda: store)

        yield store


def test_get_job_log_with_file(client, test_store):
    """Test retrieving job log when log file exists."""
    # Create a job with log file
    job = JobRecord(
        id="test-job-log-1",
        type="translate",
        status="failed",
        error="Test error",
        log=["Log entry 1", "Log entry 2", "Error occurred"],
    )
    test_store.upsert(job)
    test_store.write_log_file("test-job-log-1")

    # Get the log via API
    response = client.get("/api/jobs/test-job-log-1/log")

    assert response.status_code == 200
    data = response.json()

    assert "log" in data
    assert "source" in data
    assert data["source"] == "file"
    assert "path" in data

    log_content = data["log"]
    assert "Log entry 1" in log_content
    assert "Log entry 2" in log_content
    assert "Error occurred" in log_content
    assert "Test error" in log_content


def test_get_job_log_memory_fallback(client, test_store):
    """Test retrieving job log falls back to in-memory logs."""
    # Create a job without log file
    job = JobRecord(
        id="test-job-log-2",
        type="translate",
        status="running",
        log=["Starting job", "Processing chunk 1", "Processing chunk 2"],
    )
    test_store.upsert(job)

    # Don't write log file - should fall back to memory

    response = client.get("/api/jobs/test-job-log-2/log")

    assert response.status_code == 200
    data = response.json()

    assert data["source"] == "memory"
    assert "path" not in data

    log_content = data["log"]
    assert "Starting job" in log_content
    assert "Processing chunk 1" in log_content
    assert "Processing chunk 2" in log_content


def test_get_job_log_not_found(client, test_store):
    """Test retrieving log for nonexistent job."""
    response = client.get("/api/jobs/nonexistent-job/log")
    assert response.status_code == 404


def test_get_job_includes_log_path(client, test_store):
    """Test that GET /api/jobs/{id} includes log_path field."""
    # Create job with log file
    job = JobRecord(
        id="test-job-log-3",
        type="crawl",
        status="failed",
        error="Crawl error",
        log=["Crawl started", "Error: timeout"],
    )
    test_store.upsert(job)
    test_store.write_log_file("test-job-log-3")

    response = client.get("/api/jobs/test-job-log-3")

    assert response.status_code == 200
    data = response.json()

    assert "log_path" in data
    assert data["log_path"] is not None
    assert "test-job-log-3/log.txt" in data["log_path"]


def test_list_jobs_includes_log_path(client, test_store):
    """Test that GET /api/jobs includes log_path for all jobs."""
    # Create multiple jobs, some with log files
    job1 = JobRecord(id="job1", type="translate", status="failed", error="Error 1", log=["Log 1"])
    job2 = JobRecord(id="job2", type="crawl", status="done", log=["Log 2"])
    job3 = JobRecord(id="job3", type="translate", status="failed", error="Error 3", log=["Log 3"])

    test_store.upsert(job1)
    test_store.upsert(job2)
    test_store.upsert(job3)

    # Write log files for failed jobs
    test_store.write_log_file("job1")
    test_store.write_log_file("job3")

    response = client.get("/api/jobs")

    assert response.status_code == 200
    jobs = response.json()

    # Find our test jobs
    job1_data = next((j for j in jobs if j["id"] == "job1"), None)
    job2_data = next((j for j in jobs if j["id"] == "job2"), None)
    job3_data = next((j for j in jobs if j["id"] == "job3"), None)

    assert job1_data is not None
    assert job2_data is not None
    assert job3_data is not None

    # Jobs with log files should have log_path
    assert job1_data["log_path"] is not None
    assert job3_data["log_path"] is not None

    # Job without log file should have None
    assert job2_data["log_path"] is None


def test_get_job_log_empty_logs(client, test_store):
    """Test retrieving log for job with no log entries."""
    job = JobRecord(
        id="test-job-log-4",
        type="translate",
        status="queued",
        log=[],  # Empty log
    )
    test_store.upsert(job)

    response = client.get("/api/jobs/test-job-log-4/log")

    assert response.status_code == 200
    data = response.json()

    assert data["source"] == "memory"
    assert data["log"] == ""  # Empty string from join


def test_get_job_log_multiline_error(client, test_store):
    """Test that multiline errors are preserved in log files."""
    multiline_error = """ValueError: Invalid input

Caused by:
  TypeError: Expected string, got int

Stack trace:
  File "foo.py", line 10
    raise ValueError("Invalid input")"""

    job = JobRecord(
        id="test-job-log-5",
        type="translate",
        status="failed",
        error=multiline_error,
        log=["Job started", "Error occurred"],
    )
    test_store.upsert(job)
    test_store.write_log_file("test-job-log-5")

    response = client.get("/api/jobs/test-job-log-5/log")

    assert response.status_code == 200
    data = response.json()

    log_content = data["log"]
    assert "ValueError: Invalid input" in log_content
    assert "Caused by:" in log_content
    assert "TypeError: Expected string, got int" in log_content
    assert "Stack trace:" in log_content
