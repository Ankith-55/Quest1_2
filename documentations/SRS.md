# Software Requirements Specification (SRS)
## Video Dialogue Locator System

**Document Version:** 1.0.0  
**Status:** Approved / Implemented  
**Date:** 2026-08-26  
**Authors:** Ankith Vijayyan  

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) document defines the complete functional and non-functional requirements for the **Video Dialogue Locator** application. It establishes the technical blueprint for the system, covering the React frontend, FastAPI asynchronous backend, and the ML-powered audio/video processing pipeline.

### 1.2 Scope
The Video Dialogue Locator is an automated AI/ML software system that accepts any video URL (or local video path) and a target dialogue phrase, identifies every timestamp and corresponding exact visual frame where that dialogue is spoken, extracts high-resolution PNG frame images, and presents structured search results via a modern web interface and REST API.

### 1.3 Problem Statement & Evolution: OCR vs. ASR Rationale
* **Original Problem Statement:**
  > *"Find the Exact Frame Where a Dialogue Appears in a media URL. You are given a video URL. At some point in the video, an on-screen dialogue appears. Your task is to build a program that can identify: 1. The exact video frame in which the dialogue first appears, 2. The text contained in that dialogue, 3. The actual dialogue: 'My mind rebels at stagnation'. Input: `https://ok.ru/video/248244667877`. Output: timestamp, frame number, extracted dialogue text, corresponding frame image. The solution should work without manual inspection and be robust to variations in quality, resolution, frame rate. AI/ML tools allowed. Must document prompts, design decisions, approach for locating the relevant frame, text extraction method, and ambiguity handling."*

* **Technical Analysis & Architectural Decision:**
  * **Video Analysis:** Deep inspection of the sample video (*The Adventures of Sherlock Holmes: A Scandal in Bohemia*, `https://ok.ru/video/248244667877`) confirmed that the dialogue *"My mind rebels at stagnation"* is spoken by the character Sherlock Holmes, without burned-in open captions or subtitles on screen.
  * **ASR vs. OCR Decision:** An Optical Character Recognition (OCR) approach would fail because no text is visually rendered on screen. Therefore, the system was designed with an **Automatic Speech Recognition (ASR)-first architecture** using OpenAI Whisper to transcribe audio with word-level timestamps, combined with sliding-window fuzzy matching and FFmpeg exact visual frame extraction.

### 1.4 Definitions, Acronyms & Abbreviations
* **ASR:** Automatic Speech Recognition (speech-to-text transcription).
* **CFR / VFR:** Constant Frame Rate / Variable Frame Rate.
* **FFmpeg / ffprobe:** Multimedia processing tools for stream inspection and frame grabbing.
* **FPS:** Frames Per Second.
* **NMS:** Non-Maximum Suppression (used for temporal cluster deduplication).
* **RapidFuzz:** High-performance fuzzy string matching library using Levenshtein distance.
* **SPA:** Single Page Application (React 18 + Vite).

---

## 2. Overall Description

### 2.1 Product Perspective
The Video Dialogue Locator operates as a decoupled, multi-tiered application:
1. **Client Tier:** React 18 SPA providing query input, model parameter controls, live polling progress, and multi-match visual frame inspection.
2. **API Tier:** FastAPI server managing non-blocking job queues, thread-safe state transitions, and static artifact distribution.
3. **ML & Video Processing Engine:** Python pipeline orchestrating media downloading (`yt-dlp`), audio normalization, Whisper transcription, fuzzy dialogue localization (`RapidFuzz`), and precise frame extraction (`FFmpeg`).
4. **Storage Tier:** Local filesystem structured by persistent media caches (`media_cache/`) and unique per-job execution folders (`results/{job_id}/`).

```
[ Web Browser / Client ]
        │ (HTTP REST / Polling)
        ▼
[ FastAPI Server & JobManager ] ──► [ Static File Mount (/output) ]
        │ (Background Worker)
        ▼
[ ML Processing Engine ]
  ├── 1. yt-dlp & Media Cache
  ├── 2. OpenAI Whisper ASR
  ├── 3. RapidFuzz Sliding Window + NMS
  └── 4. FFmpeg Precise Frame Extractor
        │
        ▼
[ Storage (results/{job_id}/) ] ──► [ frame.png, transcript.json, result.json ]
```

### 2.2 User Characteristics
* **End Users / Content Researchers:** Non-technical or semi-technical users searching for spoken quotes, scenes, or soundbites across video archives.
* **Developers / Integrators:** Technical consumers integrating the `/jobs` REST API into automated ingestion pipelines.

### 2.3 Operating Environment
* **Server OS:** Windows, Linux, or macOS.
* **Python Runtime:** Python 3.10+ with `virtualenv`.
* **System Utilities:** FFmpeg and ffprobe available on system `PATH`.
* **Frontend Runtime:** Node.js 18+ (for development) or modern evergreen web browsers (Chrome, Firefox, Edge, Safari).

### 2.4 Design & Implementation Constraints
* Large video downloads and ASR transcription are computationally intensive and cannot block HTTP request threads; asynchronous background job execution is mandatory.
* Video frame rates vary across sources (e.g., 23.976, 24.0, 25.0, 29.97, 30.0, 60.0 FPS) requiring dynamic metadata extraction via `ffprobe` rather than hardcoded assumptions.

---

## 3. Functional Requirements

### 3.1 Media Ingestion & Caching
* **FR-1.1 (Multi-Source Ingestion):** The system shall download video and audio from arbitrary media URLs (e.g., YouTube, ok.ru, direct HTTP video links) or process local filesystem paths using `yt-dlp`.
* **FR-1.2 (Audio Extraction & Normalization):** The system shall extract an optimized 16,000 Hz, 16-bit mono PCM WAV audio stream from the ingested video for Whisper model consumption.
* **FR-1.3 (Stream FPS Detection):** The system shall programmatically query the video stream's exact frame rate using `ffprobe` to ensure frame index accuracy.
* **FR-1.4 (Persistent Media Caching):** The system shall store downloaded videos and audio in a shared `media_cache/` directory. If a URL has already been downloaded, subsequent searches on that video shall reuse local files without re-downloading.

### 3.2 Speech-to-Text Transcription (ASR)
* **FR-2.1 (Whisper Model Selection):** The system shall support selectable Whisper model sizes: `tiny`, `base`, `small`, `medium`, and `large`.
* **FR-2.2 (Word-Level Timing):** The system shall extract segment-level and word-level start/end timestamps from the audio stream.
* **FR-2.3 (Transcript Persistence):** The system shall save the full transcription output as a structured `transcript.json` inside the job's artifact directory.

### 3.3 Fuzzy Dialogue Matching & Ambiguity Handling
* **FR-3.1 (Text Normalization):** The system shall normalize both transcript segments and user queries by lowercasing, stripping punctuation, and collapsing multiple whitespaces.
* **FR-3.2 (Sliding-Window Fuzzy Search):** The system shall evaluate dialogue matches across dynamic multi-word token windows using `RapidFuzz` similarity algorithms.
* **FR-3.3 (Configurable Similarity Threshold):** The system shall allow users to specify a match threshold between `0.0` and `1.0` (default: `0.90` / 90%).
* **FR-3.4 (Temporal Non-Maximum Suppression):** The system shall apply Non-Maximum Suppression (NMS) over matched temporal windows to prevent duplicate detections of the same phrase instance while accurately detecting all distinct multiple occurrences across the video.
* **FR-3.5 (Near-Miss Fallback):** If no match satisfies the threshold, the system shall return top candidate matches ranked by similarity score with explanatory metadata.

### 3.4 Frame Number Calculation & Extraction
* **FR-4.1 (Mathematical Frame Mapping):** The system shall calculate exact frame numbers using the formula:
  $$\text{Frame Number} = \text{round}(\text{timestamp\_seconds} \times \text{FPS})$$
* **FR-4.2 (High-Resolution Frame Extraction):** The system shall invoke FFmpeg using fast input seeking (`-ss`) to extract high-resolution PNG image frames for every identified occurrence.
* **FR-4.3 (Structured File Output):** The system shall save primary frame captures (`frame.png`), individual multi-match frames (`frames/frame_N_HH_MM_SS_sss.png`), human-readable reports (`result.txt`), and JSON outputs (`result.json`) in an isolated `results/{job_id}/` folder.

### 3.5 Asynchronous REST API & Job Management
* **FR-5.1 (Job Submission):** `POST /jobs` shall accept `url`, `target_text`, `model_size`, and `threshold`, returning HTTP `202 Accepted` with a unique `job_id` and initial status `queued`.
* **FR-5.2 (Background Execution):** The backend shall execute pipeline tasks asynchronously using FastAPI `BackgroundTasks` without blocking API throughput.
* **FR-5.3 (Thread-Safe Job Tracking):** The `JobManager` shall track job states (`queued` $\rightarrow$ `processing` $\rightarrow$ `completed` / `failed`) protected by a `threading.Lock`.
* **FR-5.4 (Status Polling):** `GET /jobs/{job_id}` shall return the current state, execution timing, error messages, and completed result payload including relative image URLs.
* **FR-5.5 (Job History):** `GET /jobs` shall return a list of all historical search jobs.
* **FR-5.6 (Static Asset Serving):** The API shall mount `/output` pointing to the results directory to serve frame images directly to web clients.

### 3.6 Web User Interface (Frontend)
* **FR-6.1 (Interactive Query Form):** The UI shall provide input fields for Video URL and Target Text, alongside preset sample buttons (e.g., Sherlock Holmes, Avengers trailer).
* **FR-6.2 (Model & Threshold Controls):** The UI shall provide a model selector dropdown (`tiny` to `large`) and a slider for the fuzzy threshold (`50%` to `100%`).
* **FR-6.3 (Live Polling & State Tracking):** The UI shall automatically poll `/jobs/{job_id}` every 2 seconds until completion or error, displaying animated status badges.
* **FR-6.4 (Multi-Match Visualizer):** The UI shall render primary match hero cards and a grid of all secondary dialogue occurrences, displaying exact timestamp (`HH:MM:SS.sss`), calculated frame number, similarity confidence %, and frame image previews.
* **FR-6.5 (Full-Resolution Frame Modal):** The UI shall allow users to click any frame preview to inspect the full-resolution PNG in a modal overlay with one-click timestamp copying.
* **FR-6.6 (Historical Search Drawer):** The UI shall allow users to review and reload previous search runs directly from the backend history.

---

## 4. Non-Functional Requirements

### 4.1 Performance & Latency
* **NFR-1.1 (Non-Blocking API):** `POST /jobs` response latency shall be $< 100\text{ ms}$.
* **NFR-1.2 (Cache Speedup):** Re-running searches on previously cached videos shall bypass network downloading, reducing end-to-end execution to transcription/matching duration only.
* **NFR-1.3 (Efficient Frame Extraction):** FFmpeg fast input seek (`-ss` before `-i`) shall extract single frames in $< 500\text{ ms}$.

### 4.2 Accuracy & Precision
* **NFR-2.1 (Temporal Accuracy):** Extracted frame timestamps shall align within $\pm 1$ video frame interval ($< 0.05\text{ s}$) of the spoken dialogue onset.
* **NFR-2.2 (Robust Fuzzy Matching):** The sliding-window algorithm shall handle minor speech-to-text phonetic discrepancies, word contractions, and background music noise.

### 4.3 Reliability & Error Handling
* **NFR-3.1 (Graceful Degradation):** Invalid video URLs, network failures, or unparseable audio streams shall be caught and stored in the job's `error` attribute with HTTP 200/400 status instead of crashing the server.
* **NFR-3.2 (Client Polling Resilience):** The frontend polling client shall include automatic retry handling and a 10-minute maximum timeout.

### 4.4 Usability & Aesthetics
* **NFR-4.1 (Design Standards):** The user interface shall feature a cohesive dark aesthetic (Gruvbox theme) with responsive glassmorphism containers, smooth animations, and clear typography.
* **NFR-4.2 (Zero Placeholder Policy):** All visual components shall render actual live-computed data and genuine extracted video frame artifacts.

### 4.5 Maintainability & Testability
* **NFR-5.1 (Automated Test Suite):** Backend unit and integration tests (`tests/test_job_manager.py`, `tests/test_routes.py`) shall run in $< 2\text{ s}$ using mocks without downloading live models.
* **NFR-5.2 (Modular Decoupling):** The ML engine (`backend/ml`) shall remain fully functional both as an independent CLI script (`locate_phrase.py`) and as a module imported by FastAPI services.

---

## 5. Assumptions & Dependencies

### 5.1 System Dependencies
1. **FFmpeg & ffprobe:** Required for audio extraction, metadata inspection, and frame capturing.
2. **OpenAI Whisper:** PyTorch-based neural ASR model running on CPU or CUDA-enabled GPU.
3. **yt-dlp:** Maintained video/audio stream extraction library.
4. **FastAPI & Uvicorn:** ASGI web server framework.
5. **React 18 & Vite:** Modern web frontend build toolchain.

### 5.2 Environmental Assumptions
* The host machine has sufficient disk storage for cached video files and extracted frame PNGs.
* Active internet access is available for initial video streaming and Whisper model weight downloads (subsequent runs operate offline via cached media).
