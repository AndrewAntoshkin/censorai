#!/usr/bin/env bash
# Local secrets: Vercel "Sensitive" vars cannot be copied from the dashboard menu.
# Paste tokens into backend/.env.secrets (clipboard helpers below).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS="$ROOT/backend/.env.secrets"
EXAMPLE="$ROOT/backend/.env.secrets.example"

has_replicate() {
  [[ -f "$SECRETS" ]] && grep -qE '^REPLICATE_API_TOKEN=r8_' "$SECRETS" 2>/dev/null
}

has_blob() {
  [[ -f "$SECRETS" ]] && grep -qE '^BLOB_READ_WRITE_TOKEN=vercel_blob_rw_' "$SECRETS" 2>/dev/null
}

if has_replicate && has_blob; then
  echo "backend/.env.secrets already has REPLICATE_API_TOKEN and BLOB_READ_WRITE_TOKEN"
  exit 0
fi

if [[ ! -f "$SECRETS" ]]; then
  cp "$EXAMPLE" "$SECRETS"
  echo "Created $SECRETS from example."
fi

set_kv() {
  local key="$1" value="$2"
  if grep -q "^${key}=" "$SECRETS" 2>/dev/null; then
    sed -i '' "s|^${key}=.*|${key}=${value}|" "$SECRETS"
  else
    echo "${key}=${value}" >> "$SECRETS"
  fi
}

if command -v pbpaste >/dev/null 2>&1; then
  CLIP="$(pbpaste | tr -d '\n\r')"
  if [[ "$CLIP" == r8_* ]]; then
    set_kv REPLICATE_API_TOKEN "$CLIP"
    echo "Pasted REPLICATE_API_TOKEN from clipboard."
  elif [[ "$CLIP" == vercel_blob_rw_* ]]; then
    set_kv BLOB_READ_WRITE_TOKEN "$CLIP"
    echo "Pasted BLOB_READ_WRITE_TOKEN from clipboard."
  fi
  if has_replicate && has_blob; then
    exit 0
  fi
fi

cat <<EOF
Vercel blocks "Copy" on Sensitive variables — this is expected.

Ways to get BLOB_READ_WRITE_TOKEN locally:

1. Storage → censorai-videos-public → Settings → Regenerate read-write token
   (shown once) → paste into: $SECRETS

2. Env var row → ⋮ → Manage Blob Connection → reconnect store if offered

3. Copy token to clipboard (vercel_blob_rw_…) and run: ./scripts/import-secrets.sh

REPLICATE (r8_…) — same file, or Replicate dashboard.

Then restart backend: cd backend && .venv/bin/uvicorn main:app --reload --port 8000
EOF
