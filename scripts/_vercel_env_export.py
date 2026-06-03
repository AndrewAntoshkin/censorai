"""Print selected env vars (run via: vercel env run -e production -- python scripts/_vercel_env_export.py)."""

import os
import sys

KEYS = (
    "REPLICATE_API_TOKEN",
    "REPLICATE_MODEL",
    "BLOB_READ_WRITE_TOKEN",
    "GEMINI_API_KEY",
)

for key in KEYS:
    value = os.environ.get(key, "").strip()
    if value:
        # Avoid multiline breakage in .env
        safe = value.replace("\n", "")
        sys.stdout.write(f"{key}={safe}\n")
