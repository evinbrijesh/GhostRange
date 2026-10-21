# GhostRange

GhostRange is a **defensive security-control validation platform**. It safely simulates a fictional cloud identity compromise, generates synthetic security telemetry, evaluates detection rules against that telemetry with deterministic logic, identifies blind spots, and helps security teams improve and re-test their controls.

GhostRange is not a chatbot, an offensive scanner, or a live red-team tool. It answers one practical question:

> If this attack happened tomorrow, would our existing security controls detect it?

> **Safety:** GhostRange never connects to, scans, or modifies real infrastructure. All identities, resources, events, and IP addresses are fictional or from reserved documentation ranges, and every generated record is marked `synthetic: true`.

## How it works

```text
Run a safe simulation
        ↓
Measure detection coverage
        ↓
Inspect synthetic evidence
        ↓
Explain a blind spot with NVIDIA Nemotron (via Nebius Token Factory)
        ↓
Validate a proposed rule improvement
        ↓
Prove the before/after improvement
```

The deterministic simulator, rule parser, evaluator, and coverage calculator are the single source of truth. Nemotron explains results, proposes rules, and summarizes reports — it never sets scores or decides matches.

## Scenario

The MVP implements one scenario: **Cloud Identity Compromise** (`cloud-identity-compromise-v1`), with seven stages:

```text
S1 Initial access
S2 MFA manipulation
S3 Discovery
S4 Privilege escalation
S5 Persistence
S6 Sensitive access
S7 Data staging
```

All other scenarios are roadmap items and are shown as Coming Soon.

## Repository structure

```text
ghostrange/
├── apps/
│   ├── api/          # Python/FastAPI backend: simulation, rule engine, coverage, AI, persistence
│   └── web/          # React/TypeScript frontend: dashboard and product experience
├── packages/
│   └── schemas/      # shared data contracts (single source for API shapes)
├── scenarios/        # scenario fixtures (cloud-identity-compromise)
├── docs/             # team plan and supporting documents
├── docs/             # PRD, MVP, team plan, and supporting documents
├── CLAUDE.md         # implementation contract for AI coding agents
└── README.md
```

## Modes

- **Deterministic demo mode** — works with no API keys. Runs the seeded simulation, evaluates rules, and shows coverage. AI-dependent features show a clear degraded state.
- **Live Nemotron mode** — adds evidence-grounded explanations, rule proposals, and report summaries through Nebius Token Factory. Credentials stay server-side.

A fixed scenario version and seed always produce the same telemetry and coverage score.

## Setup

```bash
cp .env.example .env   # fill in locally; never commit .env

# Backend (Python 3.12+, uv)
cd apps/api
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000/api/health

# Frontend (Node 18+)
cd apps/web
npm install
npm run dev                            # http://localhost:5173
```

Without a Nebius key the API runs in deterministic demo mode; AI-dependent
features report a degraded state instead of failing.

## Try the demo (backend only, so far)

```bash
# create a run (uses the scenario's default seed)
curl -s -X POST localhost:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"scenarioId":"cloud-identity-compromise-v1"}'

# inspect the results (replace RUN_ID)
curl -s localhost:8000/api/runs/RUN_ID/graph
curl -s localhost:8000/api/runs/RUN_ID/coverage
curl -s "localhost:8000/api/runs/RUN_ID/telemetry?expected=true"
```

The default seed intentionally produces a mixed result — 50.0% coverage with
detected, partial, and missed stages — so there is a real gap to remediate.

## Tests and lint

```bash
cd apps/api
uv run pytest -q        # 42 tests: determinism, parser, evaluator, coverage, API
uv run ruff check app tests

cd ../web
npm run typecheck
npm run build
```

CI runs the same checks on every push and pull request.

## Documentation

- [`docs/PRD.md`](docs/PRD.md) — product intent and requirements
- [`docs/MVP.md`](docs/MVP.md) — exact MVP scope and acceptance criteria
- [`CLAUDE.md`](CLAUDE.md) — implementation contract (read before changing code)
- [`docs/TEAM_PLAN.md`](docs/TEAM_PLAN.md) — team ownership and ten-day roadmap

## License

[MIT](LICENSE)
