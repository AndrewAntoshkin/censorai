#!/usr/bin/env python3
"""Prune Vercel Blob storage: keep only videos for completed analyses (status=analyzed)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import vercel_blob
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.db_url import resolve_database_env  # noqa: E402

DELETE_PREFIXES = ("chunks/", "selftest/")
BATCH_SIZE = 50


def _load_env_file(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _normalize_blob_url(url: str) -> str:
    parsed = urlparse(url.strip())
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _list_all_blobs() -> list[dict]:
    items: list[dict] = []
    cursor: str | None = None
    while True:
        options: dict = {"limit": 1000, "mode": "expanded"}
        if cursor:
            options["cursor"] = cursor
        page = vercel_blob.list(options, timeout=120)
        items.extend(page.get("blobs") or [])
        if not page.get("hasMore"):
            break
        cursor = page.get("cursor")
        if not cursor:
            break
    return items


def _fetch_keep_urls(engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT storage_path FROM video_files
                WHERE status = 'analyzed'
                  AND storage_path IS NOT NULL
                  AND storage_path LIKE 'http%'
                """
            )
        ).fetchall()
        part_rows = conn.execute(
            text("SELECT part_urls_json FROM upload_chunk_sessions")
        ).fetchall()

    keep = {_normalize_blob_url(r[0]) for r in rows if r[0]}
    return keep


def _clear_chunk_sessions(engine, *, apply: bool) -> int:
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM upload_chunk_sessions")).scalar() or 0
        if apply and count:
            conn.execute(text("DELETE FROM upload_chunk_sessions"))
            conn.commit()
    return int(count)


def run(*, env_file: Path | None, dry_run: bool) -> int:
    if env_file and env_file.is_file():
        _load_env_file(env_file)

    if not os.getenv("BLOB_READ_WRITE_TOKEN", "").strip():
        print("BLOB_READ_WRITE_TOKEN is required", file=sys.stderr)
        return 1

    resolve_database_env()
    sync_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL", "")
    if not sync_url or "sqlite" in sync_url:
        print("Postgres DATABASE_URL required", file=sys.stderr)
        return 1

    engine = create_engine(sync_url, connect_args={"sslmode": "require"} if "postgres" in sync_url else {})
    keep_urls = _fetch_keep_urls(engine)
    blobs = _list_all_blobs()

    to_delete: list[str] = []
    kept = 0
    for blob in blobs:
        url = blob.get("url") or ""
        pathname = blob.get("pathname") or ""
        if not url:
            continue
        norm = _normalize_blob_url(url)
        if any(pathname.startswith(p) for p in DELETE_PREFIXES):
            to_delete.append(url)
            continue
        if norm in keep_urls:
            kept += 1
            continue
        to_delete.append(url)

    total_bytes = sum(b.get("size") or 0 for b in blobs)
    delete_bytes = sum(
        b.get("size") or 0 for b in blobs if (b.get("url") or "") in to_delete
    )
    chunk_sessions = _clear_chunk_sessions(engine, apply=not dry_run)

    print(f"blobs_total={len(blobs)} ({total_bytes / (1024**3):.2f} GB)")
    print(f"keep_analyzed={kept} urls={len(keep_urls)}")
    print(f"delete_candidates={len(to_delete)} ({delete_bytes / (1024**3):.2f} GB)")
    print(f"upload_chunk_sessions_cleared={chunk_sessions}")

    if dry_run:
        print("dry-run: no blobs deleted")
        return 0

    deleted = 0
    for i in range(0, len(to_delete), BATCH_SIZE):
        batch = to_delete[i : i + BATCH_SIZE]
        vercel_blob.delete(batch, timeout=120)
        deleted += len(batch)
        print(f"  deleted {deleted}/{len(to_delete)}", flush=True)

    probe = vercel_blob.put(
        "selftest/probe-after-cleanup.txt",
        b"ok",
        {"addRandomSuffix": "true", "allowOverwrite": "true"},
    )
    print(f"post-cleanup probe ok url={probe.get('url', '?')[:80]}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path("/tmp/censorai-prod.env"),
        help="Vercel env file (default: /tmp/censorai-prod.env)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(env_file=args.env_file, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
