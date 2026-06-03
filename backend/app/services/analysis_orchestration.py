"""Background analysis polling — does not depend on frontend GET requests."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.db_init import ensure_database
from app.models.project import VideoFile

logger = logging.getLogger(__name__)

# Cap work per tick so a large backlog cannot block the worker for minutes.
MAX_FILES_PER_TICK = 50


async def run_analysis_poll_cycle() -> dict:
    """Poll Replicate and recover stuck analyses for all in-flight videos."""
    await ensure_database()

    processed = 0
    errors = 0

    async with async_session_factory() as db:
        result = await db.execute(
            select(VideoFile.id)
            .where(VideoFile.status == "analyzing")
            .order_by(VideoFile.updated_at.asc())
            .limit(MAX_FILES_PER_TICK)
        )
        file_ids = list(result.scalars().all())

        if not file_ids:
            return {"processed": 0, "errors": 0, "pending": 0}

        for file_id in file_ids:
            try:
                await _process_one(file_id, db)
                await db.commit()
                processed += 1
            except Exception:
                errors += 1
                await db.rollback()
                logger.exception("Worker failed for file %s", file_id)

    return {
        "processed": processed,
        "errors": errors,
        "pending": len(file_ids),
    }


async def _process_one(file_id: str, db: AsyncSession) -> None:
    from app.api.files import _maybe_finish_analysis

    row = await db.execute(select(VideoFile).where(VideoFile.id == file_id))
    video = row.scalar_one_or_none()
    if video is None or video.status != "analyzing":
        return
    await _maybe_finish_analysis(video, db)
