"""
Import manager with resilience features (auto-retry, deduplication).
"""

import hashlib
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta


class ImportManager:
    """Manages file imports with resilience features"""

    def __init__(self):
        self._content_hashes: Dict[str, str] = {}  # hash -> job_id
        self._stuck_jobs: Dict[str, datetime] = {}  # job_id -> stuck_time
        self._stuck_timeout = timedelta(minutes=5)  # Consider stuck after 5 minutes

    def compute_content_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of content for deduplication.

        Args:
            content: Text content

        Returns:
            Hex digest of SHA-256 hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def is_duplicate(self, content: str) -> Optional[str]:
        """
        Check if content has already been imported.

        Args:
            content: Text content

        Returns:
            Job ID of duplicate if found, None otherwise
        """
        content_hash = self.compute_content_hash(content)
        return self._content_hashes.get(content_hash)

    def register_import(self, job_id: str, content: str):
        """
        Register an import to track for deduplication.

        Args:
            job_id: Job ID
            content: Imported content
        """
        content_hash = self.compute_content_hash(content)
        self._content_hashes[content_hash] = job_id

    def mark_job_stuck(self, job_id: str):
        """
        Mark a job as stuck.

        Args:
            job_id: Job ID to mark as stuck
        """
        self._stuck_jobs[job_id] = datetime.now()

    def is_job_stuck(self, job_id: str) -> bool:
        """
        Check if a job is stuck (hasn't progressed in timeout period).

        Args:
            job_id: Job ID to check

        Returns:
            True if job is stuck
        """
        if job_id not in self._stuck_jobs:
            return False

        stuck_time = self._stuck_jobs[job_id]
        return datetime.now() - stuck_time > self._stuck_timeout

    def clear_stuck_job(self, job_id: str):
        """
        Clear stuck status for a job.

        Args:
            job_id: Job ID to clear
        """
        if job_id in self._stuck_jobs:
            del self._stuck_jobs[job_id]

    def cleanup_hash(self, job_id: str):
        """
        Remove hash entry for a job (e.g., when job is deleted).

        Args:
            job_id: Job ID to clean up
        """
        # Find and remove hash entry
        to_remove = None
        for content_hash, stored_job_id in self._content_hashes.items():
            if stored_job_id == job_id:
                to_remove = content_hash
                break

        if to_remove:
            del self._content_hashes[to_remove]
