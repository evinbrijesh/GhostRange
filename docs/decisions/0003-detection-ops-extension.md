# Decision 0003 — DetectionOps extension, committed baseline, and CI gate

**Date:** 2026-10-28 · **Author:** Architect · **Status:** accepted (owner-approved)
**Affects:** scenario `environment` contract, variants/benign modules, DetectionOps metrics,
`detection-baseline.json`, `POST /api/runs/{id}/regression-analysis`,
`GET /api/runs/{id}/detection-ops|variants|ci-report`, `POST /api/rules/validate|evaluate`,
Tavily threat intel, GitHub Actions gate

## Context

`docs/MVP.md` scopes the hackathon build to simulation, detection evaluation,
coverage, AI explanation/proposal, and reporting. The team later added five
capabilities that were not in that scope:

1. Behavioral scenario variants (`var-location-shift`, `var-delayed-mfa`,
   `var-admin-noise`) and a deterministic resilience metric.
2. A benign administrative-event corpus and offline false-positive estimate.
3. A four-tier DetectionOps metric suite and CI-facing Markdown report.
4. Tavily-backed external threat context.
5. A user-facing scenario environment block (organization, identity, note).

The owner explicitly requested these as a post-MVP extension. Without a
recorded decision, the repository would contradict its own contract
("do not expand beyond MVP without an explicit decision") and later agents
would not know which boundary is authoritative.

## Decisions

### 1. The core MVP remains unchanged; this is an approved v0.2 extension

`docs/MVP.md` still defines what must work for the demo. The extension is
additive:

- It must not change the authoritative coverage score or stage statuses.
- It must degrade safely: variants, benign suppression, and CI reporting are
  deterministic and run without AI keys or network access.
- It must not contact infrastructure. Tavily is read-only external context.

### 2. The regression baseline is a committed, reviewable artifact

```text
scenarios/<scenario>/detection-baseline.json
```

```json
{
  "scenarioId": "cloud-identity-compromise-v1",
  "scenarioVersion": "1.0.0",
  "formulaVersion": "coverage-v1",
  "seed": 1337,
  "attackCoverage": 50.0,
  "variantResilience": 48.8,
  "benignSuppression": 100.0,
  "noiseRisk": "low"
}
```

- The baseline is **not** a hard-coded constant in application code and
  **not** a database row. CI must be able to compare a fresh clone.
- Changing rule behavior that lowers a metric requires an explicit baseline
  update in the same pull request. That is the gate's purpose.
- A missing, unreadable, or scenario/formula/seed-mismatched baseline is a
  configuration failure. It must never be reported as a security result.
- The loader accepts `GHOSTRANGE_BASELINE_PATH` for tests and forks.
  It is not a production feature toggle.

### 3. The gate is deterministic and blocking

`app.domain.coverage.detection_ops.evaluate_gate(metrics, baseline)` is the
only place that decides PASS/BLOCKED. It checks, all as floors:

| Check | Requirement |
| --- | --- |
| `attack_coverage` | ≥ baseline |
| `variant_resilience` | ≥ baseline |
| `benign_suppression` | ≥ baseline |
| `noise_risk` | rank ≤ baseline |

- Any failed check blocks; equal values pass.
- `python -m app.demo ci` exits non-zero on any failed check or missing
  baseline. GitHub Actions runs it as a required step.
- `GET /api/runs/{id}/ci-report` returns the same gate verdict and the gate
  checks. The frontend displays it; it does not recompute it.
- `POST /api/runs/{id}/regression-analysis` defaults to the committed
  baseline. It must not fall back to a hard-coded score.

### 4. Variants and benign events are synthetic and deterministic

- Variants derive from the same event templates with controlled IP/time
  changes, seeded per variant. No LLM-generated behavior.
- Benign events are explicitly `expected: false`, `synthetic: true`.
- A variant result is evidence for rule resilience, never a replacement for
  the primary coverage score.

### 5. Tavily is optional context, never evidence

- `TAVILY_API_KEY` is optional. Without it (or on error) the endpoint returns
  curated MITRE ATT&CK reference data with `liveSearch: false`.
- Sources are returned with titles and URLs and labeled in the UI.
- Tavily output must never be stored as telemetry, cited as run evidence, or
  used to compute coverage.

### 6. The scenario environment is served by the API

The `Scenario` contract gained an `environment` object
(`organization`, `compromisedIdentity`, `note`). The frontend renders it; it
must not hard-code tenant names, identities, or regions.

## Contract additions

New canonical schemas under `packages/schemas/json/`:

```text
detection-baseline.schema.json
detection-ops.schema.json
detection-ops-gate.schema.json
variants.schema.json
regression-analysis.schema.json
ci-report.schema.json
matches-response.schema.json
rule-validation.schema.json
rule-evaluation.schema.json
threat-intel.schema.json
```

`packages/schemas/ts/contracts.ts` mirrors them. Endpoints return typed
models or these shapes; ad-hoc response dictionaries are not acceptable for
new endpoints.

## Consequences

- `docs/MVP.md` gains a short extension section pointing here.
- `CLAUDE.md` module map lists `coverage/detection_ops.py`,
  `coverage/baseline.py`, `simulation/variants.py`, `simulation/benign.py`,
  `ai/tavily.py`.
- Adding a new stage or changing weights requires a new baseline file and a
  new version. The gate fails closed until then.
- The demo flow is unchanged: 50% baseline, S2 proposal → 60%, cumulative S6
  → 75%. The CI gate is an engineering control, not a demo step.
