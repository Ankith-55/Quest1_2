"""
ML Pipeline Package for Video Dialogue Locator.
"""

from .downloader import (
    download_audio,
    download_video_and_audio,
    extract_frame,
    get_video_fps,
)
from .transcriber import transcribe
from .matcher import find_phrase, normalize

__all__ = [
    "download_audio",
    "download_video_and_audio",
    "extract_frame",
    "get_video_fps",
    "transcribe",
    "find_phrase",
    "normalize",
]
