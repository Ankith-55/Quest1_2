# Technical Design Decisions & Architecture Trade-Offs

**Project:** Video Dialogue Locator  
**Author:** Ankith Vijayyan  
**Date:** 2026-08-26  
**Document Version:** 1.0.0  

---

## 1. Dialogue Detection: ASR (Speech Recognition) vs. OCR (Optical Character Recognition)

* **Context:** The original challenge was to find the exact frame where dialogue appears in a video URL (e.g., Sherlock Holmes *A Scandal in Bohemia*).
* **Alternatives Considered:**
  * *Video OCR (Tesseract / EasyOCR):* Sample video frames at 1–5 FPS and run OCR bounding-box detection across frames.
  * *Subtitle Track Extraction:* Extract existing subtitle tracks (SRT/VTT) using `yt-dlp`.
  * *Automatic Speech Recognition (ASR):* Transcribe spoken audio directly using an acoustic neural model (Whisper).
* **Chosen Approach:** Automatic Speech Recognition (ASR) via OpenAI Whisper.
* **Rationale:**
  * Video inspection confirmed that dialogue is spoken naturally by characters with **no burned-in text or subtitles** on screen. OCR across video frames would yield 0% detection and waste substantial compute.
  * Subtitle tracks are frequently absent or poorly synchronized across third-party video hosts.
  * ASR processes the acoustic waveform directly, yielding high-precision, word-level timestamps regardless of visual layout.
* **Code Reference:** `backend/ml/transcriber.py`, `backend/ml/locate_phrase.py`

---

## 2. Whisper Model Selection & Dynamic Model Escalation

* **Context:** ASR accuracy increases with model capacity, but larger models require higher memory and computation time.
* **Alternatives Considered:**
  * *Fixed `large-v3`:* High accuracy, but too slow for interactive web use on CPUs (~2–5 minutes per video).
  * *Fixed `tiny`:* Fast (~2 seconds), but prone to word errors on accents or background music.
  * *Cloud ASR APIs (OpenAI Whisper API / Google Speech-to-Text):* Adds external billing, rate limits, and API key dependencies.
  * *Configurable Local Models (`tiny`, `base`, `small`, `medium`, `large`):* Default to `base` with user-selectable escalation.
* **Chosen Approach:** Configurable local Whisper model with `base` as default.
* **Rationale:**
  * `base` (74M parameters) processes a 5-minute audio clip in ~8–15 seconds on standard hardware with >95% accuracy on standard dialogue.
  * The frontend provides a dropdown (`tiny`, `base`, `small`, `medium`, `large`), allowing users to escalate to `small` or `medium` for challenging accents or audio without modifying backend code.
* **Code Reference:** `backend/ml/transcriber.py`, `backend/app/core/config.py`, `frontend/src/components/TargetTextInput.jsx`

---

## 3. Media Ingestion Strategy: Audio-Only Extraction + Streamlined Video

* **Context:** Video streams from platforms like YouTube or ok.ru can be gigabytes in size.
* **Alternatives Considered:**
  * *Full High-Resolution Video Download:* Slow download times and excessive bandwidth consumption.
  * *Audio-Only Download:* Fast download, but makes subsequent visual frame extraction impossible.
  * *Streamlined Video Download + 16kHz Mono WAV Extraction:* Download video via `yt-dlp` format selection and extract an uncompressed 16kHz mono WAV for Whisper.
* **Chosen Approach:** Download video and extract dedicated 16kHz mono PCM audio.
* **Rationale:**
  * Whisper's mel-spectrogram preprocessor requires 16,000 Hz single-channel audio. Pre-converting to WAV via FFmpeg (`-ar 16000 -ac 1`) avoids in-memory decoding overhead during transcription.
  * Retaining the video file enables fast seeking for frame extraction once timestamps are identified.
* **Code Reference:** `backend/ml/downloader.py`

---

## 4. Frame Extraction Method: FFmpeg Fast Seeking vs. OpenCV Sequential Read

* **Context:** Once a dialogue timestamp (e.g., `00:01:33.200`) is located, the system must grab the exact video frame as a PNG.
* **Alternatives Considered:**
  * *OpenCV Sequential Loop (`cv2.VideoCapture`):* Open video and loop through frames until reaching the target frame index.
  * *MoviePy Frame Extraction (`VideoFileClip.get_frame`):* High overhead, pulls clip into memory.
  * *FFmpeg Fast Input Seeking (`-ss` placed before `-i`):* Jump directly to the keyframe and decode forward to the exact timestamp.
* **Chosen Approach:** FFmpeg fast input seeking with fallback.
* **Rationale:**
  * OpenCV sequential reading takes 30–90 seconds to reach a timestamp 20 minutes into a 1080p video.
  * FFmpeg fast input seek (`ffmpeg -ss <timestamp> -i <video> -frames:v 1 -q:v 2 <out.png>`) extracts frames in under 300 ms.
  * The exact frame number is calculated dynamically using `ffprobe` stream metadata: `Frame Number = round(timestamp_seconds * FPS)`.
* **Code Reference:** `backend/ml/downloader.py`

---

## 5. Fuzzy Matching Algorithm & Temporal Non-Maximum Suppression (NMS)

* **Context:** Speech-to-text transcripts frequently contain minor punctuation differences, contractions ("cannot" vs "can't"), or phonetic transcription variations. Identical phrases can also appear multiple times in a video.
* **Alternatives Considered:**
  * *Exact Substring Matching:* Fails on minor punctuation or typo differences.
  * *Global Levenshtein Distance across Full Transcript:* Fails because transcripts contain thousands of words.
  * *Sliding-Window Token Matching with RapidFuzz + Temporal NMS:* Compare normalized sliding word windows against target phrase and cluster overlapping hits.
* **Chosen Approach:** Sliding-window fuzzy matching with temporal NMS clustering.
* **Rationale:**
  * **Normalization:** Strips punctuation, lowercases text, and collapses whitespace.
  * **Dynamic Token Window:** Slides windows of length [L - 2, L + 2] words (where L is target word count) across word-level timestamps.
  * **RapidFuzz Scoring:** Combines `fuzz.ratio` and `fuzz.partial_ratio` for robust 0.0 to 1.0 scoring.
  * **Temporal NMS:** When adjacent windows match the same utterance (e.g., at 93.1s, 93.2s, 93.3s), NMS selects the highest-scoring candidate and suppresses overlapping windows (>35% overlap). This prevents duplicate frames for a single utterance while preserving distinct multiple occurrences throughout the video.
* **Code Reference:** `backend/ml/matcher.py`

---

## 6. Job Execution Architecture: FastAPI BackgroundTasks vs. Celery / Redis

* **Context:** Audio transcription takes 10–60 seconds, which exceeds standard HTTP request timeouts (15–30s).
* **Alternatives Considered:**
  * *Synchronous Request Handling:* Blocks HTTP worker threads, causing HTTP 504 gateway timeouts.
  * *Celery Task Queue with Redis / RabbitMQ:* Industry standard for multi-worker setups, but requires external message broker daemons.
  * *FastAPI `BackgroundTasks` with In-Memory `JobManager`:* Built-in asynchronous execution using Python's standard thread pool.
* **Chosen Approach:** FastAPI `BackgroundTasks` + Thread-Safe In-Memory `JobManager`.
* **Rationale:**
  * Eliminates external infrastructure dependencies (no Redis server or Docker containers required to run locally).
  * `POST /jobs` returns an immediate `202 Accepted` response with a unique `job_id` in under 50 ms.
  * Thread safety is ensured via `threading.Lock` protecting the in-memory job dictionary during concurrent operations.
* **Code Reference:** `backend/app/services/job_manager.py`, `backend/app/api/routes.py`

---

## 7. Frontend-Backend Communication: Client Polling vs. WebSockets / SSE

* **Context:** The frontend needs to track background processing stages and retrieve final results once frame extraction completes.
* **Alternatives Considered:**
  * *WebSockets (`ws://`):* Full duplex persistent connection; requires ping/pong keepalive and stateful reconnect logic.
  * *Server-Sent Events (SSE):* Unidirectional stream; complicates proxy configurations and error recovery on network drops.
  * *Short HTTP Polling (`GET /jobs/{id}` every 2s):* Simple, stateless REST polling with timeout and error handling.
* **Chosen Approach:** Short HTTP polling with client timeout and cancellation.
* **Rationale:**
  * Completely stateless and decoupled: standard HTTP requests work through any reverse proxy, firewall, or CORS configuration.
  * Simple cancellation lifecycle: when the user navigates away or submits a new search, polling halts instantly without leaking socket connections.
  * Includes a 2-second interval and a 10-minute maximum safety timeout.
* **Code Reference:** `frontend/src/api.js`, `frontend/src/App.jsx`

---

## 8. Storage Strategy: Shared Media Cache & Isolated Artifact Folders

* **Context:** Video downloads are bandwidth-intensive, and concurrent search runs must not overwrite each other's frame images or JSON files.
* **Alternatives Considered:**
  * *Single Shared Output Directory:* Overwrites previous results on every run, breaking historical job viewing.
  * *Temporary `/tmp` Storage:* Deletes files after request, preventing static image serving and history inspection.
  * *Two-Tier Storage (`media_cache/` + `results/{job_id}/`):* Shared media cache for heavy video/audio, isolated subfolders for job outputs.
* **Chosen Approach:** Shared `media_cache/` with isolated per-job result folders.
* **Rationale:**
  * **Media Caching:** Downloads are hashed by URL/filename in `backend/ml/results/media_cache/`. Repeating searches on the same video drops execution time from 60s to under 3 seconds.
  * **Artifact Isolation:** Every execution generates a folder `results/{job_id}/` containing `frame.png`, `frames/frame_N.png`, `transcript.json`, and `result.json`.
  * **Static File Serving:** Mounted directly at `/output` in FastAPI (`app.mount("/output", StaticFiles(...))`), allowing the frontend to load frame images as simple static URLs.
* **Code Reference:** `backend/ml/downloader.py`, `backend/app/main.py`, `backend/ml/locate_phrase.py`

---

## 9. Multilingual Support & Transliteration Handling

* **Context:** Videos may contain foreign languages, regional accents, or non-ASCII characters.
* **Alternatives Considered:**
  * *English-Only Whisper Models (`base.en`, `small.en`):* Faster on English, but fails completely on non-English audio.
  * *External Translation Pipelines (e.g., DeepL / Google Translate API):* Adds external dependency, cost, and latency.
  * *Multilingual Whisper with Unicode Normalization:* Use standard Whisper multilingual checkpoints and normalize Unicode strings.
* **Chosen Approach:** Multilingual Whisper architecture with robust Unicode normalization.
* **Rationale:**
  * Standard Whisper models (`tiny`, `base`, `small`, `medium`, `large`) support 99 languages natively with automatic language detection.
  * The normalization pipeline in `backend/ml/matcher.py` strips diacritics and accents using standard Unicode character substitutions, allowing phonetic fuzzy matching to bridge minor transliteration differences.
* **Code Reference:** `backend/ml/matcher.py`, `backend/ml/transcriber.py`

---

## 10. Error, Confidence & Ambiguity Handling

* **Context:** Audio quality can be degraded by background music, sound effects, or speech overlap. When a phrase is not found, returning an empty response leaves the user confused.
* **Alternatives Considered:**
  * *Binary True/False Response:* Returns `null` when no exact match is found.
  * *Candidate Ranking & Near-Miss Fallback:* Return top candidate dialogue segments ranked by similarity score when threshold is not met.
* **Chosen Approach:** Explicit state machine + top-5 candidate near-miss fallback.
* **Rationale:**
  * **State Machine:** Clear progression (`queued` -> `processing` -> `completed` / `failed`) with specific error strings on failure (e.g., "Invalid URL", "Audio extraction failed").
  * **Confidence Scoring:** Every match includes a confidence float (e.g., `0.96` / 96%) based on RapidFuzz token distance.
  * **Candidate Near-Misses:** If no segment meets the user's threshold (e.g., threshold set to 0.95, but best hit is 0.88), the backend returns the top 5 closest candidates with their timestamps and text. The UI renders these suggestions so the user can easily adjust their threshold slider.
* **Code Reference:** `backend/ml/locate_phrase.py`, `frontend/src/components/ResultDisplay.jsx`
