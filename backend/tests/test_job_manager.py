import threading
import pytest
from app.api.schemas import JobCreateRequest, JobStatus
from app.services.job_manager import JobManager


def test_create_and_get_job():
    manager = JobManager()
    req = JobCreateRequest(url="https://youtu.be/test12345", target_text="Hello world")
    job_id = manager.create_job(req)

    assert job_id is not None
    job = manager.get_job(job_id)
    assert job is not None
    assert job["job_id"] == job_id
    assert job["status"] == JobStatus.QUEUED
    assert job["request"]["url"] == "https://youtu.be/test12345"
    assert job["request"]["target_text"] == "Hello world"


def test_job_state_transitions():
    manager = JobManager()
    req = JobCreateRequest(url="https://youtu.be/test12345", target_text="Whatever it takes")
    job_id = manager.create_job(req)

    # Transition to PROCESSING
    manager.set_processing(job_id)
    job = manager.get_job(job_id)
    assert job["status"] == JobStatus.PROCESSING
    assert job["started_at"] is not None

    # Transition to COMPLETED
    mock_result = {
        "status": "found",
        "timestamp": "00:01:30.000",
        "text": "Whatever it takes",
        "confidence": 0.95,
        "image_path": "20260825_120000/frame.png",
        "matches": []
    }
    manager.set_completed(job_id, mock_result)
    job = manager.get_job(job_id)
    assert job["status"] == JobStatus.COMPLETED
    assert job["completed_at"] is not None
    assert job["result"]["text"] == "Whatever it takes"


def test_job_failed_transition():
    manager = JobManager()
    req = JobCreateRequest(url="https://youtu.be/error", target_text="Fail query")
    job_id = manager.create_job(req)

    manager.set_failed(job_id, "Download timed out")
    job = manager.get_job(job_id)
    assert job["status"] == JobStatus.FAILED
    assert job["error"] == "Download timed out"


def test_list_jobs_and_thread_safety():
    manager = JobManager()
    job_ids = []

    def worker(i):
        req = JobCreateRequest(url=f"https://youtu.be/vid_{i}", target_text=f"Phrase {i}")
        jid = manager.create_job(req)
        job_ids.append(jid)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    all_jobs = manager.list_jobs()
    assert len(all_jobs) == 10
    assert len(job_ids) == 10
