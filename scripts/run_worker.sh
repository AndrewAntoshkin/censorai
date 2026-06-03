#!/usr/bin/env bash
# Analysis background worker (arq + Redis). Run beside API, not on Vercel serverless.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if [[ ! -x .venv/bin/arq ]]; then
  echo "→ Installing backend deps (arq)…"
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

if ! redis-cli ping >/dev/null 2>&1; then
  echo "⚠️  Redis not reachable on localhost:6379. Start: docker compose up -d redis"
  exit 1
fi

echo "→ Starting analysis worker (poll interval from ANALYSIS_WORKER_POLL_SECONDS)"
exec .venv/bin/arq app.worker.WorkerSettings
