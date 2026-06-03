"""Video analysis via Replicate only (production path)."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.schemas.analysis import GeminiAnalysisResult
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

_PRODUCTION_PROVIDER = "replicate"


def get_video_provider_mode() -> str:
    """Effective provider — always Replicate in production."""
    configured = (settings.VIDEO_PROVIDER or _PRODUCTION_PROVIDER).strip().lower()
    if configured != _PRODUCTION_PROVIDER:
        logger.warning(
            "VIDEO_PROVIDER=%s is ignored; production uses Replicate only",
            configured,
        )
    return _PRODUCTION_PROVIDER


def start_analysis(
    storage_path: str,
    *,
    file_id: str | None = None,
    file_size: int | None = None,
    expected_duration_seconds: int | None = None,
    extra_prompt_suffix: str = "",
) -> str:
    return gemini_service.start_analysis(
        storage_path,
        file_id=file_id,
        file_size=file_size,
        expected_duration_seconds=expected_duration_seconds,
        extra_prompt_suffix=extra_prompt_suffix,
    )


def poll_prediction(prediction_id: str) -> tuple[str, GeminiAnalysisResult | None]:
    return gemini_service.poll_prediction(prediction_id)
