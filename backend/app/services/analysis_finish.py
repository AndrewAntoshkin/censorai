"""Finalize in-flight Replicate video analyses without blocking Neon."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.project import VideoFile
from app.schemas.analysis import GeminiAnalysisResult
from app.services.analysis_errors import (
    ContentBlockedError,
    build_full_review_result,
    build_review_scene,
)
from app.services.direct_gemini_fallback import (
    DIRECT_PREDICTION_PENDING,
    DIRECT_SEGMENTED_KEY,
    direct_prediction_running_marker,
    direct_running_is_stale,
    is_direct_prediction_id,
    is_direct_running,
    run_direct_segment_sync,
    schedule_direct_gemini_fallback,
    should_use_direct_gemini_fallback,
)
from app.services.video_analysis_provider import poll_prediction

logger = logging.getLogger(__name__)


async def maybe_finish_direct_gemini(
    video: VideoFile,
    db: AsyncSession,
    *,
    save_result,
) -> bool:
    """Drive direct Gemini analysis (single or segmented). Returns True if handled."""
    pred = video.replicate_prediction_id or ""
    if not is_direct_prediction_id(pred):
        return False

    file_id = video.id
    if video.status != "analyzing":
        return True

    if is_direct_running(pred):
        # A sibling invocation is processing a segment. Reschedule only if it
        # has clearly died (stale), otherwise just nudge progress.
        if direct_running_is_stale(pred):
            await _reset_direct_to_pending(file_id, db, reason="stale direct:running")
        else:
            await _bump_progress(file_id, db)
        return True

    if pred != DIRECT_PREDICTION_PENDING:
        await _reset_direct_to_pending(file_id, db, reason=f"unknown marker {pred}")
        return True

    # Claim in a fresh, short-lived session, then release the request's own
    # connection. The Gemini call below blocks for 150-200s; Neon drops idle
    # serverless connections, so we must NOT hold any connection across it.
    claim = await _claim_direct_step(file_id)
    if claim is None:
        return True
    running_marker, storage_path, file_size, duration_seconds, metadata = claim

    # Release the request's connection (Neon drops it if held idle during the
    # 150-200s Gemini call). commit() keeps `video` attached for the caller.
    try:
        await db.commit()
    except Exception:
        logger.debug("Failed to commit request session before direct work", exc_info=True)

    if not storage_path:
        await _fail_direct_gemini_fresh(file_id, "File has no storage path")
        return True

    if metadata.get(DIRECT_SEGMENTED_KEY):
        await _run_direct_segment(
            file_id, running_marker, metadata, save_result=save_result
        )
    else:
        await _run_direct_single(
            file_id,
            running_marker,
            storage_path,
            file_size,
            duration_seconds,
            save_result=save_result,
        )
    return True


async def _claim_direct_step(
    file_id: str,
) -> tuple[str, str | None, int | None, float | None, dict] | None:
    """Flip pending -> running under a lock; return work params + job metadata."""
    from app.services.analysis_jobs import get_job_metadata

    async with async_session_factory() as s:
        row = await s.execute(
            select(VideoFile)
            .where(VideoFile.id == file_id)
            .with_for_update(skip_locked=True)
        )
        locked = row.scalar_one_or_none()
        if not locked or locked.status != "analyzing":
            return None
        if locked.replicate_prediction_id != DIRECT_PREDICTION_PENDING:
            return None
        running_marker = direct_prediction_running_marker()
        locked.replicate_prediction_id = running_marker
        storage_path = locked.storage_path
        file_size = locked.size
        duration_seconds = locked.duration_seconds
        await s.flush()
        metadata = await get_job_metadata(s, file_id)
        await s.commit()
    return running_marker, storage_path, file_size, duration_seconds, metadata


async def _run_direct_single(
    file_id: str,
    running_marker: str,
    storage_path: str,
    file_size: int | None,
    duration_seconds: float | None,
    *,
    save_result,
) -> None:
    from app.services.analysis_coverage import expected_duration_seconds
    from app.services.gemini_service import gemini_service

    try:
        result = await asyncio.to_thread(
            gemini_service.analyze_video_direct,
            storage_path,
            file_id=file_id,
            file_size=file_size,
            expected_duration_seconds=expected_duration_seconds(
                file_size or 0, duration_seconds
            ),
        )
    except ContentBlockedError as exc:
        # Whole file refused by every model — still deliver an openable report
        # flagged for manual review instead of a hard error.
        logger.warning(
            "Direct Gemini blocked entire file %s; delivering manual-review report",
            file_id,
        )
        result = build_full_review_result(
            None, int(duration_seconds or 0), reason=str(exc)
        )
    except Exception as exc:
        logger.exception("Direct Gemini failed for file %s", file_id)
        await _fail_direct_gemini_fresh(file_id, f"Direct Gemini: {exc}")
        return

    async with async_session_factory() as s:
        await _persist_result(file_id, running_marker, result, s, save_result=save_result)
        await s.commit()


async def _run_direct_segment(
    file_id: str,
    running_marker: str,
    metadata: dict,
    *,
    save_result,
) -> None:
    from app.services.analysis_jobs import get_job_metadata, set_job_metadata
    from app.services.segmented_analysis import merge_segment_results

    ranges = metadata.get("ranges") or []
    total = len(ranges)
    idx = int(metadata.get("current_index") or 0)
    if idx >= total:
        await _fail_direct_gemini_fresh(file_id, "Segment index out of range")
        return

    range_row = ranges[idx]
    source_path = metadata.get("source_path") or ""

    blocked = False
    block_reason = ""
    try:
        result = await asyncio.to_thread(
            run_direct_segment_sync,
            source_path,
            int(range_row["start_sec"]),
            int(range_row["duration_sec"]),
            file_id=file_id,
            index=idx,
            total=total,
            extra_prompt_suffix=metadata.get("extra_prompt_suffix", ""),
        )
    except ContentBlockedError as exc:
        # One segment refused by every model — skip it (deliver the rest) and
        # flag the range for manual review instead of failing the whole file.
        blocked = True
        block_reason = str(exc)
        result = GeminiAnalysisResult()
        logger.warning(
            "Direct Gemini segment %d/%d blocked for %s; delivering partial",
            idx + 1,
            total,
            file_id,
        )
    except Exception as exc:
        logger.exception(
            "Direct Gemini segment %d/%d failed for file %s", idx + 1, total, file_id
        )
        await _fail_direct_gemini_fresh(
            file_id, f"Direct Gemini segment {idx + 1}/{total}: {exc}"
        )
        return

    # Re-lock in a fresh session and record the partial; advance or merge+save.
    async with async_session_factory() as s:
        row = await s.execute(
            select(VideoFile)
            .where(VideoFile.id == file_id)
            .with_for_update(skip_locked=True)
        )
        locked = row.scalar_one_or_none()
        if not locked or locked.status != "analyzing":
            return
        if locked.replicate_prediction_id != running_marker:
            return

        meta = await get_job_metadata(s, file_id) or metadata
        partial = list(meta.get("partial_results") or [])
        partial.append(result.model_dump())
        meta["partial_results"] = partial
        if blocked:
            blocked_ranges = list(meta.get("blocked_ranges") or [])
            blocked_ranges.append(
                {
                    "start_sec": int(range_row["start_sec"]),
                    "duration_sec": int(range_row["duration_sec"]),
                    "reason": block_reason,
                }
            )
            meta["blocked_ranges"] = blocked_ranges

        if idx + 1 < total:
            meta["current_index"] = idx + 1
            await set_job_metadata(s, file_id, meta)
            locked.replicate_prediction_id = DIRECT_PREDICTION_PENDING
            locked.progress = min(94, 30 + int(((idx + 1) / total) * 60))
            await s.flush()
            await s.commit()
            logger.info(
                "Direct Gemini: file %s segment %d/%d done, next part queued",
                file_id,
                idx + 1,
                total,
            )
            return

        logger.info(
            "Direct Gemini: file %s all %d segments done, merging", file_id, total
        )
        merged = merge_segment_results(
            partial,
            ranges,
            int(meta.get("total_duration_sec") or 0),
            locked.name,
        )
        _append_review_scenes(merged, meta.get("blocked_ranges"))
        meta.pop(DIRECT_SEGMENTED_KEY, None)
        await set_job_metadata(s, file_id, meta)
        await _persist_result(file_id, running_marker, merged, s, save_result=save_result)
        await s.commit()


def _append_review_scenes(
    merged: GeminiAnalysisResult, blocked_ranges: list | None
) -> None:
    """Append a manual-review finding for each segment the model refused."""
    if not blocked_ranges:
        return
    next_num = max((s.scene_number for s in merged.scenes), default=0) + 1
    for br in blocked_ranges:
        merged.scenes.append(
            build_review_scene(
                next_num,
                int(br.get("start_sec") or 0),
                int(br.get("duration_sec") or 0),
                reason=br.get("reason"),
            )
        )
        next_num += 1


async def _fail_direct_gemini_fresh(file_id: str, message: str) -> None:
    async with async_session_factory() as s:
        await _fail_direct_gemini(file_id, s, message)
        await s.commit()


async def _reset_direct_to_pending(
    file_id: str, db: AsyncSession, *, reason: str
) -> None:
    row = await db.execute(
        select(VideoFile)
        .where(VideoFile.id == file_id)
        .with_for_update(skip_locked=True)
    )
    locked = row.scalar_one_or_none()
    if not locked or locked.status != "analyzing":
        return
    logger.warning("Resetting direct Gemini for %s to pending (%s)", file_id, reason)
    locked.replicate_prediction_id = DIRECT_PREDICTION_PENDING
    await db.flush()


async def _fail_direct_gemini(
    file_id: str,
    db: AsyncSession,
    message: str,
) -> None:
    row = await db.execute(
        select(VideoFile)
        .where(VideoFile.id == file_id)
        .with_for_update(skip_locked=True)
    )
    locked = row.scalar_one_or_none()
    if not locked or locked.status != "analyzing":
        return

    from app.services.analysis_jobs import (
        is_transient_analysis_error,
        mark_job_failed,
        requeue_transient_failure,
    )

    if is_transient_analysis_error(message):
        # A disk-space wait (pre-flight guard or ffmpeg errno 28) is pure
        # capacity pressure from concurrent jobs, not a problem with this file,
        # so it must not burn the retry budget — it clears once others finish.
        msg_lower = message.lower()
        disk_wait = any(
            m in msg_lower
            for m in (
                "insufficient_tmp_space",
                "no space left",
                "errno 28",
                "недостаточно места",
            )
        )
        if await requeue_transient_failure(
            db, file_id, message, count_attempt=not disk_wait
        ):
            logger.warning(
                "Direct Gemini transient failure for %s, auto-retrying: %s",
                file_id,
                message[:200],
            )
            locked.replicate_prediction_id = DIRECT_PREDICTION_PENDING
            locked.progress = max(locked.progress or 0, 30)
            await db.flush()
            return

    logger.error("Direct Gemini fallback failed for %s: %s", file_id, message[:300])
    locked.status = "error"
    locked.replicate_prediction_id = None
    await db.flush()
    await mark_job_failed(db, file_id, message)


async def maybe_finish_analysis(
    video: VideoFile,
    db: AsyncSession,
    *,
    save_result,
) -> None:
    """Poll Replicate once, then persist under a short row lock.

    ``save_result(video, db, gemini_result)`` must set status=analyzed and
  analysis_id on success (see files._save_analysis_result).
    """
    if video.status != "analyzing" or not video.replicate_prediction_id:
        return
    if is_direct_prediction_id(video.replicate_prediction_id):
        return

    prediction_id = video.replicate_prediction_id
    file_id = video.id

    # Do not hold FOR UPDATE or a Neon connection during the Replicate HTTP call.
    try:
        _status, result = await asyncio.to_thread(poll_prediction, prediction_id)
    except Exception as exc:
        await _handle_poll_error(video, db, file_id, exc)
        return

    if result is None:
        await _bump_progress(file_id, db)
        return

    await _persist_result(file_id, prediction_id, result, db, save_result=save_result)


async def _bump_progress(file_id: str, db: AsyncSession) -> None:
    row = await db.execute(
        select(VideoFile)
        .where(VideoFile.id == file_id)
        .with_for_update(skip_locked=True)
    )
    video = row.scalar_one_or_none()
    if not video or video.status != "analyzing" or video.analysis_id:
        return
    video.progress = min(98, (video.progress or 0) + 2)
    await db.flush()


async def _persist_result(
    file_id: str,
    prediction_id: str,
    result: GeminiAnalysisResult,
    db: AsyncSession,
    *,
    save_result,
) -> None:
    row = await db.execute(
        select(VideoFile)
        .where(VideoFile.id == file_id)
        .with_for_update(skip_locked=True)
    )
    video = row.scalar_one_or_none()
    if video is None:
        return

    if video.status != "analyzing":
        return
    if video.replicate_prediction_id != prediction_id:
        return

    if video.analysis_id:
        video.replicate_prediction_id = None
        video.status = "analyzed"
        video.progress = 100
        await db.flush()
        return

    try:
        from app.services.segmented_analysis import advance_after_segment

        if await advance_after_segment(
            video, db, result, save_merged=save_result
        ):
            return
        saved = await save_result(video, db, result)
        if saved is None:
            return
        video.replicate_prediction_id = None
    except Exception:
        logger.exception("Failed to save analysis for file %s; will retry on next poll", file_id)
        await db.rollback()
        # Leave status=analyzing and prediction_id so the next poll can re-fetch output.


async def _handle_poll_error(
    video: VideoFile,
    db: AsyncSession,
    file_id: str,
    exc: Exception,
) -> None:
    err = str(exc).lower()
    if (
        ("interrupted" in err or "code: pa" in err)
        and video.storage_path
        and (video.progress or 0) < 90
    ):
        path_ok = video.storage_path.startswith(("http://", "https://")) or Path(
            video.storage_path
        ).exists()
        if path_ok:
            row = await db.execute(
                select(VideoFile)
                .where(VideoFile.id == file_id)
                .with_for_update(skip_locked=True)
            )
            locked = row.scalar_one_or_none()
            if locked and locked.status == "analyzing":
                try:
                    from app.services.analysis_coverage import expected_duration_seconds

                    from app.services.video_analysis_provider import start_analysis

                    new_id = await asyncio.to_thread(
                        start_analysis,
                        locked.storage_path,
                        file_id=locked.id,
                        file_size=locked.size,
                        expected_duration_seconds=expected_duration_seconds(
                            locked.size or 0, locked.duration_seconds
                        ),
                    )
                    locked.replicate_prediction_id = new_id
                    locked.progress = min((locked.progress or 0) + 10, 85)
                    await db.flush()
                    return
                except Exception:
                    logger.exception("Retry failed for file %s", file_id)

    if should_use_direct_gemini_fallback(exc):
        scheduled = await schedule_direct_gemini_fallback(
            db,
            file_id,
            reason=str(exc),
        )
        if scheduled:
            return

    row = await db.execute(
        select(VideoFile)
        .where(VideoFile.id == file_id)
        .with_for_update(skip_locked=True)
    )
    locked = row.scalar_one_or_none()
    if not locked or locked.status != "analyzing":
        return

    from app.services.analysis_jobs import (
        is_transient_analysis_error,
        mark_job_failed,
        requeue_transient_failure,
    )

    if is_transient_analysis_error(exc) and await requeue_transient_failure(
        db, file_id, str(exc)
    ):
        logger.warning(
            "Replicate poll transient failure for %s, auto-retrying: %s",
            file_id,
            str(exc)[:200],
        )
        locked.replicate_prediction_id = None
        locked.progress = max(locked.progress or 0, 10)
        await db.flush()
        return

    logger.exception("Poll failed for file %s", file_id)
    locked.status = "error"
    locked.replicate_prediction_id = None
    await db.flush()
    await mark_job_failed(db, file_id, str(exc))
