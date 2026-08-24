import json
import logging
from pathlib import Path
from typing import Optional, Union
import whisper

logger = logging.getLogger(__name__)


def transcribe(
    audio_path: Union[str, Path],
    model_size: str = "medium",
    output_json: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Transcribes an audio file using OpenAI Whisper with word-level timestamps.

    Args:
        audio_path: Path to the input audio file (e.g. 16kHz mono WAV).
        model_size: Whisper model size ("tiny", "base", "small", "medium", "large", etc.).
        output_json: Optional file path to save the full transcript JSON.

    Returns:
        dict: Full transcription result including segments and word-level timestamps.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    logger.info("Loading Whisper model '%s'...", model_size)
    try:
        model = whisper.load_model(model_size)
    except Exception as e:
        logger.error("Failed to load Whisper model '%s': %s", model_size, e)
        raise RuntimeError(f"Error loading Whisper model '{model_size}': {e}") from e

    logger.info("Transcribing audio '%s' with word_timestamps=True...", audio_path)
    try:
        result = model.transcribe(str(audio_path), word_timestamps=True)
    except Exception as e:
        logger.error("Transcription failed for '%s': %s", audio_path, e)
        raise RuntimeError(f"Transcription failed: {e}") from e

    if output_json is not None:
        json_path = Path(output_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Saving full transcript to '%s'...", json_path)
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Failed to save transcript to '%s': %s", json_path, e)

    return result
