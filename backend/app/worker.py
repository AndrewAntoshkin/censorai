"""arq worker: background analysis polling (stage 2 orchestration)."""

from __future__ import annotations

import logging

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.services.analysis_orchestration import run_analysis_poll_cycle

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    logger.info("Analysis worker starting (poll every %ss)", settings.ANALYSIS_WORKER_POLL_SECONDS)


async def shutdown(ctx: dict) -> None:
    logger.info("Analysis worker stopped")


async def poll_analyses(ctx: dict) -> dict:
    stats = await run_analysis_poll_cycle()
    if stats["pending"]:
        logger.info(
            "Poll tick: processed=%d errors=%d pending=%d",
            stats["processed"],
            stats["errors"],
            stats["pending"],
        )
    return stats


def _cron_seconds(interval: int) -> set[int]:
    if interval <= 0:
        interval = 30
    if interval >= 60:
        return {0}
    return set(range(0, 60, interval))


class WorkerSettings:
    """Run: arq app.worker.WorkerSettings"""

    functions = [poll_analyses]
    cron_jobs = [
        cron(
            poll_analyses,
            second=_cron_seconds(settings.ANALYSIS_WORKER_POLL_SECONDS),
            run_at_startup=True,
        )
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 2
    job_timeout = 600
