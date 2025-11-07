"""Tests for job log file creation and retrieval."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from sagemtl.jobs.store import JobRecord, JobStore


def test_log_file_creation_on_failure():
    """Test that log files are created when jobs fail."""
    with TemporaryDirectory() as tmpdir:
        store = JobStore(Path(tmpdir) / "jobs.json")

        # Create a failed job
        job = JobRecord(
            id="test-job-1",
            type="translate",
            status="failed",
            error="Test error message",
            log=["Starting job", "Processing...", "Error occurred"],
        )
        store.upsert(job)

        # Write log file
        log_path = store.write_log_file("test-job-1")

        assert log_path is not None
        assert log_path.exists()
        assert log_path.name == "log.txt"
        assert "jobs/test-job-1" in str(log_path)

        # Verify log content
        log_content = log_path.read_text(encoding="utf-8")
        assert "Starting job" in log_content
        assert "Processing..." in log_content
        assert "Error occurred" in log_content
        assert "Test error message" in log_content
        assert "Job ID: test-job-1" in log_content
        assert "Status: failed" in log_content


def test_log_path_in_job_record():
    """Test that log_path is stored in JobRecord after writing."""
    with TemporaryDirectory() as tmpdir:
        store = JobStore(Path(tmpdir) / "jobs.json")

        job = JobRecord(
            id="test-job-2",
            type="crawl",
            status="failed",
            error="Crawl failed",
            log=["Crawling started", "Error: Connection timeout"],
        )
        store.upsert(job)

        # Initially no log_path
        retrieved = store.get("test-job-2")
        assert retrieved.log_path is None

        # Write log file
        store.write_log_file("test-job-2")

        # Now log_path should be set
        retrieved = store.get("test-job-2")
        assert retrieved.log_path is not None
        assert "test-job-2/log.txt" in retrieved.log_path


def test_log_file_with_stack_trace():
    """Test that log files include stack traces."""
    with TemporaryDirectory() as tmpdir:
        store = JobStore(Path(tmpdir) / "jobs.json")

        stack_trace = """Traceback (most recent call last):
  File "test.py", line 10, in <module>
    raise ValueError("Test error")
ValueError: Test error"""

        job = JobRecord(
            id="test-job-3",
            type="translate",
            status="failed",
            error=f"ValueError: Test error\n\nStack trace:\n{stack_trace}",
            log=["Job started", "Error occurred", f"Stack trace:\n{stack_trace}"],
        )
        store.upsert(job)

        log_path = store.write_log_file("test-job-3")
        log_content = log_path.read_text(encoding="utf-8")

        assert "Traceback (most recent call last)" in log_content
        assert "ValueError: Test error" in log_content
        assert "=== ERROR ===" in log_content
        assert "=== Job Info ===" in log_content


def test_log_file_persistence_across_store_instances():
    """Test that log_path persists when store is reloaded."""
    with TemporaryDirectory() as tmpdir:
        jobs_file = Path(tmpdir) / "jobs.json"

        # Create store and write log
        store1 = JobStore(jobs_file)
        job = JobRecord(
            id="test-job-4",
            type="translate",
            status="failed",
            error="Test error",
            log=["Log entry 1", "Log entry 2"],
        )
        store1.upsert(job)
        store1.write_log_file("test-job-4")

        # Get log_path from first store
        job1 = store1.get("test-job-4")
        log_path_1 = job1.log_path

        # Create new store instance (simulating reload)
        store2 = JobStore(jobs_file)
        job2 = store2.get("test-job-4")

        # log_path should be preserved
        assert job2.log_path == log_path_1
        assert job2.log_path is not None


def test_write_log_file_nonexistent_job():
    """Test that write_log_file returns None for nonexistent jobs."""
    with TemporaryDirectory() as tmpdir:
        store = JobStore(Path(tmpdir) / "jobs.json")
        result = store.write_log_file("nonexistent-job")
        assert result is None


def test_log_file_utf8_encoding():
    """Test that log files handle UTF-8 characters correctly."""
    with TemporaryDirectory() as tmpdir:
        store = JobStore(Path(tmpdir) / "jobs.json")

        job = JobRecord(
            id="test-job-5",
            type="translate",
            status="failed",
            error="翻译失败 (Translation failed) - エラー",
            log=["Processing 中文", "Error: 日本語のエラー", "Failed: 한국어 오류"],
        )
        store.upsert(job)

        log_path = store.write_log_file("test-job-5")
        log_content = log_path.read_text(encoding="utf-8")

        assert "翻译失败" in log_content
        assert "エラー" in log_content
        assert "日本語のエラー" in log_content
        assert "한국어 오류" in log_content


def test_log_file_without_error():
    """Test log file creation for successful jobs (no error field)."""
    with TemporaryDirectory() as tmpdir:
        store = JobStore(Path(tmpdir) / "jobs.json")

        job = JobRecord(
            id="test-job-6",
            type="translate",
            status="done",
            log=["Job started", "Processing complete", "Success"],
        )
        store.upsert(job)

        log_path = store.write_log_file("test-job-6")
        log_content = log_path.read_text(encoding="utf-8")

        # Should not have ERROR section
        assert "=== ERROR ===" not in log_content
        # Should have job info
        assert "=== Job Info ===" in log_content
        assert "Status: done" in log_content
        # Should have log messages
        assert "Job started" in log_content
        assert "Success" in log_content
