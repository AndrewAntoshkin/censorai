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


@asynccontextmanager
async def lifespan(app: FastAPI):
    import app.models  # noqa: F401 — ensure all models are registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "framecheck"}
