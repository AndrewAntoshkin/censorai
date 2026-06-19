"""Direct Google AI Studio analysis: primary path and Replicate E001 fallback."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.project import VideoFile
from app.schemas.analysis import GeminiAnalysisResult

logger = logging.getLogger(__name__)

DIRECT_PREDICTION_PENDING = "direct:pending"
DIRECT_SEGMENTED_KEY = "direct_segmented"


def direct_gemini_is_primary() -> bool:
    return (
        settings.ANALYSIS_PRIMARY_PROVIDER or ""
    ).strip().lower() == "direct_gemini" and direct_gemini_fallback_enabled()


async def setup_direct_analysis(
    db: AsyncSession,
    video: VideoFile,
    *,
    total_seconds: int | None,
    extra_prompt_suffix: str = "",
    prompt_override: str | None = None,
) -> None:
    """Mark a file for direct Gemini; plan segments when the video is long."""
    from app.services.analysis_jobs import set_job_metadata
    from app.services.video_segmentation import (
        needs_segmentation,
        plan_segment_ranges,
        size_aware_segment_seconds,
    )

    # Cap segment length by both duration and bytes, so high-bitrate files are
    # split into upload-safe chunks even when they are short.
    max_seg = size_aware_segment_seconds(
        total_seconds,
        video.size,
        settings.GEMINI_DIRECT_SEGMENT_SECONDS,
        settings.GEMINI_DIRECT_MAX_SEGMENT_MB,
    )
    if total_seconds and needs_segmentation(total_seconds, max_seg):
        ranges = plan_segment_ranges(total_seconds, max_seg)
        metadata = {
            DIRECT_SEGMENTED_KEY: True,
            "total_duration_sec": total_seconds,
            "ranges": [
                {"start_sec": start, "duration_sec": dur} for start, dur in ranges
            ],
            "source_path": video.storage_path or "",
            "current_index": 0,
            "partial_results": [],
            "extra_prompt_suffix": extra_prompt_suffix,
            "prompt_override": prompt_override,
        }
        await set_job_metadata(db, video.id, metadata)
        logger.info(
            "Direct Gemini: file %s split into %d segment(s) of <=%ds",
            video.id,
            len(ranges),
            max_seg,
        )

    video.status = "analyzing"
    video.replicate_prediction_id = DIRECT_PREDICTION_PENDING
    video.progress = max(video.progress or 0, 30)
    await db.flush()


def run_direct_segment_sync(
    source_path: str,
    start_sec: int,
    duration_sec: int,
    *,
    file_id: str,
    index: int,
    total: int,
    extra_prompt_suffix: str = "",
    prompt_override: str | None = None,
) -> GeminiAnalysisResult:
    """Cut one segment to a local temp and analyze it via direct Gemini."""
    from app.services.gemini_service import gemini_service
    from app.services.video_segmentation import (
        prepare_single_segment_file,
        segment_prompt_suffix,
    )

    local_path, temps = prepare_single_segment_file(
        source_path, start_sec, duration_sec, index=index, file_id=file_id
    )
    try:
        extra = (extra_prompt_suffix or "") + segment_prompt_suffix(
            index, total, start_sec, duration_sec
        )
        return gemini_service.analyze_local_file_direct(
            local_path,
            expected_duration_seconds=duration_sec,
            extra_prompt_suffix=extra,
            prompt_override=prompt_override,
        )
    finally:
        for path in temps:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass


def direct_gemini_fallback_enabled() -> bool:
    return bool(settings.GEMINI_API_KEY.strip())


def direct_prediction_running_marker() -> str:
    return f"direct:running:{int(time.time())}"


def is_direct_prediction_id(prediction_id: str | None) -> bool:
    return bool(prediction_id and prediction_id.startswith("direct:"))


def is_direct_running(prediction_id: str | None) -> bool:
    return bool(prediction_id and prediction_id.startswith("direct:running"))


def direct_running_is_stale(prediction_id: str | None, *, stale_seconds: int = 600) -> bool:
    if not is_direct_running(prediction_id):
        return False
    parts = (prediction_id or "").split(":")
    if len(parts) < 3:
        return True
    try:
        started = int(parts[2])
    except ValueError:
        return True
    return (time.time() - started) > stale_seconds


def should_use_direct_gemini_fallback(exc: Exception | str) -> bool:
    if not direct_gemini_fallback_enabled():
        return False
    msg = str(exc).lower()
    markers = (
        "e001",
        "uploading videos to gemini",
        "modelerror",
        "prediction failed",
        "prediction ended with status failed",
    )
    return any(marker in msg for marker in markers)


async def schedule_direct_gemini_fallback(
    db: AsyncSession,
    file_id: str,
    *,
    reason: str,
) -> bool:
    """Mark file for direct Gemini on the next poll. Returns True if scheduled."""
    if not direct_gemini_fallback_enabled():
        return False

    row = await db.execute(
        select(VideoFile)
        .where(VideoFile.id == file_id)
        .with_for_update(skip_locked=True)
    )
    locked = row.scalar_one_or_none()
    if not locked or locked.status != "analyzing":
        return False
    if is_direct_prediction_id(locked.replicate_prediction_id):
        return True

    logger.warning(
        "Scheduling direct Gemini fallback for %s (%s)",
        file_id,
        reason[:200],
    )
    locked.replicate_prediction_id = DIRECT_PREDICTION_PENDING
    locked.progress = max(locked.progress or 0, 35)
    await db.flush()
    return True
