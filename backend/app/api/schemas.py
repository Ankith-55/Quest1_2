from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreateRequest(BaseModel):
    url: str = Field(..., min_length=1, description="URL of the video to search in")
    target_text: str = Field(..., min_length=1, description="Target spoken phrase to locate")
    model_size: Optional[str] = Field(default="base", description="Whisper model size: tiny, base, small, medium, large")
    threshold: Optional[float] = Field(default=0.9, ge=0.0, le=1.0, description="Fuzzy match threshold between 0.0 and 1.0")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Video URL must not be empty.")
        return v.strip()

    @field_validator("target_text")
    @classmethod
    def validate_target_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Target phrase must not be empty.")
        return v.strip()


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED


class JobMatch(BaseModel):
    instance: Optional[int] = 1
    timestamp: str
    timestamp_seconds: float
    frame_number: int
    text: str
    confidence: float
    image_path: Optional[str] = None
    image_url: Optional[str] = None


class JobCandidate(BaseModel):
    candidate: int
    timestamp: str
    timestamp_seconds: float
    frame_number: int
    text: str
    score: float


class JobResult(BaseModel):
    status: str
    timestamp: Optional[str] = None
    timestamp_seconds: Optional[float] = None
    frame_number: Optional[int] = None
    text: Optional[str] = None
    confidence: Optional[float] = None
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    matches: List[JobMatch] = []
    candidates: Optional[List[JobCandidate]] = []
    fps: Optional[float] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[JobResult] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    project: str
    version: str
