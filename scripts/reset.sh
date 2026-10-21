#!/usr/bin/env bash
# Reset demo state (idempotent).
#
# STATUS: with in-memory persistence, restarting the backend resets all state.
# This script will clear the database once SQLite persistence lands.
set -euo pipefail
echo "In-memory demo state resets when the backend restarts."
echo "To reset now: restart the API (see scripts/dev.sh)."
