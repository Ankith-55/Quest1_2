import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Video Dialogue Locator API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = ""

    # ML Pipeline Defaults
    MODEL_SIZE: str = "base"
    FUZZY_THRESHOLD: float = 0.9

    # Directories (relative to backend directory by default)
    OUTPUT_BASE_DIR: str = "ml/results"
    MEDIA_CACHE_DIR: str = "ml/results/media_cache"

    MAX_CONCURRENT_JOBS: int = 2
    CORS_ORIGINS: List[str] = ["*"]

    def get_output_base_path(self) -> Path:
        """
        Resolves the absolute path to the top-level results directory.
        """
        p = Path(self.OUTPUT_BASE_DIR)
        if not p.is_absolute():
            backend_root = Path(__file__).resolve().parent.parent.parent
            p = (backend_root / p).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_media_cache_path(self) -> Path:
        """
        Resolves the absolute path to the media cache directory.
        """
        p = Path(self.MEDIA_CACHE_DIR)
        if not p.is_absolute():
            backend_root = Path(__file__).resolve().parent.parent.parent
            p = (backend_root / p).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


settings = Settings()
