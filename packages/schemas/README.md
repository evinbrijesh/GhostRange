# GhostRange shared contracts

This package is the single source of truth for data shapes exchanged between
the backend (`apps/api`) and the frontend (`apps/web`).

- `json/` — canonical JSON Schema (draft 2020-12) definitions
- `ts/contracts.ts` — TypeScript mirror consumed by the frontend

## Rules

1. **JSON Schema is canonical.** `ts/contracts.ts` must stay in sync; a PR that
   changes a contract updates both, plus affected backend models and screens.
2. Per `TEAM_PLAN.md` §3, contract changes are discussed before implementation
   and recorded with: old shape, new shape, reason, affected files/screens.
3. The authoritative vocabularies are fixed:
   - Run lifecycle: `queued → running → completed | failed`
   - Stage statuses: `detected | partial | missed | error`
   - Evidence references: `event:{id} | rule:{id} | match:{id} | stage:{id}`
   - `error` (parser/evaluator failure) is always reported separately from
     `missed` (a security gap). Never conflate them.
4. The frontend consumes these types; it never computes authoritative coverage
   and never calls Nebius directly.
5. AI output may cite only evidence IDs supplied in the request
   (`inputEvidenceIds`).

## Files

| Schema | Object |
|---|---|
| `common.schema.json` | Shared enums, evidence refs, timestamps, safe messages |
| `scenario.schema.json` | Scenario + stages + weights |
| `run.schema.json` | Run lifecycle |
| `telemetry-event.schema.json` | Synthetic telemetry event |
| `detection-rule.schema.json` | Detection rule + parser status |
| `rule-match.schema.json` | Deterministic rule match |
| `stage-result.schema.json` | Per-stage evaluation result |
| `coverage-result.schema.json` | Score, counts, evaluator errors |
| `ai-artifact.schema.json` | Nemotron output artifact |
| `rule-proposal.schema.json` | Proposed rule + validation result |
| `api-error.schema.json` | Stable error envelope |
