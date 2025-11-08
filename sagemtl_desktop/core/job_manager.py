"""
Job manager with threading and Qt signals for UI updates.
"""

from PySide6.QtCore import QObject, Signal, QThread, QMutex, QMutexLocker
from typing import List, Optional, Callable, Dict
import uuid
from datetime import datetime
import traceback

from .models import Job, JobStatus, JobType


class JobWorker(QThread):
    """Worker thread that processes a single job"""

    # Signals
    progress_updated = Signal(str, float)  # job_id, progress (0-100)
    job_completed = Signal(str)            # job_id
    job_failed = Signal(str, str, str)     # job_id, error_msg, traceback
    log_message = Signal(str, str, str)    # job_id, level, message

    def __init__(self, job: Job, processor: Callable, parent=None):
        """
        Initialize worker.

        Args:
            job: Job to process
            processor: Function that processes the job
                      Signature: processor(job, progress_callback, log_callback) -> None
            parent: Parent QObject
        """
        super().__init__(parent)
        self.job = job
        self.processor = processor
        self._should_stop = False

    def run(self):
        """Execute job in background thread"""
        try:
            self.emit_log("info", f"Started processing: {self.job.name}")

            # Call the processor with callbacks
            self.processor(
                self.job,
                self.emit_progress,
                self.emit_log
            )

            if not self._should_stop:
                self.emit_log("info", f"Completed processing: {self.job.name}")
                self.job_completed.emit(self.job.job_id)

        except Exception as e:
            tb = traceback.format_exc()
            self.emit_log("error", f"Processing failed: {str(e)}")
            self.job_failed.emit(self.job.job_id, str(e), tb)

    def emit_progress(self, progress: float):
        """Emit progress update"""
        if not self._should_stop:
            self.progress_updated.emit(self.job.job_id, progress)

    def emit_log(self, level: str, message: str):
        """Emit log message"""
        self.log_message.emit(self.job.job_id, level, message)

    def stop(self):
        """Request worker to stop"""
        self._should_stop = True


class JobManager(QObject):
    """
    Manages all jobs and worker threads.

    This class is thread-safe and emits Qt signals for UI updates.
    """

    # Signals
    job_added = Signal(str)                 # job_id
    job_updated = Signal(str)               # job_id
    job_removed = Signal(str)               # job_id
    progress_changed = Signal(str, float)   # job_id, progress
    log_emitted = Signal(str, str, str, str)  # timestamp, job_id, level, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._jobs: Dict[str, Job] = {}
        self._workers: Dict[str, JobWorker] = {}
        self._mutex = QMutex()

    def create_job(
        self,
        job_type: JobType,
        name: str,
        **metadata
    ) -> str:
        """
        Create a new job and return its ID.

        Args:
            job_type: Type of job
            name: Job name (filename or novel title)
            **metadata: Additional metadata

        Returns:
            Job ID
        """
        job = Job(
            job_id=str(uuid.uuid4()),
            job_type=job_type,
            status=JobStatus.PENDING,
            name=name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata
        )

        with QMutexLocker(self._mutex):
            self._jobs[job.job_id] = job

        self.job_added.emit(job.job_id)
        self._emit_log(job.job_id, "info", f"Created job: {name}")

        return job.job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job or None if not found
        """
        with QMutexLocker(self._mutex):
            return self._jobs.get(job_id)

    def get_all_jobs(self) -> List[Job]:
        """
        Get all jobs.

        Returns:
            List of all jobs
        """
        with QMutexLocker(self._mutex):
            return list(self._jobs.values())

    def update_job(self, job: Job):
        """
        Update job in storage.

        Args:
            job: Job to update
        """
        job.updated_at = datetime.now()

        with QMutexLocker(self._mutex):
            self._jobs[job.job_id] = job

        self.job_updated.emit(job.job_id)

    def remove_job(self, job_id: str):
        """
        Remove job.

        Args:
            job_id: Job ID
        """
        # Stop worker if running
        if job_id in self._workers:
            worker = self._workers[job_id]
            worker.stop()
            worker.wait(2000)  # Wait up to 2 seconds
            if worker.isRunning():
                worker.terminate()
            worker.deleteLater()
            del self._workers[job_id]

        # Remove job
        with QMutexLocker(self._mutex):
            if job_id in self._jobs:
                del self._jobs[job_id]

        self.job_removed.emit(job_id)

    def start_job(self, job_id: str, processor: Callable):
        """
        Start processing a job in background thread.

        Args:
            job_id: Job ID
            processor: Processing function
                      Signature: processor(job, progress_callback, log_callback) -> None
        """
        job = self.get_job(job_id)
        if not job:
            return

        job.status = JobStatus.IN_PROGRESS
        job.progress = 0.0
        self.update_job(job)

        # Create and start worker
        worker = JobWorker(job, processor, self)
        worker.progress_updated.connect(self._on_progress)
        worker.job_completed.connect(self._on_completed)
        worker.job_failed.connect(self._on_failed)
        worker.log_message.connect(self._on_log)

        self._workers[job_id] = worker
        worker.start()

    def _on_progress(self, job_id: str, progress: float):
        """Handle progress update from worker"""
        job = self.get_job(job_id)
        if job:
            job.progress = progress
            self.update_job(job)
            self.progress_changed.emit(job_id, progress)

    def _on_completed(self, job_id: str):
        """Handle job completion from worker"""
        job = self.get_job(job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            self.update_job(job)

        # Cleanup worker
        self._cleanup_worker(job_id)

    def _on_failed(self, job_id: str, error_msg: str, error_traceback: str):
        """Handle job failure from worker"""
        job = self.get_job(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = error_msg
            job.error_traceback = error_traceback
            self.update_job(job)

        # Cleanup worker
        self._cleanup_worker(job_id)

    def _on_log(self, job_id: str, level: str, message: str):
        """Handle log message from worker"""
        self._emit_log(job_id, level, message)

    def _emit_log(self, job_id: str, level: str, message: str):
        """Emit log signal with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_emitted.emit(timestamp, job_id, level, message)

    def _cleanup_worker(self, job_id: str):
        """Cleanup worker thread"""
        if job_id in self._workers:
            worker = self._workers[job_id]
            worker.deleteLater()
            del self._workers[job_id]

    def stop_all_jobs(self):
        """Stop all running jobs"""
        for job_id in list(self._workers.keys()):
            self.remove_job(job_id)

    def get_stats(self) -> Dict[str, int]:
        """
        Get job statistics.

        Returns:
            Dictionary with counts by status
        """
        stats = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
            "total": 0
        }

        with QMutexLocker(self._mutex):
            stats["total"] = len(self._jobs)
            for job in self._jobs.values():
                if job.status == JobStatus.PENDING:
                    stats["pending"] += 1
                elif job.status == JobStatus.IN_PROGRESS:
                    stats["in_progress"] += 1
                elif job.status == JobStatus.COMPLETED:
                    stats["completed"] += 1
                elif job.status == JobStatus.FAILED:
                    stats["failed"] += 1

        return stats
