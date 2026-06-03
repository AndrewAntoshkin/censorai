#!/usr/bin/env python3
"""Sync Vercel production secrets into backend/.env.secrets (keeps backend/.env local)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
ENV_FILE = BACKEND / ".env"
SECRETS_FILE = BACKEND / ".env.secrets"
EXPORT_SCRIPT = ROOT / "scripts" / "_vercel_env_export.py"

MERGE_KEYS = frozenset(
    {
        "REPLICATE_API_TOKEN",
        "REPLICATE_MODEL",
        "BLOB_READ_WRITE_TOKEN",
        "GEMINI_API_KEY",
    }
)

LOCAL_DEFAULTS = {
    "DEV_ANALYSIS_POLL_ENABLED": "true",
    "WORKER_DEV_POLL_SECRET": "dev-poll-local",
    "VIDEO_PROVIDER": "replicate",
    "ANALYSIS_WORKER_POLL_SECONDS": "30",
    "REDIS_URL": "redis://localhost:6379/0",
}

# Stub without secret keys so `vercel env run` does not load empty overrides from .env
_STUB_LINES = [
    "# temporary stub for vercel env run",
    "DATABASE_URL=sqlite+aiosqlite:///./censorai.db",
]


def _vercel_cli_token() -> str | None:
    for path in (
        Path.home() / "Library/Application Support/com.vercel.cli/auth.json",
        Path.home() / ".local/share/com.vercel.cli/auth.json",
    ):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            token = (data.get("token") or "").strip()
            if token:
                return token
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _vercel_project_meta() -> tuple[str, str | None]:
    repo_json = ROOT / ".vercel/repo.json"
    if not repo_json.exists():
        return "censorai", None
    data = json.loads(repo_json.read_text(encoding="utf-8"))
    projects = data.get("projects") or []
    if not projects:
        return "censorai", None
    project = projects[0]
    return project.get("id") or project.get("name", "censorai"), project.get("orgId")


def fetch_vercel_api_secrets() -> dict[str, str]:
    token = _vercel_cli_token()
    if not token:
        return {}
    project_id, team_id = _vercel_project_meta()
    params: dict[str, str] = {
        "decrypt": "true",
        "target": "production",
        "source": "vercel-cli:pull",
    }
    if team_id:
        params["teamId"] = team_id
    url = f"https://api.vercel.com/v10/projects/{project_id}/env"
    response = httpx.get(
        url,
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60.0,
    )
    response.raise_for_status()
    secrets: dict[str, str] = {}
    for env in response.json().get("envs") or []:
        key = (env.get("key") or "").strip()
        value = (env.get("value") or "").strip()
        if key in MERGE_KEYS and value:
            secrets[key] = value
    return secrets


def fetch_vercel_cli_run_secrets() -> dict[str, str]:
    backup = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else None
    ENV_FILE.write_text("\n".join(_STUB_LINES) + "\n", encoding="utf-8")
    try:
        result = subprocess.run(
            [
                "npx",
                "--yes",
                "vercel@latest",
                "env",
                "run",
                "-e",
                "production",
                "--cwd",
                str(BACKEND),
                "--",
                sys.executable,
                str(EXPORT_SCRIPT),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        if backup is not None:
            ENV_FILE.write_text(backup, encoding="utf-8")

    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"vercel env run failed (code {result.returncode})")

    secrets: dict[str, str] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key in MERGE_KEYS and value:
            secrets[key] = value
    return secrets


def merge_secrets_file(secrets: dict[str, str]) -> None:
    lines: list[str] = []
    seen: set[str] = set()

    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in MERGE_KEYS:
                    if key in secrets:
                        lines.append(f"{key}={secrets[key]}")
                        print(f"  synced {key}")
                    seen.add(key)
                    continue
            lines.append(line)
            if stripped and "=" in stripped and not stripped.startswith("#"):
                seen.add(stripped.split("=", 1)[0].strip())

    if not lines:
        lines.append("# Secrets from Vercel production (gitignored). Do not commit.")

    for key, value in secrets.items():
        if key not in seen:
            lines.append(f"{key}={value}")
            print(f"  added {key}")
            seen.add(key)

    SECRETS_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def ensure_local_env_defaults() -> None:
    lines: list[str] = []
    seen: set[str] = set()
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                seen.add(key)
                if key in MERGE_KEYS:
                    continue
            lines.append(line)
    for key, value in LOCAL_DEFAULTS.items():
        if key not in seen:
            lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    print("Fetching secrets from Vercel API (production)…")
    secrets = fetch_vercel_api_secrets()
    if not secrets.get("REPLICATE_API_TOKEN"):
        print("Trying vercel env run fallback…")
        try:
            secrets = fetch_vercel_cli_run_secrets()
        except RuntimeError as exc:
            print(exc, file=sys.stderr)

    if not secrets.get("REPLICATE_API_TOKEN"):
        print(
            "WARN: REPLICATE_API_TOKEN not available from Vercel CLI.\n"
            "Add to backend/.env.secrets manually (same value as Vercel dashboard → Environment Variables).",
            file=sys.stderr,
        )
        ensure_local_env_defaults()
        return 1

    merge_secrets_file(secrets)
    ensure_local_env_defaults()
    print(f"Updated {SECRETS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
