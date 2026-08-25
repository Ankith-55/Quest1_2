import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure backend root is in sys.path so 'ml' package can be imported reliably
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from ml.locate_phrase import run_pipeline
except ImportError:
    from backend.ml.locate_phrase import run_pipeline

from app.api.schemas import JobCreateRequest
from app.core.config import settings
from app.services.job_manager import job_manager

logger = logging.getLogger(__name__)


def process_job(job_id: str, request_data: JobCreateRequest) -> None:
    """
    Background worker function that executes the ML dialogue locator pipeline
    and updates the job state.
    """
    logger.info("Starting background processing for Job ID: %s", job_id)
    job_manager.set_processing(job_id)

    try:
        output_base_dir = settings.get_output_base_path()
        model_size = request_data.model_size or settings.MODEL_SIZE
        threshold = request_data.threshold if request_data.threshold is not None else settings.FUZZY_THRESHOLD

        raw_result = run_pipeline(
            video_url=request_data.url,
            target_phrase=request_data.target_text,
            model_size=model_size,
            threshold=threshold,
            output_base_dir=output_base_dir,
            run_id=job_id,
        )

        # Build formatted matches with image_url
        matches = []
        for m in raw_result.get("matches", []):
            img_rel = m.get("image_path")
            img_url = f"/output/{img_rel}" if img_rel else None
            matches.append({
                "instance": m.get("instance", 1),
                "timestamp": m.get("timestamp"),
                "timestamp_seconds": m.get("timestamp_seconds"),
                "frame_number": m.get("frame_number"),
                "text": m.get("text"),
                "confidence": m.get("confidence"),
                "image_path": img_rel,
                "image_url": img_url,
            })

        primary_img_rel = raw_result.get("image_path")
        primary_img_url = f"/output/{primary_img_rel}" if primary_img_rel else None

        formatted_result: Dict[str, Any] = {
            "status": raw_result.get("status", "not_found"),
            "timestamp": raw_result.get("timestamp"),
            "timestamp_seconds": raw_result.get("timestamp_seconds"),
            "frame_number": raw_result.get("frame_number"),
            "text": raw_result.get("text"),
            "confidence": raw_result.get("confidence"),
            "image_path": primary_img_rel,
            "image_url": primary_img_url,
            "matches": matches,
            "candidates": raw_result.get("candidates", []),
            "fps": raw_result.get("fps"),
        }

        job_manager.set_completed(job_id, formatted_result)
        logger.info("Job %s completed successfully (status: %s)", job_id, raw_result.get("status"))

    except Exception as e:
        logger.exception("Error processing Job ID %s: %s", job_id, e)
        job_manager.set_failed(job_id, str(e))
