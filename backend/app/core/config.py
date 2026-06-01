import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.db_url import resolve_database_env

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
    GEMINI_MODEL: str = "gemini-2.5-pro-preview-05-06"

    REPLICATE_API_TOKEN: str = ""
    REPLICATE_MODEL: str = "google/gemini-3.5-flash"

    UPLOAD_MAX_SIZE_MB: int = 500
    UPLOAD_DIR: str = "./uploads"

    GEMINI_MAX_CONCURRENT: int = 3

    # Files larger than this use Blob URL or signed /replicate-media (not base64 inline).
    INLINE_VIDEO_MAX_MB: int = 4
    REPLICATE_MEDIA_TTL_SECONDS: int = 7200
    PUBLIC_API_BASE_URL: str = _default_public_api_base()
    REPLICATE_MAX_VIDEO_MINUTES: int = 45

    REPLICATE_VIDEO_FPS: float = 1
    # Always use 65535 in code (see analysis_coverage.FULL_ANALYSIS_MAX_OUTPUT_TOKENS).
    REPLICATE_MAX_OUTPUT_TOKENS: int = 65535
    ANALYSIS_MAX_COVERAGE_RETRIES: int = 2
    REPLICATE_THINKING_LEVEL: str = "none"

    HTTPS_PROXY_URL: str = ""

    VIDEO_PROVIDER: str = "replicate"  # "replicate" | "gemini"

    API_PREFIX: str = _default_api_prefix()

    def route_prefix(self, path: str) -> str:
        segment = path if path.startswith("/") else f"/{path}"
        if not self.API_PREFIX:
            return segment
        return f"{self.API_PREFIX.rstrip('/')}{segment}"

    @property
    def public_api_base_url(self) -> str:
        return self.PUBLIC_API_BASE_URL.rstrip("/")


settings = Settings()
