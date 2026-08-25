import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Union
import yt_dlp

try:
    import certifi
    ca_bundle = certifi.where()
    if os.path.exists(ca_bundle):
        os.environ["SSL_CERT_FILE"] = ca_bundle
        os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle
except ImportError:
    pass

# Clean up broken SSL_CERT_FILE if pointing to non-existent path
if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
    del os.environ["SSL_CERT_FILE"]

logger = logging.getLogger(__name__)


def get_video_fps(video_path: Union[str, Path], default_fps: float = 30.0) -> float:
    """
    Retrieves the frame rate (FPS) of a video file using ffprobe.
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        rate_str = result.stdout.strip()
        if "/" in rate_str:
            num, denom = rate_str.split("/", 1)
            if float(denom) != 0:
                return round(float(num) / float(denom), 3)
        elif rate_str:
            return round(float(rate_str), 3)
    except Exception as e:
        logger.debug("ffprobe FPS extraction failed (%s), defaulting to %s", e, default_fps)
    return default_fps


def download_video_and_audio(url: str, output_dir: Union[str, Path] = "media") -> Dict[str, Any]:
    """
    Downloads video and audio from a URL using yt-dlp, extracts 16kHz mono WAV for transcription,
    and returns media metadata including FPS.

    Args:
        url: The video URL (YouTube, ok.ru, etc.).
        output_dir: Directory where the video and audio files will be stored.

    Returns:
        dict: {
            "video_path": Path,
            "audio_path": Path,
            "fps": float,
            "duration": float,
            "title": str
        }
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    video_template = str(output_path / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best",
        "outtmpl": video_template,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "nocheckcertificate": True,
        "legacyserverconnect": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    logger.info("Downloading video and audio from URL: %s", url)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_id = info_dict.get("id", "video")
            video_title = info_dict.get("title", "")
            duration = float(info_dict.get("duration", 0.0) or 0.0)
            raw_fps = info_dict.get("fps")
            video_filepath = ydl.prepare_filename(info_dict)
    except Exception as e:
        logger.error("Failed to download video with yt-dlp: %s", e)
        raise RuntimeError(f"Failed to download video from URL: {e}") from e

    video_path = Path(video_filepath)
    if not video_path.exists():
        # Search if extension differed during merge (e.g. .mkv / .webm / .mp4)
        candidates = list(output_path.glob(f"{video_id}.*"))
        # Exclude .wav
        candidates = [c for c in candidates if c.suffix.lower() != ".wav"]
        if candidates:
            video_path = candidates[0]
        else:
            raise FileNotFoundError(f"Downloaded video file not found for video ID: {video_id}")

    # Determine FPS
    fps = float(raw_fps) if raw_fps else get_video_fps(video_path)

    # Convert audio track to 16kHz mono WAV for Whisper
    output_wav_path = output_path / f"{video_id}_16k_mono.wav"
    logger.info("Extracting 16kHz mono WAV audio: %s -> %s", video_path, output_wav_path)

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_wav_path)
    ]

    try:
        subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error("ffmpeg audio extraction failed: %s", e.stderr)
        raise RuntimeError(f"ffmpeg audio extraction failed: {e.stderr}") from e
    except FileNotFoundError as e:
        logger.error("ffmpeg executable not found in system PATH.")
        raise RuntimeError("ffmpeg executable not found in system PATH.") from e

    logger.info("Media ready. Video: %s, Audio: %s, FPS: %s", video_path, output_wav_path, fps)
    return {
        "video_path": video_path,
        "audio_path": output_wav_path,
        "fps": fps,
        "duration": duration,
        "title": video_title
    }


def extract_frame(
    video_path: Union[str, Path],
    timestamp: float,
    output_image_path: Union[str, Path]
) -> Path:
    """
    Extracts the exact video frame at a given timestamp in seconds as an image file (PNG).

    Args:
        video_path: Path to the source video file.
        timestamp: Timestamp in seconds.
        output_image_path: Path where the PNG image frame will be saved.

    Returns:
        Path: Path to the generated image file.
    """
    video_path = Path(video_path)
    output_path = Path(output_image_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Extracting video frame at %.3fs -> %s", timestamp, output_path)

    # ffmpeg -y -ss <timestamp> -i <video_path> -vframes 1 -q:v 2 <output_path>
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{timestamp:.3f}",
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path)
    ]

    try:
        subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error("ffmpeg frame extraction failed: %s", e.stderr)
        raise RuntimeError(f"ffmpeg frame extraction failed: {e.stderr}") from e
    except FileNotFoundError as e:
        logger.error("ffmpeg executable not found in system PATH.")
        raise RuntimeError("ffmpeg executable not found in system PATH.") from e

    return output_path


def download_audio(url: str, output_dir: Union[str, Path] = "audio") -> Path:
    """
    Legacy helper: Downloads audio only from a video URL and converts it to a 16kHz mono WAV file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    raw_template = str(output_path / "raw_audio_%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": raw_template,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "nocheckcertificate": True,
    }

    logger.info("Downloading audio from URL: %s", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        video_id = info_dict.get("id", "audio")
        raw_filepath = ydl.prepare_filename(info_dict)

    raw_audio_path = Path(raw_filepath)
    if not raw_audio_path.exists():
        candidates = list(output_path.glob(f"raw_audio_{video_id}.*"))
        if candidates:
            raw_audio_path = candidates[0]
        else:
            raise FileNotFoundError(f"Downloaded audio file not found for video ID: {video_id}")

    output_wav_path = output_path / f"{video_id}_16k_mono.wav"
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", str(raw_audio_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_wav_path)
    ]

    subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

    if raw_audio_path.exists() and raw_audio_path.resolve() != output_wav_path.resolve():
        try:
            raw_audio_path.unlink()
        except OSError:
            pass

    return output_wav_path
