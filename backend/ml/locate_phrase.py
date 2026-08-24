#!/usr/bin/env python3
"""
Main pipeline script to locate all occurrences of a spoken target phrase in a video,
extract corresponding video frame images (PNG), calculate frame numbers, and save formatted results.

Usage:
    python locate_phrase.py <video_url> <target_phrase> [--model MODEL] [--threshold THRESHOLD] [--output-dir OUTPUT_DIR]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser(
        description="Locate spoken target phrase in a video and extract dialogue timestamps & frames."
    )
    parser.add_argument("video_url", type=str, help="URL of the video (YouTube, ok.ru, etc.)")
    parser.add_argument("target_phrase", type=str, help="Target spoken phrase to locate")
    parser.add_argument(
        "--model",
        type=str,
        default="medium",
        help="Whisper model size: tiny, base, small, medium, large (default: medium)"
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
        default="output",
        help="Output directory to save artifacts (default: output)"
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = CURRENT_DIR / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    media_dir = output_dir / "media"
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    transcript_file = output_dir / "transcript.json"
    result_json_file = output_dir / "result.json"
    results_txt_file = output_dir / "results.txt"

    print("=" * 60)
    print("Video Dialogue Locator Pipeline")
    print(f"Target Phrase : \"{args.target_phrase}\"")
    print(f"Video URL     : {args.video_url}")
    print(f"Model Size    : {args.model}")
    print(f"Threshold     : {args.threshold}")
    print(f"Output Dir    : {output_dir}")
    print("=" * 60)

    # Step 1: Download video and convert audio
    logger.info("[Step 1/4] Downloading video & extracting audio...")
    try:
        media_info = download_video_and_audio(args.video_url, output_dir=media_dir)
        video_path = media_info["video_path"]
        audio_path = media_info["audio_path"]
        fps = media_info.get("fps", 30.0)
        logger.info("Video ready (%s, %.2f FPS), Audio ready (%s)", video_path.name, fps, audio_path.name)
    except Exception as e:
        logger.error("Step 1 failed: %s", e)
        sys.exit(1)

    # Step 2: Transcribe audio
    logger.info("[Step 2/4] Transcribing audio using Whisper '%s'...", args.model)
    try:
        transcript = transcribe(
            audio_path=audio_path,
            model_size=args.model,
            output_json=transcript_file
        )
        logger.info("Transcription completed. Saved to: %s", transcript_file)
    except Exception as e:
        logger.error("Step 2 failed: %s", e)
        sys.exit(1)

    # Step 3: Fuzzy match phrase
    logger.info("[Step 3/4] Locating phrase occurrences in transcript...")
    try:
        match_result = find_phrase(
            transcript=transcript,
            target=args.target_phrase,
            threshold=args.threshold
        )
    except Exception as e:
        logger.error("Step 3 failed: %s", e)
        sys.exit(1)

    # Step 4: Frame extraction & Result generation
    logger.info("[Step 4/4] Processing matches and extracting video frames...")

    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)

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

        for idx, inst in enumerate(instances, 1):
            start_sec = float(inst["start"])
            matched_text = inst["text"]
            score = float(inst["score"])
            formatted_ts = format_timestamp(start_sec)
            frame_num = int(round(start_sec * fps))

            # Frame image filename
            safe_ts = formatted_ts.replace(":", "_").replace(".", "_")
            frame_filename = f"frame_{idx}_{safe_ts}.png"
            frame_output_path = frames_dir / frame_filename

            # Extract exact video frame
            try:
                extract_frame(video_path, start_sec, frame_output_path)
                relative_frame_path = str(frame_output_path.relative_to(output_dir))
            except Exception as e:
                logger.warning("Frame extraction failed for instance %d: %s", idx, e)
                relative_frame_path = ""

            # Print to console
            print(f"\n--- Match Instance {idx} ---")
            print(f"Timestamp : {formatted_ts} ({start_sec:.2f}s)")
            print(f"Frame     : {frame_num}")
            print(f"Text      : \"{matched_text}\" (score: {score})")
            if relative_frame_path:
                print(f"Image     : {relative_frame_path}")

            # Append to text output
            if len(instances) > 1:
                txt_lines.append(f"Instance {idx}:")
            txt_lines.append(f"Timestamp : {formatted_ts}")
            txt_lines.append(f"Frame : {frame_num}")
            txt_lines.append(f"Text : \"{matched_text}\"")
            if relative_frame_path:
                txt_lines.append(f"Image : {relative_frame_path}")
            txt_lines.append("")

            json_instances.append({
                "instance": idx,
                "timestamp_formatted": formatted_ts,
                "timestamp_seconds": start_sec,
                "frame_number": frame_num,
                "text": matched_text,
                "confidence": score,
                "image_path": str(frame_output_path)
            })

        # Save results.txt
        with open(results_txt_file, "w", encoding="utf-8") as f:
            f.write("\n".join(txt_lines).strip() + "\n")
        logger.info("Formatted text results saved to: %s", results_txt_file)

        # Save result.json
        primary_match = json_instances[0]
        json_payload = {
            "status": "found",
            "timestamp": primary_match["timestamp_seconds"],
            "timestamp_formatted": primary_match["timestamp_formatted"],
            "frame_number": primary_match["frame_number"],
            "text": primary_match["text"],
            "confidence": primary_match["confidence"],
            "image_path": primary_match["image_path"],
            "instances": json_instances,
            "fps": fps
        }
        with open(result_json_file, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2)
        logger.info("JSON result saved to: %s", result_json_file)

    else:
        print("Phrase not found above threshold. Best candidates:")
        candidates = match_result.get("candidates", [])
        top_5 = candidates[:5]
        for idx, cand in enumerate(top_5, 1):
            formatted_ts = format_timestamp(cand["start"])
            frame_num = int(round(cand["start"] * fps))
            print(f"  {idx}. Score: {cand['score']} | Timestamp: {formatted_ts} (Frame {frame_num}) | Text: \"{cand['text']}\"")

        txt_lines.append("Phrase not found above threshold. Best candidates:")
        for idx, cand in enumerate(top_5, 1):
            formatted_ts = format_timestamp(cand["start"])
            frame_num = int(round(cand["start"] * fps))
            txt_lines.append(f"Candidate {idx}:")
            txt_lines.append(f"Timestamp : {formatted_ts}")
            txt_lines.append(f"Frame : {frame_num}")
            txt_lines.append(f"Text : \"{cand['text']}\"")
            txt_lines.append(f"Score : {cand['score']}")
            txt_lines.append("")

        with open(results_txt_file, "w", encoding="utf-8") as f:
            f.write("\n".join(txt_lines).strip() + "\n")

        json_payload = {
            "status": "not_found",
            "candidates": candidates,
            "fps": fps
        }
        with open(result_json_file, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2)
        logger.info("Results saved to: %s and %s", results_txt_file, result_json_file)


if __name__ == "__main__":
    main()
