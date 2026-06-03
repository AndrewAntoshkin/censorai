"""Multi-segment Replicate analysis for videos longer than 45 minutes."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import VideoFile
from app.schemas.analysis import (
    GeminiAgeRatingTrigger,
    GeminiAnalysisResult,
    GeminiEntity,
    GeminiMarking,
    GeminiScene,
    GeminiSceneRisk,
)
from app.services.analysis_coverage import (
    estimate_duration_seconds,
    format_duration,
    parse_timecode_seconds,
)
from app.services.analysis_jobs import get_job_metadata, set_job_metadata
from app.services.blob_storage import blob_enabled, delete_urls, put_bytes
from app.services.video_segmentation import (
    needs_segmentation,
    plan_segment_ranges,
    prepare_single_segment_file,
    probe_duration_seconds,
    segment_prompt_suffix,
)

logger = logging.getLogger(__name__)

_AGE_ORDER = ("0+", "6+", "12+", "16+", "18+")


async def resolve_duration_seconds(video: VideoFile) -> int | None:
    if video.duration_seconds and video.duration_seconds > 30:
        return int(video.duration_seconds)
    if not video.storage_path:
        return None
    probed = await asyncio.to_thread(probe_duration_seconds, video.storage_path)
    return probed


async def prepare_segmented_job(
    video: VideoFile,
    db: AsyncSession,
    *,
    total_seconds: int,
    extra_prompt_suffix: str = "",
) -> dict:
    """Cut video, upload segment blobs, store plan in job_metadata."""
    ranges = plan_segment_ranges(total_seconds)
    storage_path = video.storage_path or ""
    segment_urls: list[str] = []

    # One segment in /tmp at a time — Vercel /tmp is ~512 MB.
    for index, (start_sec, duration_sec) in enumerate(ranges):
        def _cut_one() -> tuple[str, list[Path]]:
            return prepare_single_segment_file(
                storage_path,
                start_sec,
                duration_sec,
                index=index,
                file_id=video.id,
            )

        local_path, temps = await asyncio.to_thread(_cut_one)
        try:
            url = await _upload_segment(video.id, index, local_path)
            segment_urls.append(url)
            logger.info(
                "Long video %s: segment %d/%d uploaded (%s–%s)",
                video.id,
                index + 1,
                len(ranges),
                format_duration(start_sec),
                format_duration(start_sec + duration_sec),
            )
        finally:
            for path in temps:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass

    metadata = {
        "segmented": True,
        "total_duration_sec": total_seconds,
        "ranges": [
            {"start_sec": start, "duration_sec": dur} for start, dur in ranges
        ],
        "segment_urls": segment_urls,
        "current_index": 0,
        "partial_results": [],
        "extra_prompt_suffix": extra_prompt_suffix,
    }
    await set_job_metadata(db, video.id, metadata)
    parts = len(segment_urls)
    logger.info(
        "Long video %s: cut into %d segment(s) for Replicate (total %s)",
        video.id,
        parts,
        format_duration(total_seconds),
    )
    return metadata


async def _upload_segment(video_id: str, index: int, local_path: str) -> str:
    path = Path(local_path)
    data = path.read_bytes()

    if blob_enabled():
        blob_path = f"videos/{video_id}_seg{index}.mp4"

        def _put() -> str:
            result = put_bytes(blob_path, data, content_type="video/mp4")
            url = result.get("url")
            if not url:
                raise RuntimeError("Blob upload returned no URL")
            return url

        return await asyncio.to_thread(_put)

    if path.stat().st_size / (1024 * 1024) > 4:
        raise RuntimeError(
            "Для длинного ролика без Vercel Blob нельзя отправить части в Replicate. "
            "Добавьте BLOB_READ_WRITE_TOKEN."
        )
    return local_path


async def start_segment_prediction(
    video: VideoFile,
    db: AsyncSession,
    metadata: dict,
    index: int,
) -> str:
    from app.services.video_analysis_provider import start_analysis

    ranges = metadata["ranges"]
    urls = metadata["segment_urls"]
    total_parts = len(urls)
    range_row = ranges[index]
    start_sec = range_row["start_sec"]
    duration_sec = range_row["duration_sec"]
    extra = (metadata.get("extra_prompt_suffix") or "") + segment_prompt_suffix(
        index, total_parts, start_sec, duration_sec
    )

    prediction_id = await asyncio.to_thread(
        start_analysis,
        urls[index],
        file_id=video.id,
        file_size=None,
        expected_duration_seconds=duration_sec,
        extra_prompt_suffix=extra,
    )
    metadata["current_index"] = index
    await set_job_metadata(db, video.id, metadata)
    return prediction_id


async def advance_after_segment(
    video: VideoFile,
    db: AsyncSession,
    result: GeminiAnalysisResult,
    *,
    save_merged,
) -> bool:
    """Store segment result; start next segment or merge and save. Returns True when finished."""
    metadata = await get_job_metadata(db, video.id)
    if not metadata.get("segmented"):
        return False

    partial = list(metadata.get("partial_results") or [])
    partial.append(result.model_dump())
    metadata["partial_results"] = partial
    idx = int(metadata.get("current_index") or 0)
    urls = metadata.get("segment_urls") or []

    if idx + 1 < len(urls):
        metadata["current_index"] = idx + 1
        await set_job_metadata(db, video.id, metadata)
        total = len(urls)
        logger.info(
            "Long video %s: segment %d/%d done, starting part %d",
            video.id,
            idx + 1,
            total,
            idx + 2,
        )
        video.progress = min(94, 30 + int(((idx + 1) / total) * 55))
        video.replicate_prediction_id = await start_segment_prediction(
            video, db, metadata, idx + 1
        )
        await db.flush()
        return True

    logger.info(
        "Long video %s: all %d segments done, merging results",
        video.id,
        len(urls),
    )
    merged = merge_segment_results(
        partial,
        metadata.get("ranges") or [],
        int(metadata.get("total_duration_sec") or 0),
        video.name,
    )
    await _cleanup_segment_blobs(metadata)
    metadata.pop("segmented", None)
    await set_job_metadata(db, video.id, metadata)

    await save_merged(video, db, merged)
    return True


async def _cleanup_segment_blobs(metadata: dict) -> None:
    urls = metadata.get("segment_urls") or []
    await asyncio.to_thread(delete_urls, [u for u in urls if isinstance(u, str)])


def merge_segment_results(
    partial_dicts: list[dict],
    ranges: list[dict],
    total_seconds: int,
    video_name: str,
) -> GeminiAnalysisResult:
    partials = [GeminiAnalysisResult.model_validate(d) for d in partial_dicts]
    all_scenes: list[GeminiScene] = []
    scene_num = 1
    triggers: list[GeminiAgeRatingTrigger] = []
    entities: list[GeminiEntity] = []
    markings: list[GeminiMarking] = []
    best_rating: str | None = None
    best_reason: str | None = None

    for part_index, (result, range_row) in enumerate(zip(partials, ranges)):
        offset = int(range_row.get("start_sec") or 0)
        for scene in result.scenes:
            all_scenes.append(
                GeminiScene(
                    scene_number=scene_num,
                    start_time=_shift_timecode(scene.start_time, offset),
                    end_time=_shift_timecode(scene.end_time, offset),
                    description=scene.description,
                    risks=[GeminiSceneRisk.model_validate(r.model_dump()) for r in scene.risks],
                )
            )
            scene_num += 1

        for trigger in result.age_rating_triggers:
            triggers.append(
                GeminiAgeRatingTrigger(
                    scene_number=trigger.scene_number,
                    start_time=_shift_timecode(trigger.start_time, offset),
                    end_time=_shift_timecode(trigger.end_time, offset),
                    trigger=trigger.trigger,
                    reason=trigger.reason,
                )
            )

        for entity in result.entities:
            entities.append(entity.model_copy())

        for marking in result.markings_detected:
            markings.append(
                GeminiMarking(
                    type=marking.type,
                    text=marking.text,
                    scene_number=marking.scene_number,
                    start_time=_shift_timecode(marking.start_time, offset),
                )
            )

        rating = result.recommended_age_rating
        if not rating:
            continue
        if best_rating is None:
            best_rating = rating
            best_reason = result.age_rating_reason
            continue
        if rating in _AGE_ORDER and best_rating in _AGE_ORDER:
            if _AGE_ORDER.index(rating) > _AGE_ORDER.index(best_rating):
                best_rating = rating
                best_reason = result.age_rating_reason

    duration_label = format_duration(total_seconds) if total_seconds else None
    title = partials[0].video_title if partials and partials[0].video_title else video_name

    return GeminiAnalysisResult(
        video_title=title,
        duration=duration_label,
        total_scenes_reviewed=len(all_scenes),
        recommended_age_rating=best_rating,
        age_rating_reason=best_reason,
        age_rating_triggers=triggers,
        entities=entities,
        markings_detected=markings,
        scenes=all_scenes,
    )


def _shift_timecode(value: str | None, offset_sec: int) -> str | None:
    if not value:
        return value
    seconds = parse_timecode_seconds(value)
    if seconds is None:
        return value
    return format_duration(seconds + offset_sec)


async def should_segment(video: VideoFile) -> tuple[bool, int | None]:
    duration = await resolve_duration_seconds(video)
    if duration is None and video.size:
        estimated = estimate_duration_seconds(int(video.size))
        if estimated:
            duration = estimated
            logger.info(
                "Using estimated duration %s for file %s (no ffprobe)",
                format_duration(duration),
                video.id,
            )
    if duration is None:
        return False, None
    return needs_segmentation(duration), duration
