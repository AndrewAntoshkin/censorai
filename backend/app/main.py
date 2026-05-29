import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.books import router as books_router
from app.api.files import router as files_router
from app.api.projects import router as projects_router
from app.core.database import Base, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _migrate_sqlite_columns() -> None:
    import sqlalchemy as sa
    from app.core.config import settings

    if "sqlite" not in settings.DATABASE_URL_SYNC:
        return
    sync_engine = sa.create_engine(settings.DATABASE_URL_SYNC)
    with sync_engine.begin() as conn:
        cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(video_files)"))}
        if "replicate_prediction_id" not in cols:
            conn.execute(
                sa.text(
                    "ALTER TABLE video_files ADD COLUMN replicate_prediction_id VARCHAR(128)"
                )
            )
            logger.info("Added video_files.replicate_prediction_id column")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import app.models  # noqa: F401 — ensure all models are registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _migrate_sqlite_columns()
    logger.info("Database tables created")

    yield

    await engine.dispose()


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


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "framecheck"}
