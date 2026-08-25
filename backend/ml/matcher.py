import logging
import re
from typing import Any, Dict, List
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def normalize(text: str) -> str:
    """
    Normalizes text by lowercasing, removing punctuation, and collapsing multiple spaces.

    Args:
        text: Input string.

    Returns:
        str: Normalized string.
    """
    if not text:
        return ""
    # Lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse multiple whitespace characters into single space and strip
    text = re.sub(r"\s+", " ", text).strip()
    return text


def cluster_overlapping_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extracts distinct spoken occurrences using temporal Non-Maximum Suppression (NMS).
    Greedily selects the highest-scoring candidate and suppresses overlapping candidate
    windows for that same spoken instance, avoiding transitive chaining of closely-spaced lines.
    """
    if not candidates:
        return []

    # Sort descending by similarity score, then earlier start time
    sorted_by_score = sorted(candidates, key=lambda c: (c["score"], -c["start"]), reverse=True)
    kept_instances: List[Dict[str, Any]] = []

    while sorted_by_score:
        best = sorted_by_score.pop(0)
        kept_instances.append(best)

        b_start = best["start"]
        b_end = best["end"]
        b_dur = max(0.5, b_end - b_start)

        remaining = []
        for cand in sorted_by_score:
            c_start = cand["start"]
            c_end = cand["end"]

            # Calculate temporal intersection
            overlap_start = max(b_start, c_start)
            overlap_end = min(b_end, c_end)
            overlap = max(0.0, overlap_end - overlap_start)

            # Check if this candidate belongs to the same spoken occurrence
            is_same_occurrence = (
                overlap > 0.35 * b_dur
                or abs(c_start - b_start) < 0.75 * b_dur
                or (c_start >= b_start and c_start <= b_end)
                or (b_start >= c_start and b_start <= c_end)
            )

            if not is_same_occurrence:
                remaining.append(cand)

        sorted_by_score = remaining

    # Return distinct instances ordered chronologically by timestamp
    return sorted(kept_instances, key=lambda c: c["start"])


def find_phrase(transcript: dict, target: str, threshold: float = 0.9) -> dict:
    """
    Locates all occurrences of the target phrase in the Whisper transcript using a sliding window
    over word-level timestamps.

    Args:
        transcript: Dict returned by Whisper containing segments and word timestamps.
        target: Spoken phrase to search for.
        threshold: Fuzzy match score threshold between 0.0 and 1.0 (default: 0.9).

    Returns:
        dict:
            If found: {
                "status": "found",
                "start": float,
                "text": str,
                "score": float,
                "instances": [...],
                "candidates": [...]
            }
            If not found: {
                "status": "not_found",
                "candidates": [...]
            }
    """
    norm_target = normalize(target)
    target_words = norm_target.split()
    n_words = len(target_words)

    if not norm_target or n_words == 0:
        logger.warning("Target phrase is empty after normalization.")
        return {"status": "not_found", "candidates": [], "instances": []}

    # Extract all words from transcript segments
    words_list: List[Dict[str, Any]] = []
    segments = transcript.get("segments", [])

    for segment in segments:
        segment_words = segment.get("words", [])
        if segment_words:
            for w in segment_words:
                words_list.append({
                    "word": str(w.get("word", "")).strip(),
                    "start": float(w.get("start", 0.0)),
                    "end": float(w.get("end", 0.0)),
                    "score": float(w.get("probability", w.get("score", 1.0))),
                })
        else:
            # Fallback if segment does not have 'words' key
            seg_text = segment.get("text", "").strip()
            seg_start = float(segment.get("start", 0.0))
            seg_end = float(segment.get("end", 0.0))
            for raw_w in seg_text.split():
                words_list.append({
                    "word": raw_w,
                    "start": seg_start,
                    "end": seg_end,
                    "score": 1.0,
                })

    if not words_list:
        logger.warning("No words found in transcript.")
        return {"status": "not_found", "candidates": [], "instances": []}

    all_candidates: List[Dict[str, Any]] = []
    total_words = len(words_list)

    # Dynamic multi-scale window sizing (+/- 1 word for punctuation, compound words, or missing spaces)
    min_window = max(1, n_words - 1)
    max_window = min(total_words, n_words + 1)

    for w_size in range(min_window, max_window + 1):
        for i in range(total_words - w_size + 1):
            window = words_list[i : i + w_size]
            window_raw_text = " ".join(w["word"] for w in window)
            norm_window = normalize(window_raw_text)

            ratio = fuzz.ratio(norm_target, norm_window) / 100.0
            token_sort = fuzz.token_sort_ratio(norm_target, norm_window) / 100.0

            # Safe length-penalized partial ratio
            len_ratio = (
                min(len(norm_target), len(norm_window)) / max(len(norm_target), len(norm_window))
                if max(len(norm_target), len(norm_window)) > 0
                else 0
            )
            partial_ratio = (fuzz.partial_ratio(norm_target, norm_window) / 100.0) * (len_ratio ** 0.5)

            match_score = max(ratio, token_sort, partial_ratio)

            start_time = float(window[0]["start"])
            end_time = float(window[-1]["end"])

            all_candidates.append({
                "start": round(start_time, 3),
                "end": round(end_time, 3),
                "text": window_raw_text,
                "score": round(match_score, 4),
            })

    # Sort all candidates descending by score
    all_candidates.sort(key=lambda c: c["score"], reverse=True)

    # Filter matches meeting or exceeding threshold
    matches_above_threshold = [c for c in all_candidates if c["score"] >= threshold]

    if matches_above_threshold:
        # Group overlapping windows to get distinct occurrences
        distinct_instances = cluster_overlapping_candidates(matches_above_threshold)
        best_match = max(distinct_instances, key=lambda c: c["score"])

        return {
            "status": "found",
            "start": float(best_match["start"]),
            "text": str(best_match["text"]),
            "score": float(best_match["score"]),
            "instances": distinct_instances,
            "candidates": matches_above_threshold,
        }
    else:
        top_10 = all_candidates[:10]
        return {
            "status": "not_found",
            "instances": [],
            "candidates": top_10,
        }
