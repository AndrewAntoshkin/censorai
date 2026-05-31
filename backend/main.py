import os

from app.core.db_url import resolve_database_env

resolve_database_env()

os.environ.setdefault("UPLOAD_DIR", "/tmp/uploads")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/censorai.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:////tmp/censorai.db")
os.environ.setdefault("VIDEO_PROVIDER", "replicate")

from app.main import app  # noqa: E402, F401
