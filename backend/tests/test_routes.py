from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.job_manager import job_manager

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_job_store():
    """Clear in-memory jobs before each test."""
    job_manager.clear()
    yield
    job_manager.clear()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "project" in data
    assert "version" in data


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs_url" in data


def test_submit_job_valid():
    payload = {
        "url": "https://youtu.be/TcMBFSGVi1c",
        "target_text": "Whatever it takes",
        "model_size": "tiny",
        "threshold": 0.85
    }

    with patch("app.services.pipeline.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = {
            "status": "found",
            "timestamp": "00:01:33.200",
            "timestamp_seconds": 93.2,
            "frame_number": 2236,
            "text": "Whatever it takes",
            "confidence": 0.96,
            "image_path": "test_run/frame.png",
            "matches": [
                {
                    "instance": 1,
                    "timestamp": "00:01:33.200",
                    "timestamp_seconds": 93.2,
                    "frame_number": 2236,
                    "text": "Whatever it takes",
                    "confidence": 0.96,
                    "image_path": "test_run/frames/frame_1.png"
                }
            ],
            "fps": 24.0
        }

        response = client.post("/jobs", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"

        job_id = data["job_id"]

        # Poll the job status (in TestClient background tasks execute synchronously)
        status_resp = client.get(f"/jobs/{job_id}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["status"] == "completed"
        assert status_data["result"]["status"] == "found"
        assert status_data["result"]["text"] == "Whatever it takes"
        assert status_data["result"]["image_url"] == "/output/test_run/frame.png"
        assert len(status_data["result"]["matches"]) == 1


def test_submit_job_empty_url_validation():
    payload = {
        "url": "   ",
        "target_text": "Hello world"
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_submit_job_empty_target_validation():
    payload = {
        "url": "https://youtu.be/TcMBFSGVi1c",
        "target_text": "   "
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_get_nonexistent_job():
    response = client.get("/jobs/does_not_exist_123")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_job_failure_handling():
    payload = {
        "url": "https://youtu.be/invalid_video",
        "target_text": "Test phrase"
    }

    with patch("app.services.pipeline.run_pipeline") as mock_pipeline:
        mock_pipeline.side_effect = RuntimeError("Failed to download video stream")

        response = client.post("/jobs", json=payload)
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        status_resp = client.get(f"/jobs/{job_id}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["status"] == "failed"
        assert "Failed to download video stream" in status_data["error"]


def test_list_all_jobs():
    with patch("app.services.pipeline.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = {"status": "not_found", "matches": []}

        client.post("/jobs", json={"url": "https://youtu.be/v1", "target_text": "phrase 1"})
        client.post("/jobs", json={"url": "https://youtu.be/v2", "target_text": "phrase 2"})

        response = client.get("/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 2
