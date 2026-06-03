#!/usr/bin/env bash
# One-time local secrets setup (Vercel "Sensitive" vars cannot be pulled via CLI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS="$ROOT/backend/.env.secrets"
EXAMPLE="$ROOT/backend/.env.secrets.example"

if [[ -f "$SECRETS" ]] && grep -q '^REPLICATE_API_TOKEN=r8_' "$SECRETS" 2>/dev/null; then
  echo "backend/.env.secrets already has REPLICATE_API_TOKEN"
  exit 0
fi

if [[ ! -f "$SECRETS" ]]; then
  cp "$EXAMPLE" "$SECRETS"
  echo "Created $SECRETS from example."
fi

if command -v pbpaste >/dev/null 2>&1; then
  CLIP="$(pbpaste | tr -d '\n')"
  if [[ "$CLIP" == r8_* ]]; then
    if grep -q '^REPLICATE_API_TOKEN=' "$SECRETS"; then
      sed -i '' "s|^REPLICATE_API_TOKEN=.*|REPLICATE_API_TOKEN=$CLIP|" "$SECRETS"
    else
      echo "REPLICATE_API_TOKEN=$CLIP" >> "$SECRETS"
    fi
    echo "Pasted REPLICATE_API_TOKEN from clipboard."
    exit 0
  fi
fi

echo "Open Vercel → censorai → Settings → Environment Variables → Production"
echo "Reveal REPLICATE_API_TOKEN and BLOB_READ_WRITE_TOKEN, then edit:"
echo "  $SECRETS"
echo ""
echo "Or copy token to clipboard (starts with r8_) and run this script again."
