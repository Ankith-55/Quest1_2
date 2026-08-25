import copy
from datetime import datetime
import threading
from typing import Any, Dict, List, Optional
import uuid

from app.api.schemas import JobCreateRequest, JobStatus


class JobManager:
    """
    Thread-safe in-memory job store for tracking video dialogue locator jobs.
    """

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_job(self, request: JobCreateRequest, custom_id: Optional[str] = None) -> str:
        """
        Creates a new job in the queued state.
        """
        job_id = custom_id or uuid.uuid4().hex[:12]
        now = datetime.utcnow().isoformat() + "Z"

        job_data = {
            "job_id": job_id,
            "status": JobStatus.QUEUED,
            "request": request.model_dump(),
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
        }

        with self._lock:
            self._jobs[job_id] = job_data

        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a job by its ID.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                return copy.deepcopy(job)
            return None

    def set_processing(self, job_id: str) -> None:
        """
        Marks a job as actively processing.
        """
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = JobStatus.PROCESSING
                self._jobs[job_id]["started_at"] = now

    def set_completed(self, job_id: str, result: Dict[str, Any]) -> None:
        """
        Marks a job as completed and stores the execution result.
        """
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = JobStatus.COMPLETED
                self._jobs[job_id]["completed_at"] = now
                self._jobs[job_id]["result"] = result

    def set_failed(self, job_id: str, error_message: str) -> None:
        """
        Marks a job as failed and stores the error message.
        """
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = JobStatus.FAILED
                self._jobs[job_id]["completed_at"] = now
                self._jobs[job_id]["error"] = error_message

    def list_jobs(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all jobs sorted by creation timestamp descending.
        """
        with self._lock:
            jobs = [copy.deepcopy(job) for job in self._jobs.values()]
        jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        return jobs

    def clear(self) -> None:
        """
        Clears all jobs (useful for testing).
        """
        with self._lock:
            self._jobs.clear()


job_manager = JobManager()
