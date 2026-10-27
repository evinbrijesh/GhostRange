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

- **Deterministic demo mode** — works out-of-the-box with zero API keys. Runs the seeded simulation, evaluates rules with deterministic logic, calculates coverage, generates fallback rule improvements, and serves curated MITRE ATT&CK threat intelligence.
- **Live AI & Threat Intel mode** — enabled when sponsor keys (`NEBIUS_API_KEY`, `TAVILY_API_KEY`) are configured:
  - **NVIDIA Nemotron (`nvidia/nemotron-4-340b-instruct`) via Nebius Token Factory**: Generates evidence-grounded gap explanations, synthesizes detection rule proposals, and creates executive risk briefings. All AI outputs are strictly constrained to cite synthetic evidence IDs (`event:...`, `rule:...`, `stage:...`).
  - **Tavily Search API**: Dynamically retrieves real-world threat intelligence, active adversary TTPs, and detection tradecraft for each scenario stage.

All credentials stay strictly server-side. A fixed scenario version and seed always produce the exact same telemetry and authoritative coverage score.

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

Without sponsor keys the API automatically operates in deterministic fallback mode; all workflows remain fully functional and verifiable.

## Try the demo

```bash
./scripts/seed.sh    # creates the fixed demo run (idempotent)
./scripts/reset.sh   # clears all demo state (idempotent)
```

Or explore runs and AI-assisted workflows through the API:

```bash
# 1. Create a simulation run
curl -s -X POST localhost:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"scenarioId":"cloud-identity-compromise-v1"}'

# 2. Inspect graph, coverage, and stages (replace RUN_ID)
curl -s localhost:8000/api/runs/RUN_ID/graph
curl -s localhost:8000/api/runs/RUN_ID/coverage
curl -s localhost:8000/api/runs/RUN_ID/stages/S2      # mismatch reasons
curl -s "localhost:8000/api/runs/RUN_ID/telemetry?expected=true"

# 3. Request Nemotron-generated rule proposal for a blind spot
curl -s -X POST localhost:8000/api/runs/RUN_ID/rule-proposals/generate \
  -H 'Content-Type: application/json' \
  -d '{"stageId":"S2"}'

# 4. Validate proposal with cumulative stacking across stages
curl -s -X POST "localhost:8000/api/runs/RUN_ID/rule-proposals/validate?cumulative=true" \
  -H 'Content-Type: application/json' \
  -d '{"ruleId":"rule_s2_mfa_update","stageId":"S2","yamlSource":"..."}'

# 5. Generate AI Executive Briefing summary
curl -s -X POST localhost:8000/api/runs/RUN_ID/report/summary

# 6. Fetch Tavily threat intelligence for a stage
curl -s localhost:8000/api/threat-intel/stages/S2

# 7. Inspect DetectionOps 4-tier metrics (coverage, resilience, suppression, regression)
curl -s localhost:8000/api/runs/RUN_ID/detection-ops
curl -s localhost:8000/api/runs/RUN_ID/variants
curl -s localhost:8000/api/runs/RUN_ID/matches
curl -s localhost:8000/api/runs/RUN_ID/ci-report
```

The default seed intentionally produces a mixed result — 50.0% coverage with
detected, partial, and missed stages — so there is a real gap to remediate.
Remediating Stage S2 jumps coverage to 60.0%, and cumulatively fixing Stage S6 reaches 75.0%.
Runs are stored in SQLite (`DATABASE_URL`) and survive backend restarts.

## Tests and lint

```bash
cd apps/api
uv run pytest -q        # 103 tests: determinism, variants, benign suppression, DetectionOps, AI, reports
uv run ruff check app tests

cd ../web
npm run typecheck
npm run build
```

CI runs the same checks on every push and pull request.

## Documentation

- [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) — 3-minute hackathon pitch & live demo walkthrough
- [`docs/PRD.md`](docs/PRD.md) — product intent and requirements
- [`docs/MVP.md`](docs/MVP.md) — exact MVP scope and acceptance criteria
- [`CLAUDE.md`](CLAUDE.md) — implementation contract (read before changing code)
- [`docs/TEAM_PLAN.md`](docs/TEAM_PLAN.md) — team ownership and ten-day roadmap

## License

[MIT](LICENSE)
