#!/usr/bin/env python3
"""One-off prod DB query (run via: vercel env run --environment production -- python scripts/prod_db_query.py)."""
import os
import sys

import psycopg2

url = (
    os.environ.get("POSTGRES_URL_NON_POOLING")
    or os.environ.get("POSTGRES_URL")
    or os.environ.get("POSTGRES_DATABASE_URL_UNPOOLED")
    or os.environ.get("POSTGRES_DATABASE_URL")
)
if not url:
    host = os.environ.get("POSTGRES_PGHOST_UNPOOLED") or os.environ.get("POSTGRES_PGHOST") or os.environ.get("POSTGRES_HOST")
    user = os.environ.get("POSTGRES_PGUSER") or os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD")
    database = os.environ.get("POSTGRES_PGDATABASE") or os.environ.get("POSTGRES_DATABASE")
    if host and user and password and database:
        url = f"postgresql://{user}:{password}@{host}/{database}?sslmode=require"
if not url:
    print("No POSTGRES URL in env", file=sys.stderr)
    for k in sorted(os.environ):
        if "POSTGRES" in k or "DATABASE" in k:
            v = os.environ.get(k, "")
            print(f"  {k}: len={len(v)}", file=sys.stderr)
    sys.exit(1)

conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute(
    """
SELECT vf.id, vf.name, vf.status, vf.progress, vf.size, vf.duration_seconds,
       vf.updated_at, vf.created_at, aj.last_error, aj.attempts, aj.status AS job_status,
       vf.project_id, vf.storage_path, vf.replicate_prediction_id
FROM video_files vf
LEFT JOIN analysis_jobs aj ON aj.video_file_id = vf.id
WHERE vf.id = %s OR vf.name ILIKE %s OR vf.name ILIKE %s
ORDER BY vf.updated_at DESC
LIMIT 20
""",
    ("ec820dff-3d25-4c53-a74b-8b080c272476", "%Кухня%", "%get.gt%"),
)
rows = cur.fetchall()
print("matches", len(rows))
for r in rows:
    print("---")
    cols = [
        "id",
        "name",
        "status",
        "progress",
        "size",
        "duration",
        "updated",
        "created",
        "last_error",
        "attempts",
        "job_status",
        "project",
        "storage",
        "pred",
    ]
    for c, v in zip(cols, r):
        if c == "last_error" and v:
            print(f"{c}: {v}")
        elif c in ("storage", "pred") and v:
            print(f"{c}: {str(v)[:180]}")
        else:
            print(f"{c}: {v}")

cur.execute(
    """
SELECT vf.id, vf.name, vf.status, vf.updated_at, aj.last_error, vf.size, vf.duration_seconds
FROM video_files vf
LEFT JOIN analysis_jobs aj ON aj.video_file_id = vf.id
WHERE vf.status = %s
ORDER BY vf.updated_at DESC LIMIT 15
""",
    ("error",),
)
print("=== recent errors ===")
for r in cur.fetchall():
    print("---", r[0], "|", r[1])
    print("updated", r[3], "size", r[5], "dur", r[6])
    print("last_error:", (r[4] or "")[:2000])
conn.close()
