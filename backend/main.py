import os
from pathlib import Path

from app.core.db_url import resolve_database_env

_BACKEND_ROOT = Path(__file__).resolve().parent

# On Vercel env vars come from the dashboard; never load a local .env there.
if not os.getenv("VERCEL"):
    from dotenv import load_dotenv

    load_dotenv(_BACKEND_ROOT / ".env")
    load_dotenv(_BACKEND_ROOT / ".env.secrets", override=True)

resolve_database_env()

os.environ.setdefault("VIDEO_PROVIDER", "replicate")

if os.getenv("VERCEL"):
    os.environ.setdefault("UPLOAD_DIR", "/tmp/uploads")
else:
    os.environ.setdefault("UPLOAD_DIR", str(_BACKEND_ROOT / "uploads"))
    if not os.getenv("DATABASE_URL", "").strip():
        db_path = (_BACKEND_ROOT / "censorai.db").resolve()
        os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
        os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{db_path}"

from app.main import app  # noqa: E402, F401
