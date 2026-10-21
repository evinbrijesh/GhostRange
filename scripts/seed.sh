#!/usr/bin/env bash
# Seed demo data.
#
# STATUS: the deterministic slice currently uses in-memory persistence, so
# there is nothing durable to seed — scenario fixtures and starter rules are
# loaded from scenarios/ at request time. This script will seed the database
# once SQLite persistence lands (MVP days 3-4).
set -euo pipefail
echo "Nothing to seed yet: demo state is in-memory and fixtures load on demand."
echo "Create a demo run with: curl -s -X POST localhost:8000/api/runs -H 'Content-Type: application/json' -d '{\"scenarioId\":\"cloud-identity-compromise-v1\"}'"
