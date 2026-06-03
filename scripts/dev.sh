#!/usr/bin/env bash
# Запуск backend + frontend (из корня репозитория).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x backend/.venv/bin/uvicorn ]]; then
  echo "→ Создаём venv и ставим зависимости backend…"
  (cd backend && python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt)
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "→ npm install frontend…"
  npm install --prefix frontend
fi

cleanup() {
  trap - EXIT INT TERM
  kill "$BACK_PID" "$FRONT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "→ Backend http://127.0.0.1:8000"
(cd backend && .venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000) &
BACK_PID=$!

echo "→ Frontend http://localhost:3005"
npm run dev --prefix frontend &
FRONT_PID=$!

wait
