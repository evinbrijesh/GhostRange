#!/usr/bin/env bash
# Start backend and frontend for local development.
set -euo pipefail
cd "$(dirname "$0")/.."

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"

echo "Starting GhostRange dev servers..."
echo "  API  -> http://localhost:${API_PORT}/api/health"
echo "  Web  -> http://localhost:${WEB_PORT}"

(cd apps/api && uv run uvicorn app.main:app --reload --port "$API_PORT") &
API_PID=$!
(cd apps/web && VITE_API_URL="http://127.0.0.1:${API_PORT}" npm run dev -- --port "$WEB_PORT" --strictPort) &
WEB_PID=$!

trap 'kill $API_PID $WEB_PID 2>/dev/null' EXIT
wait
