"""FastAPI entrypoint for Vercel Python runtime."""
import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(_backend))

os.environ.setdefault("UPLOAD_DIR", "/tmp/uploads")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/censorai.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:////tmp/censorai.db")
os.environ.setdefault("VIDEO_PROVIDER", "replicate")

from app.main import app  # noqa: E402
