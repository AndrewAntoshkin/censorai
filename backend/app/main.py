import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.books import router as books_router
from app.api.files import router as files_router
from app.api.projects import router as projects_router
from app.core.config import settings
from app.core.database import Base, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _migrate_columns() -> None:
    import sqlalchemy as sa
    from app.core.config import settings

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
            logger.info("Ensured video_files.replicate_prediction_id and scenes.mode columns")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    import app.models  # noqa: F401 — ensure all models are registered

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await asyncio.to_thread(_migrate_columns)
    except Exception:
        logger.exception("Database initialization failed")
        raise

    await asyncio.to_thread(_seed_demo_if_needed)

    from app.core.db_url import is_ephemeral_sqlite
    import os as _os

    if _os.getenv("VERCEL") and is_ephemeral_sqlite():
        logger.warning(
            "VERCEL without external Postgres: SQLite in /tmp is per-instance — "
            "uploads and analysis status will be lost across cold starts. "
            "Add Vercel Postgres or Neon and set POSTGRES_URL."
        )
    else:
        db_kind = "postgres" if "postgres" in settings.DATABASE_URL else "sqlite"
        logger.info("Database ready (%s)", db_kind)

    yield

    await engine.dispose()


def _seed_demo_if_needed() -> None:
    from app.services.seed_bundle import ensure_demo_seeded

    try:
        if ensure_demo_seeded():
            logger.info("Demo bundle loaded into empty database")
    except Exception:
        logger.exception("Failed to seed demo bundle")


app = FastAPI(
    title="фреймчек",
    description="Сервис анализа видеоконтента на соответствие требованиям",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(files_router)
app.include_router(books_router)


@app.get(settings.route_prefix("/health"))
async def health_check():
    import os

    from app.core.db_url import is_ephemeral_sqlite

    db = "postgres" if "postgres" in settings.DATABASE_URL else "sqlite"
    return {
        "status": "ok",
        "service": "framecheck",
        "database": db,
        "ephemeral_db": is_ephemeral_sqlite(),
        "env": {
            "has_database_url": bool(os.getenv("DATABASE_URL")),
            "has_postgres_url": bool(os.getenv("POSTGRES_URL")),
            "has_storage_url": bool(os.getenv("STORAGE_URL")),
        },
    }


@app.post(settings.route_prefix("/seed-demo"))
async def seed_demo():
    import asyncio

    from app.services.seed_bundle import ensure_demo_seeded

    seeded = await asyncio.to_thread(ensure_demo_seeded)
    return {"seeded": seeded}
