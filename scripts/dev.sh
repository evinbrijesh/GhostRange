#!/usr/bin/env bash
# Start backend and frontend for local development.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Starting GhostRange dev servers..."
echo "  API  -> http://localhost:8000/api/health"
echo "  Web  -> http://localhost:5173"

(cd apps/api && uv run uvicorn app.main:app --reload) &
API_PID=$!
(cd apps/web && npm run dev) &
WEB_PID=$!

trap 'kill $API_PID $WEB_PID 2>/dev/null' EXIT
wait
