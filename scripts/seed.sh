#!/usr/bin/env bash
# Seed demo data: creates (or refreshes) the fixed demo run.
# Idempotent — safe to run repeatedly.
set -euo pipefail
cd "$(dirname "$0")/../apps/api"
uv run python -m app.demo seed
