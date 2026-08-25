import logging
from typing import List
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.schemas import (
    HealthResponse,
    JobCreateRequest,
    JobCreateResponse,
    JobStatus,
    JobStatusResponse,
)
from app.core.config import settings
from app.services.job_manager import job_manager
from app.services.pipeline import process_job

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint"
)
async def health_check():
    """
    Returns the health status and metadata of the API service.
    """
    return HealthResponse(
        status="healthy",
        project=settings.PROJECT_NAME,
        version=settings.VERSION
    )


@router.post(
    "/jobs",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Jobs"],
    summary="Submit a video dialogue search job"
)
async def submit_job(request: JobCreateRequest, background_tasks: BackgroundTasks):
    """
    Creates a new phrase location job and starts execution asynchronously in the background.

    - **url**: URL of the video (YouTube, ok.ru, direct video links).
    - **target_text**: Spoken dialogue phrase to locate.
    - **model_size**: Whisper model size ('tiny', 'base', 'small', 'medium', 'large', default: 'base').
    - **threshold**: Similarity score threshold (0.0 to 1.0, default: 0.9).
    """
    job_id = job_manager.create_job(request)
    logger.info("Job submitted: %s for query \"%s\"", job_id, request.target_text)

    # Dispatch pipeline execution to background worker
    background_tasks.add_task(process_job, job_id, request)

    return JobCreateResponse(
        job_id=job_id,
        status=JobStatus.QUEUED
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    tags=["Jobs"],
    summary="Get job status and results"
)
async def get_job_status(job_id: str):
    """
    Retrieves the current status, timestamps, and extracted frame results for a submitted job.

    Possible status values:
    - **queued**: Job is waiting to start.
    - **processing**: Video downloading, transcribing, or matching is in progress.
    - **completed**: Dialogue located and frame image(s) extracted.
    - **failed**: An error occurred during processing.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found."
        )

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        result=job.get("result"),
        error=job.get("error")
    )


@router.get(
    "/jobs",
    response_model=List[JobStatusResponse],
    tags=["Jobs"],
    summary="List all submitted jobs"
)
async def list_all_jobs():
    """
    Returns a list of all tracked jobs, sorted newest to oldest.
    """
    jobs = job_manager.list_jobs()
    return [
        JobStatusResponse(
            job_id=j["job_id"],
            status=j["status"],
            created_at=j["created_at"],
            started_at=j.get("started_at"),
            completed_at=j.get("completed_at"),
            result=j.get("result"),
            error=j.get("error")
        )
        for j in jobs
    ]
