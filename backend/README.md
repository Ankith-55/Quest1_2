# Video Dialogue Locator - FastAPI Backend

A FastAPI service that wraps the Whisper + RapidFuzz Video Dialogue Locator ML pipeline to find spoken phrases in videos, compute exact timestamps, calculate video frame numbers, and extract high-resolution PNG video frames.

---

## Features

- **Asynchronous Job Execution**: Submit a job (`POST /jobs`) and poll its progress (`GET /jobs/{job_id}`).
- **Static Artifact Serving**: Extracted frame images and JSON results are served directly at `/output/...`.
- **Shared Media Cache**: Automatically reuses previously downloaded video and audio files from `ml/results/media_cache/`.
- **Thread-safe In-Memory Job Management**: Track job state transitions (`queued` → `processing` → `completed` / `failed`).
- **Interactive OpenAPI Documentation**: Built-in Swagger UI at `/docs` and ReDoc at `/redoc`.

---

## Installation & Setup

### 1. Prerequisites
- **Python 3.10+** (in `backend/venv`)
- **FFmpeg** installed and accessible in `PATH` (`ffmpeg -version`)

### 2. Install Dependencies
```bash
cd backend
# Activate your virtual environment:
# Windows PowerShell: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Variables (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

---

## Running the API Server

From the `backend/` directory:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **API Root**: [http://localhost:8000/](http://localhost:8000/)
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Static Artifacts**: [http://localhost:8000/output/](http://localhost:8000/output/)

---

## API Endpoints

### 1. Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "project": "Video Dialogue Locator API",
  "version": "1.0.0"
}
```

---

### 2. Submit Search Job
```http
POST /jobs
Content-Type: application/json

{
  "url": "https://youtu.be/TcMBFSGVi1c?si=EB2-z4GcB69kRg9v",
  "target_text": "Whatever it takes",
  "model_size": "base",
  "threshold": 0.9
}
```

**Response (HTTP 202 Accepted):**
```json
{
  "job_id": "a1b2c3d4e5f6",
  "status": "queued"
}
```

---

### 3. Get Job Status & Results
```http
GET /jobs/{job_id}
```

**Response (Completed):**
```json
{
  "job_id": "a1b2c3d4e5f6",
  "status": "completed",
  "created_at": "2026-08-25T18:30:00Z",
  "started_at": "2026-08-25T18:30:01Z",
  "completed_at": "2026-08-25T18:30:25Z",
  "result": {
    "status": "found",
    "timestamp": "00:01:33.200",
    "timestamp_seconds": 93.2,
    "frame_number": 2236,
    "text": "Whatever it takes.",
    "confidence": 1.0,
    "image_path": "20260825_183000/frame.png",
    "image_url": "/output/20260825_183000/frame.png",
    "matches": [
      {
        "instance": 1,
        "timestamp": "00:01:33.200",
        "timestamp_seconds": 93.2,
        "frame_number": 2236,
        "text": "Whatever it takes.",
        "confidence": 1.0,
        "image_path": "20260825_183000/frames/frame_1_00_01_33_200.png",
        "image_url": "/output/20260825_183000/frames/frame_1_00_01_33_200.png"
      }
    ],
    "fps": 24.0
  },
  "error": null
}
```

---

### 4. List All Jobs
```http
GET /jobs
```

---

## Running Unit Tests

Run the test suite with pytest:

```bash
cd backend
pytest tests/
```
