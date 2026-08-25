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


def download_video_and_audio(url: str, output_dir: Union[str, Path] = "media_cache") -> Dict[str, Any]:
    """
    Downloads video and audio from a URL using yt-dlp, extracts 16kHz mono WAV for transcription,
    and returns media metadata including FPS. Reuses already downloaded media if found in cache.

    Args:
        url: The video URL (YouTube, ok.ru, etc.).
        output_dir: Directory where the video and audio files will be cached.

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

    # Step 0: Check if url is a local file path or matches a local video in backend directory
    raw_path = Path(url)
    backend_root = Path(__file__).resolve().parent.parent
    local_candidates = [
        raw_path,
        backend_root / url,
        backend_root / raw_path.name,
    ]
    # Also search for local files containing the video ID or name in backend directory
    if not any(p.exists() and p.is_file() for p in local_candidates):
        for local_f in backend_root.glob("*.mp4"):
            if raw_path.name in local_f.name or (len(url) > 5 and url in local_f.name):
                local_candidates.append(local_f)
                break

    for local_file in local_candidates:
        if local_file.exists() and local_file.is_file() and local_file.stat().st_size > 1000000: # > 1MB
            video_path = local_file
            video_id = "".join(c for c in video_path.stem if c.isalnum()) or "local_video"
            cached_wav = output_path / f"{video_id}_16k_mono.wav"
            fps = get_video_fps(video_path)

            if not cached_wav.exists() or cached_wav.stat().st_size == 0:
                logger.info("Extracting 16kHz mono WAV from local video: %s -> %s", video_path, cached_wav)
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", str(video_path),
                    "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                    str(cached_wav)
                ]
                subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

            logger.info("Using local video (%s) and audio (%s).", video_path.name, cached_wav.name)
            return {
                "video_path": video_path,
                "audio_path": cached_wav,
                "fps": fps,
                "duration": 0.0,
                "title": video_path.stem
            }

    # Step A: Check if video and audio are already in local cache
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_id = info_dict.get("id", "video")
            video_title = info_dict.get("title", "")
            duration = float(info_dict.get("duration", 0.0) or 0.0)
            raw_fps = info_dict.get("fps")

            # Check if there is an existing full local video with this ID in backend root
            for local_f in backend_root.glob(f"*{video_id}*.mp4"):
                if local_f.stat().st_size > 10000000: # > 10MB
                    video_path = local_f
                    fps = float(raw_fps) if raw_fps else get_video_fps(video_path)
                    cached_wav = output_path / f"{video_id}_16k_mono.wav"
                    if not cached_wav.exists() or cached_wav.stat().st_size < 1000000:
                        logger.info("Extracting full 16kHz mono WAV from local video: %s -> %s", video_path, cached_wav)
                        ffmpeg_cmd = [
                            "ffmpeg", "-y", "-i", str(video_path),
                            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                            str(cached_wav)
                        ]
                        subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                    logger.info("Using local full video (%s) for ID %s.", video_path.name, video_id)
                    return {
                        "video_path": video_path,
                        "audio_path": cached_wav,
                        "fps": fps,
                        "duration": duration,
                        "title": video_title or video_path.stem
                    }

            candidates = list(output_path.glob(f"{video_id}.*"))
            candidates = [c for c in candidates if c.suffix.lower() not in [".wav", ".part", ".ytdl"]]
            cached_wav = output_path / f"{video_id}_16k_mono.wav"

            # Check if an incomplete download part file exists
            has_part_file = any(output_path.glob(f"{video_id}.*part*"))

            if candidates and candidates[0].stat().st_size > 50000000 and not has_part_file:
                video_path = candidates[0]
                fps = float(raw_fps) if raw_fps else get_video_fps(video_path)

                # Ensure 16k WAV exists too
                if not cached_wav.exists() or cached_wav.stat().st_size == 0:
                    logger.info("Extracting 16kHz mono WAV from cached video: %s -> %s", video_path, cached_wav)
                    ffmpeg_cmd = [
                        "ffmpeg", "-y", "-i", str(video_path),
                        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                        str(cached_wav)
                    ]
                    subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

                logger.info("Using cached video (%s) and audio (%s). Skipping download!", video_path.name, cached_wav.name)
                return {
                    "video_path": video_path,
                    "audio_path": cached_wav,
                    "fps": fps,
                    "duration": duration,
                    "title": video_title
                }
    except Exception as e:
        logger.debug("Cache lookup notice: %s. Proceeding with download.", e)

    # Step B: Download video if not in cache
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
        candidates = list(output_path.glob(f"{video_id}.*"))
        candidates = [c for c in candidates if c.suffix.lower() not in [".wav", ".part", ".ytdl"]]
        if candidates:
            video_path = candidates[0]
        else:
            raise FileNotFoundError(f"Downloaded video file not found for video ID: {video_id}")

    # Determine FPS
    fps = float(raw_fps) if raw_fps else get_video_fps(video_path)

    # Convert audio track to 16kHz mono WAV for Whisper
    output_wav_path = output_path / f"{video_id}_16k_mono.wav"
    if not output_wav_path.exists() or output_wav_path.stat().st_size == 0:
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
