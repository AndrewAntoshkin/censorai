#!/usr/bin/env bash
# One-time production setup (run locally after `render login` or set secrets in GitHub).
set -euo pipefail

REPO="AndrewAntoshkin/censorai"
API_URL="${API_URL:-https://censorai-api.onrender.com}"

if [[ -f backend/.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source backend/.env
  set +a
fi

if [[ -z "${REPLICATE_API_TOKEN:-}" ]]; then
  echo "REPLICATE_API_TOKEN not set. Add it to backend/.env"
  exit 1
fi

echo "Setting GitHub secrets for ${REPO}..."
gh secret set REPLICATE_API_TOKEN --repo "$REPO" --body "$REPLICATE_API_TOKEN"
gh secret set NEXT_PUBLIC_API_URL --repo "$REPO" --body "$API_URL"

if [[ -n "${RENDER_API_KEY:-}" && -n "${RENDER_SERVICE_ID:-}" ]]; then
  gh secret set RENDER_API_KEY --repo "$REPO" --body "$RENDER_API_KEY"
  gh secret set RENDER_SERVICE_ID --repo "$REPO" --body "$RENDER_SERVICE_ID"
  echo "Render deploy secrets configured."
fi

echo ""
echo "If API is not on Render yet, open blueprint deploy:"
echo "  https://render.com/deploy?repo=https://github.com/${REPO}"
echo ""
echo "In Render UI set env: REPLICATE_API_TOKEN (same as local .env)"
echo "Then re-run GitHub Actions: Deploy demo to GitHub Pages"
