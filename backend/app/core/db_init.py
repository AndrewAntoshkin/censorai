"""Lazy database initialization for Vercel serverless cold starts."""

import asyncio
import logging
import threading

from app.core.config import settings
from app.core.database import Base

logger = logging.getLogger(__name__)

_init_lock = threading.Lock()
_initialized = False
_init_error: str | None = None


def _migrate_columns() -> None:
    import sqlalchemy as sa

    sync_connect_args: dict = {}
    if "postgres" in settings.DATABASE_URL_SYNC:
        sync_connect_args = {"sslmode": "require"}

    sync_engine = sa.create_engine(
        settings.DATABASE_URL_SYNC,
        connect_args=sync_connect_args,
    )
    is_sqlite = "sqlite" in settings.DATABASE_URL_SYNC

    with sync_engine.begin() as conn:
        if is_sqlite:
            video_cols = {
                row[1] for row in conn.execute(sa.text("PRAGMA table_info(video_files)"))
            }
            if "replicate_prediction_id" not in video_cols:
                conn.execute(
                    sa.text(
                        "ALTER TABLE video_files ADD COLUMN replicate_prediction_id VARCHAR(128)"
                    )
                )
                logger.info("Added video_files.replicate_prediction_id column")

            scene_cols = {
                row[1] for row in conn.execute(sa.text("PRAGMA table_info(scenes)"))
            }
            if "mode" not in scene_cols:
                conn.execute(sa.text("ALTER TABLE scenes ADD COLUMN mode VARCHAR(50)"))
                logger.info("Added scenes.mode column")
            if "duration_seconds" not in video_cols:
                conn.execute(sa.text("ALTER TABLE video_files ADD COLUMN duration_seconds REAL"))
                logger.info("Added video_files.duration_seconds column")
            if "analysis_attempts" not in video_cols:
                conn.execute(
                    sa.text(
                        "ALTER TABLE video_files ADD COLUMN analysis_attempts "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
                logger.info("Added video_files.analysis_attempts column")
        else:
            conn.execute(
                sa.text(
                    "ALTER TABLE video_files ADD COLUMN IF NOT EXISTS "
                    "replicate_prediction_id VARCHAR(128)"
                )
            )
            conn.execute(
                sa.text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS mode VARCHAR(50)")
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE video_files ADD COLUMN IF NOT EXISTS "
                    "duration_seconds DOUBLE PRECISION"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE video_files ADD COLUMN IF NOT EXISTS "
                    "analysis_attempts INTEGER NOT NULL DEFAULT 0"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE upload_chunk_sessions ADD COLUMN IF NOT EXISTS "
                    "duration_seconds DOUBLE PRECISION"
                )
            )
            logger.info(
                "Ensured video_files.replicate_prediction_id, duration_seconds, "
                "analysis_attempts and scenes.mode columns"
            )


def _init_sync() -> None:
    global _initialized, _init_error

    with _init_lock:
        if _initialized:
            return
        if _init_error:
            raise RuntimeError(_init_error)

        try:
            import app.models  # noqa: F401
            import sqlalchemy as sa

            sync_connect_args: dict = {}
            if "sqlite" in settings.DATABASE_URL_SYNC:
                sync_connect_args = {"check_same_thread": False}

            sync_engine = sa.create_engine(
                settings.DATABASE_URL_SYNC,
                connect_args=sync_connect_args,
            )
            Base.metadata.create_all(sync_engine)
            sync_engine.dispose()

            _migrate_columns()

            from app.services.seed_bundle import ensure_demo_seeded

            ensure_demo_seeded()
            _initialized = True
            db_kind = "postgres" if "postgres" in settings.DATABASE_URL else "sqlite"
            logger.info("Database initialized (%s)", db_kind)
        except Exception as exc:
            _init_error = str(exc)
            logger.exception("Database initialization failed")
            raise


async def ensure_database() -> None:
    await asyncio.to_thread(_init_sync)


def database_status() -> dict:
    return {
        "initialized": _initialized,
        "error": _init_error,
        "url_scheme": settings.DATABASE_URL.split("://", 1)[0],
    }
