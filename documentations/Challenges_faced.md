# Key Challenges Faced & Solutions

---

### 1. Multiple Outputs & Overlapping Detections
* **Challenge:** Early implementations either returned only a single occurrence or generated multiple redundant frames for the same utterance due to closely adjacent sliding-window hits.
* **Resolution:** Implemented temporal Non-Maximum Suppression (NMS) in `matcher.py` to suppress overlapping window duplicates while preserving all distinct spoken dialogue occurrences across the video in a multi-match visual gallery.

---

### 2. Balancing Whisper Multiple Model Sizes
* **Challenge:** Balancing inference speed against transcription accuracy across varying hardware setups; `tiny` models struggled with background audio and heavy accents, whereas `large` models caused severe latency on CPU environments.
* **Resolution:** Implemented configurable model selection (`tiny`, `base`, `small`, `medium`, `large`) defaulting to `base`/`small`, providing an optimal ~8–15s runtime while allowing on-demand escalation for difficult audio.

---

### 3. Geoblocking & ISP Restrictions on Video Platforms (e.g., ok.ru)
* **Challenge:** Direct downloads and streaming from websites like `ok.ru` were inaccessible and timed out on Indian IP addresses due to regional ISP blocks and georestrictions unless routed through a VPN.

---

### 4. Client Polling & Lifecycle Management in Early Versions
* **Challenge:** Earlier iterations had polling instability where switching jobs or re-submitting queries caused race conditions, memory leaks, and indefinite polling on network disconnects.
* **Resolution:** Refactored the polling engine in `frontend/src/api.js` and `App.jsx` with active cancellation refs (`useRef`), automated terminal state detection, and a 10-minute timeout safeguard.

---

### 5. Media Ingestion & Bandwidth Caching
* **Challenge:** Re-downloading multi-gigabyte video streams for every new search query consumed excessive bandwidth, slowed execution to minutes, and risked YouTube rate-limiting/throttling.
* **Resolution:** Created a persistent `media_cache/` directory that stores downloaded videos and extracted 16kHz mono WAV audio, reducing repeat search runtimes from 60+ seconds to under 3 seconds.

---

### 6. Structured Artifact Storage & Overwrite Prevention
* **Challenge:** Early prototype scripts wrote all outputs to a single static folder, overwriting transcripts, JSON reports, and extracted frame images on every new run.
* **Resolution:** Established an isolated per-job directory structure (`results/{job_id}/`) containing structured `result.json`, `result.txt`, `transcript.json`, and frame PNGs, served cleanly via FastAPI static mounts.
