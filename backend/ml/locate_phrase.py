#!/usr/bin/env python3
"""
Main pipeline module and CLI script to locate all occurrences of a spoken target phrase in a video,
extract corresponding video frame images (PNG), calculate frame numbers, and save formatted results
into a unique timestamped subfolder inside the results directory.

Can be run as a standalone CLI script:
    python locate_phrase.py <video_url> <target_phrase> [--model MODEL] [--threshold THRESHOLD] [--output-dir OUTPUT_DIR]

Or imported programmatically:
    from backend.ml.locate_phrase import run_pipeline
"""

import argparse
from datetime import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import certifi
    ca_bundle = certifi.where()
    if os.path.exists(ca_bundle):
        os.environ["SSL_CERT_FILE"] = ca_bundle
        os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle
except ImportError:
    pass

if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
    del os.environ["SSL_CERT_FILE"]

# Add current module directory to sys.path if invoked directly
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from downloader import download_video_and_audio, extract_frame
from transcriber import transcribe
from matcher import find_phrase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("locate_phrase")


def format_timestamp(seconds: float) -> str:
    """
    Formats a duration in seconds into HH:MM:SS.sss format.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def run_pipeline(
    video_url: str,
    target_phrase: str,
    model_size: str = "base",
    threshold: float = 0.9,
    output_base_dir: Union[str, Path] = "results",
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the end-to-end Video Dialogue Locator pipeline.

    Args:
        video_url: URL of the target video.
        target_phrase: Spoken phrase to search for in video dialogue.
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large').
        threshold: Fuzzy similarity threshold between 0.0 and 1.0.
        output_base_dir: Top-level results directory.
        run_id: Optional unique identifier for this run. If None, uses timestamp YYYYMMDD_HHMMSS.

    Returns:
        Dict[str, Any]: Structured execution summary with timestamps, frame numbers, matches, and file paths.
    """
    top_output_dir = Path(output_base_dir)
    if not top_output_dir.is_absolute():
        top_output_dir = CURRENT_DIR / top_output_dir
    top_output_dir.mkdir(parents=True, exist_ok=True)

    # Shared media cache for downloaded video and converted audio
    media_cache_dir = top_output_dir / "media_cache"
    media_cache_dir.mkdir(parents=True, exist_ok=True)

    # Dedicated subfolder for this run
    if not run_id:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    run_dir = top_output_dir / run_id
    counter = 1
    while run_dir.exists() and run_id.isdigit():
        run_dir = top_output_dir / f"{run_id}_{counter}"
        counter += 1
    run_dir.mkdir(parents=True, exist_ok=True)

    frames_dir = run_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    transcript_file = run_dir / "transcript.json"
    result_json_file = run_dir / "result.json"
    result_txt_file = run_dir / "result.txt"

    logger.info("=" * 60)
    logger.info("Starting Video Dialogue Locator Pipeline")
    logger.info("Target Phrase : \"%s\"", target_phrase)
    logger.info("Video URL     : %s", video_url)
    logger.info("Model Size    : %s", model_size)
    logger.info("Threshold     : %s", threshold)
    logger.info("Run Output Dir: %s", run_dir)
    logger.info("=" * 60)

    # Step 1: Download video & extract 16kHz audio (reuses local cache if available)
    logger.info("[Step 1/4] Checking media cache / downloading video...")
    media_info = download_video_and_audio(video_url, output_dir=media_cache_dir)
    video_path = media_info["video_path"]
    audio_path = media_info["audio_path"]
    fps = media_info.get("fps", 30.0)
    logger.info("Media ready: %s (%.2f FPS)", video_path.name, fps)

    # Step 2: Transcribe audio with Whisper
    logger.info("[Step 2/4] Transcribing audio with Whisper '%s'...", model_size)
    transcript = transcribe(
        audio_path=audio_path,
        model_size=model_size,
        output_json=transcript_file
    )
    logger.info("Transcription completed. Saved to: %s", transcript_file)

    # Step 3: Locate target phrase occurrences
    logger.info("[Step 3/4] Locating target phrase in transcript...")
    match_result = find_phrase(
        transcript=transcript,
        target=target_phrase,
        threshold=threshold
    )

    # Step 4: Extract video frames & generate results
    logger.info("[Step 4/4] Processing matches and extracting video frames...")

    txt_lines = []
    json_instances = []

    if match_result.get("status") == "found":
        instances = match_result.get("instances", [])
        if not instances and "start" in match_result:
            instances = [{
                "start": match_result["start"],
                "text": match_result["text"],
                "score": match_result["score"]
            }]

        primary_relative_image_path = ""

        for idx, inst in enumerate(instances, 1):
            start_sec = float(inst["start"])
            matched_text = inst["text"]
            score = float(inst["score"])
            formatted_ts = format_timestamp(start_sec)
            frame_num = int(round(start_sec * fps))

            safe_ts = formatted_ts.replace(":", "_").replace(".", "_")
            instance_frame_path = frames_dir / f"frame_{idx}_{safe_ts}.png"
            primary_frame_path = run_dir / "frame.png"

            try:
                extract_frame(video_path, start_sec, instance_frame_path)
                if idx == 1:
                    extract_frame(video_path, start_sec, primary_frame_path)
                # Path relative to output_base_dir so it can be served as /output/<relative_path>
                rel_to_base = str(instance_frame_path.relative_to(top_output_dir)).replace("\\", "/")
                rel_primary = str(primary_frame_path.relative_to(top_output_dir)).replace("\\", "/")
                if idx == 1:
                    primary_relative_image_path = rel_primary
            except Exception as e:
                logger.warning("Frame extraction failed for instance %d: %s", idx, e)
                rel_to_base = ""

            # Text report lines
            if len(instances) > 1:
                txt_lines.append(f"Instance {idx}:")
            txt_lines.append(f"Timestamp : {formatted_ts}")
            txt_lines.append(f"Frame : {frame_num}")
            txt_lines.append(f"Text : \"{matched_text}\"")
            if rel_to_base:
                txt_lines.append(f"Image : {rel_to_base}")
            txt_lines.append("")

            json_instances.append({
                "instance": idx,
                "timestamp": formatted_ts,
                "timestamp_seconds": start_sec,
                "frame_number": frame_num,
                "text": matched_text,
                "confidence": score,
                "image_path": rel_to_base
            })

        # Save result.txt
        with open(result_txt_file, "w", encoding="utf-8") as f:
            f.write("\n".join(txt_lines).strip() + "\n")

        # Save result.json
        primary_match = json_instances[0]
        json_payload = {
            "status": "found",
            "timestamp": primary_match["timestamp"],
            "timestamp_seconds": primary_match["timestamp_seconds"],
            "frame_number": primary_match["frame_number"],
            "text": primary_match["text"],
            "confidence": primary_match["confidence"],
            "image_path": primary_relative_image_path or primary_match["image_path"],
            "matches": json_instances,
            "fps": fps
        }
        with open(result_json_file, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2)

        return {
            "status": "found",
            "run_id": run_id,
            "run_dir": str(run_dir),
            "timestamp": primary_match["timestamp"],
            "timestamp_seconds": primary_match["timestamp_seconds"],
            "frame_number": primary_match["frame_number"],
            "text": primary_match["text"],
            "confidence": primary_match["confidence"],
            "image_path": primary_relative_image_path or primary_match["image_path"],
            "matches": json_instances,
            "fps": fps,
            "result_json_path": str(result_json_file),
            "result_txt_path": str(result_txt_file),
            "transcript_json_path": str(transcript_file)
        }

    else:
        candidates = match_result.get("candidates", [])
        top_5 = candidates[:5]

        txt_lines.append("Phrase not found above threshold. Best candidates:")
        formatted_candidates = []
        for idx, cand in enumerate(top_5, 1):
            formatted_ts = format_timestamp(cand["start"])
            frame_num = int(round(cand["start"] * fps))
            txt_lines.append(f"Candidate {idx}:")
            txt_lines.append(f"Timestamp : {formatted_ts}")
            txt_lines.append(f"Frame : {frame_num}")
            txt_lines.append(f"Text : \"{cand['text']}\"")
            txt_lines.append(f"Score : {cand['score']}")
            txt_lines.append("")

            formatted_candidates.append({
                "candidate": idx,
                "timestamp": formatted_ts,
                "timestamp_seconds": cand["start"],
                "frame_number": frame_num,
                "text": cand["text"],
                "score": cand["score"]
            })

        with open(result_txt_file, "w", encoding="utf-8") as f:
            f.write("\n".join(txt_lines).strip() + "\n")

        json_payload = {
            "status": "not_found",
            "candidates": candidates,
            "fps": fps
        }
        with open(result_json_file, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2)

        return {
            "status": "not_found",
            "run_id": run_id,
            "run_dir": str(run_dir),
            "timestamp": None,
            "timestamp_seconds": None,
            "frame_number": None,
            "text": None,
            "confidence": None,
            "image_path": None,
            "matches": [],
            "candidates": formatted_candidates,
            "fps": fps,
            "result_json_path": str(result_json_file),
            "result_txt_path": str(result_txt_file),
            "transcript_json_path": str(transcript_file)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Locate spoken target phrase in a video and extract dialogue timestamps & frames."
    )
    parser.add_argument("video_url", type=str, help="URL of the video (YouTube, ok.ru, etc.)")
    parser.add_argument("target_phrase", type=str, help="Target spoken phrase to locate")
    parser.add_argument(
        "--model",
        type=str,
        default="base",
        help="Whisper model size: tiny, base, small, medium, large (default: base)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.9,
        help="Fuzzy match similarity threshold between 0.0 and 1.0 (default: 0.9)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Top-level output directory to save results (default: results)"
    )

    args = parser.parse_args()

    result = run_pipeline(
        video_url=args.video_url,
        target_phrase=args.target_phrase,
        model_size=args.model,
        threshold=args.threshold,
        output_base_dir=args.output_dir
    )

    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)

    if result.get("status") == "found":
        matches = result.get("matches", [])
        for m in matches:
            print(f"\n--- Match Instance {m.get('instance', 1)} ---")
            print(f"Timestamp : {m.get('timestamp')} ({m.get('timestamp_seconds')}s)")
            print(f"Frame     : {m.get('frame_number')}")
            print(f"Text      : \"{m.get('text')}\" (score: {m.get('confidence')})")
            if m.get("image_path"):
                print(f"Image     : {m.get('image_path')}")
    else:
        print("Phrase not found above threshold. Best candidates:")
        for c in result.get("candidates", []):
            print(f"  {c['candidate']}. Score: {c['score']} | Timestamp: {c['timestamp']} (Frame {c['frame_number']}) | Text: \"{c['text']}\"")


if __name__ == "__main__":
    main()
