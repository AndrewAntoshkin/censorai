from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Max size for inline (base64 data-URI) video sent to the model.
    # The Gemini-on-Replicate model reliably accepts inline videos; large files
    # should be analysed as shorter fragments.
    INLINE_VIDEO_MAX_MB: int = 40

    # Optional egress proxy (e.g. for the geo-restricted direct Google Gemini API).
    HTTPS_PROXY_URL: str = ""

    VIDEO_PROVIDER: str = "replicate"  # "replicate" | "gemini"


settings = Settings()
