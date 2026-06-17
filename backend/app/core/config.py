import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.db_url import resolve_database_env

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if not os.getenv("VERCEL"):
    load_dotenv(_BACKEND_ROOT / ".env")
    load_dotenv(_BACKEND_ROOT / ".env.secrets", override=True)

resolve_database_env()

if os.getenv("VERCEL"):
    os.environ.setdefault("UPLOAD_DIR", "/tmp/uploads")
    if not os.getenv("DATABASE_URL", "").strip():
        os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/censorai.db")
        os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:////tmp/censorai.db")


def _default_api_prefix() -> str:
    if os.getenv("API_PREFIX") is not None:
        return os.getenv("API_PREFIX", "")
    return "" if os.getenv("VERCEL") else "/api"


def _default_public_api_base() -> str:
    explicit = os.getenv("PUBLIC_API_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    vercel_url = os.getenv("VERCEL_URL", "").strip()
    if vercel_url:
        return f"https://{vercel_url}".rstrip("/")
    return "http://localhost:8000"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/censorai"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/censorai"

    REDIS_URL: str = "redis://localhost:6379/0"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "censorai"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # Stronger model tried automatically when GEMINI_MODEL refuses content
    # (block_reason). It is a different model, so it sometimes analyzes footage
    # that Flash blocks. Empty disables the fallback.
    GEMINI_PRO_MODEL: str = "gemini-2.5-pro"

    # "direct_gemini" (Google AI Studio, bypasses Replicate) or "replicate".
    # Replicate Gemini currently fails uploads with E001, so direct is the default.
    ANALYSIS_PRIMARY_PROVIDER: str = "direct_gemini"
    # Direct Gemini runs one segment per serverless invocation (≤300s on Vercel).
    # Long videos are cut into chunks of this size so each generate_content call
    # stays under the time limit and produces a JSON small enough to not truncate.
    GEMINI_DIRECT_SEGMENT_SECONDS: int = 600
    # Also cap each direct segment by SIZE, not just duration: a short but
    # high-bitrate file (e.g. 295 MB / 4 min) is split so each chunk's upload to
    # Gemini fits one serverless invocation and /tmp (~512 MB on Vercel).
    GEMINI_DIRECT_MAX_SEGMENT_MB: int = 150

    REPLICATE_API_TOKEN: str = ""
    REPLICATE_MODEL: str = "google/gemini-3.5-flash"
    BLOB_READ_WRITE_TOKEN: str = ""

    UPLOAD_MAX_SIZE_MB: int = 500
    UPLOAD_DIR: str = "./uploads"

    # Each direct analysis buffers a full video to /tmp (~512 MB on Vercel) and
    # into RAM, so concurrent runs on one warm instance overflow disk/memory.
    # Keep this at 1 on serverless; raise only on a dedicated worker with disk.
    GEMINI_MAX_CONCURRENT: int = 1

    # Files larger than this use Blob URL or signed /replicate-media (not base64 inline).
    INLINE_VIDEO_MAX_MB: int = 4
    REPLICATE_MEDIA_TTL_SECONDS: int = 7200
    PUBLIC_API_BASE_URL: str = _default_public_api_base()
    # Gemini rejects ~45 min videos (E006); 40 min works, 45 fails. 35 = safe margin.
    REPLICATE_MAX_VIDEO_MINUTES: int = 35

    REPLICATE_VIDEO_FPS: float = 1
    # Always use 65535 in code (see analysis_coverage.FULL_ANALYSIS_MAX_OUTPUT_TOKENS).
    REPLICATE_MAX_OUTPUT_TOKENS: int = 65535
    ANALYSIS_MAX_COVERAGE_RETRIES: int = 2
    REPLICATE_THINKING_LEVEL: str = "none"

    # On Vercel, drop Blob objects after analysis to stay within storage quota.
    DELETE_BLOB_AFTER_ANALYSIS: bool = True

    HTTPS_PROXY_URL: str = ""

    # Production analysis always uses Replicate; other values are ignored with a warning.
    VIDEO_PROVIDER: str = "replicate"

    API_PREFIX: str = _default_api_prefix()

    # When true, API requires a signed-in user; projects/files are scoped per owner.
    AUTH_REQUIRED: bool = False
    # Used to sign session identifiers (set a long random string in production).
    AUTH_SECRET: str = "dev-change-me-in-production"

    SUPER_ADMIN_EMAIL: str = "andrew.antoshkin@gmail.com"
    FRAMECHECK_ORG_NAME: str = "Фреймчек"
    # Invite code for the Framecheck org (created on DB init if missing).
    FRAMECHECK_REGISTRATION_CODE: str = "FRAMECHECK2026"

    # Background worker (arq) polls all analyzing videos — not only on frontend GET.
    ANALYSIS_WORKER_POLL_SECONDS: int = 30
    # Dev-only manual poll (GET /api/worker/poll-once). Set in local .env; leave empty on Vercel.
    WORKER_DEV_POLL_SECRET: str = ""
    # When Redis is down locally, API process polls analyzing videos in the background.
    DEV_ANALYSIS_POLL_ENABLED: bool = True
    # Higher cap so transient retries (disk/network/model pressure) have room to
    # self-heal across worker ticks before a file is shown as a real error.
    ANALYSIS_JOB_MAX_ATTEMPTS: int = 10
    ANALYSIS_STALE_JOB_HOURS: int = 6
    # ffmpeg scene-change hints appended to the model prompt (stage 4 pre-pass).
    ANALYSIS_CASCADE_ENABLED: bool = False

    # S3-compatible object storage (MinIO, R2, AWS). When set, uploads go to S3.
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = "auto"
    S3_PRESIGN_TTL_SECONDS: int = 7200

    def route_prefix(self, path: str) -> str:
        segment = path if path.startswith("/") else f"/{path}"
        if not self.API_PREFIX:
            return segment
        return f"{self.API_PREFIX.rstrip('/')}{segment}"

    @property
    def public_api_base_url(self) -> str:
        return self.PUBLIC_API_BASE_URL.rstrip("/")

    @property
    def analysis_ready(self) -> bool:
        return bool(self.REPLICATE_API_TOKEN.strip())


settings = Settings()
