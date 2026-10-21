# GhostRange MVP

**Release:** Hackathon MVP v0.1  
**Implements:** Cloud Identity Compromise only  
**Track:** Best Apps and Agents  
**Delivery target:** Professional, deployable, reproducible vertical slice

## 1. MVP statement

Build a working web application that simulates a fictional cloud identity compromise, generates synthetic telemetry for seven attack stages, evaluates a small documented detection-rule language, explains missed detections with Nemotron through Nebius Token Factory, validates proposed rule improvements, and shows a real before/after coverage comparison.

The MVP is complete when the full workflow works without contacting any real cloud account or executing any offensive action.

## 2. Exact demo workflow

1. Open the GhostRange dashboard.
2. Select the available Cloud Identity Compromise scenario.
3. Review the fictional environment and loaded detection rules.
4. Click **Run Simulation**.
5. Observe run status and the seven-stage attack graph.
6. See detected, partial, and missed stages.
7. Open a missed stage and inspect its synthetic events.
8. Inspect the rule that failed to match and the mismatch reason.
9. Request an evidence-grounded Nemotron explanation.
10. Review a proposed rule diff.
11. Validate the proposal locally.
12. Re-run the evaluator with the proposal.
13. Compare before/after coverage.
14. Export the report.

## 3. Implemented scenario

The scenario ID is `cloud-identity-compromise-v1` and contains these stages:

```text
S1 Initial access
S2 MFA manipulation
S3 Discovery
S4 Privilege escalation
S5 Persistence
S6 Sensitive access
S7 Data staging
```

The simulator uses one fictional environment, a fixed default seed, fictional identities, fictional resources, and reserved documentation IP addresses. It generates enough positive and negative events to test both matching and non-matching behavior.

## 4. MVP rule language

Implement a small, documented YAML syntax:

```yaml
title: Privilege Escalation Through Admin Role Attachment
id: gr-rule-s4-admin-role
stage: S4
logsource:
  product: cloud
  service: iam
selection:
  action: AttachRolePolicy
  policy|contains: AdministratorAccess
condition: selection
level: high
```

Required support:

- Exact field matching.
- `contains` matching.
- Rule ID, title, stage, logsource, selection, condition, and level.
- Clear validation errors for missing fields or unsupported operators.

Do not implement full Sigma compatibility in the MVP.

## 5. Coverage algorithm

For each attack stage, the evaluator examines generated events and enabled rules mapped to that stage.

- `detected`: an expected event is matched by at least one valid rule.
- `partial`: a related event is matched but a required event or correlation is not.
- `missed`: no valid rule matches an expected event.
- `error`: parsing or evaluation prevented a valid result.

The overall score must be computed from the scenario's stage-weight configuration. Store the formula and stage-level results so the score is explainable. Do not hard-code the demo score.

## 6. Required backend modules

```text
apps/api/app/
├── main.py                  # FastAPI app
├── config.py                # environment configuration
├── api/
│   ├── health.py
│   ├── scenarios.py
│   ├── runs.py
│   ├── explanations.py
│   ├── proposals.py
│   └── reports.py
├── domain/
│   ├── scenarios/           # scenario loading and validation
│   ├── simulation/          # seeded telemetry generation
│   ├── telemetry/           # normalized event models
│   ├── detections/          # YAML parser and evaluator
│   ├── coverage/            # stage and score calculation
│   └── reports/             # report models and rendering
├── ai/
│   ├── client.py            # Nebius Token Factory client
│   ├── prompts.py
│   ├── schemas.py
│   └── grounding.py
├── persistence/
│   ├── models.py
│   ├── repository.py
│   └── database.py
└── shared/
    ├── errors.py
    └── ids.py
```

## 7. Required frontend modules

```text
apps/web/src/
├── app/
├── components/
├── features/
│   ├── overview/
│   ├── scenarios/
│   ├── attack-graph/
│   ├── telemetry/
│   ├── detections/
│   ├── improvements/
│   └── reports/
├── lib/
└── types/
```

The frontend must not calculate authoritative coverage or call Nebius directly. It consumes typed API responses.

## 8. Required data objects

The MVP needs these persisted objects:

- `Scenario`: ID, version, seed, stages, synthetic-only flag.
- `Run`: ID, scenario ID, seed, status, timestamps, error.
- `TelemetryEvent`: ID, run ID, stage ID, timestamp, source, identity, action, resource, attributes.
- `DetectionRule`: ID, version, YAML/source, stage, parser status, enabled flag.
- `RuleMatch`: run ID, event ID, rule ID, stage ID, match details.
- `StageResult`: stage ID, status, expected events, matched rules, latency, evidence IDs.
- `CoverageResult`: score, stage counts, formula version, evaluator errors.
- `AIArtifact`: task type, input evidence IDs, output, model, status, validation errors.
- `RuleProposal`: original rule ID, proposed source, rationale, validation result.

## 9. Suggested API

```text
GET  /api/health
GET  /api/scenarios
GET  /api/scenarios/{scenario_id}
POST /api/runs
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/graph
GET  /api/runs/{run_id}/telemetry
GET  /api/runs/{run_id}/coverage
POST /api/runs/{run_id}/explanations
POST /api/runs/{run_id}/rule-proposals
POST /api/runs/{run_id}/rule-proposals/{proposal_id}/validate
GET  /api/runs/{run_id}/report
```

## 10. AI tasks in the MVP

Nemotron is used for three required tasks:

1. Explain why a selected stage was missed or partially detected.
2. Propose a modification in the supported rule syntax.
3. Generate a report summary from structured evaluation results.

The model receives structured evidence and must return validated JSON. It may cite only IDs supplied in the request. If the AI service is unavailable, the run still completes and the UI shows a degraded explanation state.

## 11. Seeded data and expected demo behavior

The default demo seed should intentionally produce a mixture of outcomes, not a perfect score. Starter rules should detect several stages, partially detect at least one, and miss at least one important stage.

The rule-improvement flow must produce a measurable improvement after deterministic validation. The exact number is not prescribed, but the result must be non-trivial, reproducible, and visible in the UI.

## 12. Ten-day build sequence

**Days 1–2:** repository, schemas, scenario fixtures, simulator, deterministic telemetry, and unit tests.

**Days 3–4:** rule parser, evaluator, coverage calculator, persistence, run lifecycle, and API endpoints.

**Days 5–6:** dashboard, scenario view, attack graph, telemetry explorer, and live API wiring.

**Days 7–8:** Nebius/Nemotron integration, evidence-grounded explanations, rule proposal diff, validation loop, and reports.

**Day 9:** deployment, accessibility, error states, CI, security review, README, and demo reset.

**Day 10:** clean-install verification, end-to-end demo rehearsal, video recording, repository finalization, and submission.

## 13. Acceptance criteria

The MVP passes acceptance when:

- A fresh installation runs using documented commands.
- The dashboard loads without credentials in deterministic demo mode.
- A run produces the seven stages and synthetic events.
- A fixed seed reproduces the same result.
- The evaluator distinguishes detected, partial, missed, and error states.
- Rules are evaluated by backend logic rather than model judgment.
- Telemetry is inspectable and marked synthetic.
- Nemotron is called through Nebius Token Factory in the normal AI flow.
- AI output is schema-validated and evidence-grounded.
- A proposed rule can be validated and compared.
- The report contains limitations and does not overclaim production security.
- No feature contacts or modifies external infrastructure.
- The repository contains an open-source license, README, setup steps, and `.env.example` without secret values.

## 14. Not part of this MVP

Do not implement live AWS/Azure/GCP integrations, real SIEM connectors, exploit execution, malware samples, public scanning, automatic remediation, full Sigma support, multi-tenant accounts, billing, or the future scenario cards.
