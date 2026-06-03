"""In-process analysis poll when Redis/worker is unavailable (local dev only)."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.services.analysis_orchestration import run_analysis_poll_cycle

logger = logging.getLogger(__name__)

_poll_task: asyncio.Task | None = None


async def redis_available() -> bool:
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1.0)
        try:
            return bool(await client.ping())
        finally:
            await client.aclose()
    except Exception:
        return False


async def _poll_loop() -> None:
    interval = max(5, settings.ANALYSIS_WORKER_POLL_SECONDS)
    logger.info("Dev in-process analysis poll every %ss (no Redis worker)", interval)
    while True:
        try:
            stats = await run_analysis_poll_cycle()
            if any(stats.get(k) for k in ("processed", "recovered", "queued_started", "pending")):
                logger.info("Dev poll tick: %s", stats)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Dev analysis poll failed")
        await asyncio.sleep(interval)


async def start_dev_poll_if_needed() -> asyncio.Task | None:
    global _poll_task
    if not settings.DEV_ANALYSIS_POLL_ENABLED:
        return None
    if await redis_available():
        logger.info("Redis available — using arq worker for analysis poll")
        return None
    if _poll_task is not None and not _poll_task.done():
        return _poll_task
    _poll_task = asyncio.create_task(_poll_loop(), name="dev-analysis-poll")
    return _poll_task


async def stop_dev_poll() -> None:
    global _poll_task
    if _poll_task is None:
        return
    _poll_task.cancel()
    try:
        await _poll_task
    except asyncio.CancelledError:
        pass
    _poll_task = None
