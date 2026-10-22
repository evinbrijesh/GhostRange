#!/usr/bin/env bash
# Reset demo state: removes all runs. Idempotent — safe to run repeatedly.
set -euo pipefail
cd "$(dirname "$0")/../apps/api"
uv run python -m app.demo reset
