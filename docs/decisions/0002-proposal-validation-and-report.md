# Decision 0002 — Proposal validation flow and run report

**Date:** 2026-10-23 · **Author:** Evin · **Status:** implemented (backend + contracts)
**Affects:** `packages/schemas/json/report.schema.json` (new), `packages/schemas/ts/contracts.ts`, proposal endpoints, `GET /api/runs/{id}/report`, Reports screen

## Context

The improvement loop (MVP demo steps 11–13) needs a deterministic way to
answer: *does this proposed rule actually improve coverage?* And FR-10
requires a structured report with evidence references, assumptions, and
limitations. Both must work without any AI dependency.

## Decisions

### 1. Proposal validation is fully deterministic

```text
POST /api/runs/{run_id}/rule-proposals            # parse now; store proposed|rejected
POST /api/runs/{run_id}/rule-proposals/{id}/validate   # before/after comparison
GET  /api/runs/{run_id}/rule-proposals            # list for the workspace
```

- The proposed rule **replaces** the original rule in the rule set during
  validation (proposals are modifications, not additions). If the original is
  not in the run's rule set, the proposal is treated as an addition.
- `coverageBefore` is the run's **stored** score — never recomputed. The
  stored result is authoritative.
- `improvesCoverage = coverageAfter > coverageBefore`, computed only by the
  deterministic evaluator. Nemotron never sets it.
- Unparseable proposals are stored with `status: rejected`,
  `parserStatus: invalid`, and `improvesCoverage: null` — a parser error is
  not a security miss.
- The stored original rule is **never modified** by a proposal.

### 2. The report is deterministic-first with an optional AI slot

`RunReport` (new contract, `report.schema.json`):

```ts
interface RunReport {
  runId: string;
  scenario: { id: string; name: string; version: string };
  seed: number;
  generatedAt: string;
  coverage: CoverageResult;          // embedded as-is
  improvements: ReportImprovement[]; // validated + improving proposals ONLY
  assumptions: string[];
  limitations: string[];             // static, honest; never remove entries
  aiSummary: AiArtifact | null;      // days 7-8; null = degraded-AI state
}
```

- `improvements` contains only proposals with `status: validated` AND
  `improvesCoverage: true`. Never-validated or non-improving proposals are
  not improvements and must not be presented as such.
- `limitations` is a static, honest list (synthetic-only, subset parser,
  single scenario, weighted coverage, AI may be unavailable). Removing
  entries to make a report look stronger is a contract violation.
- `aiSummary: null` is a valid, complete report state. The UI renders a
  degraded-AI notice, not an error.

## Screens to update

- Improvement workspace: proposal list, validate button, before/after display.
- Reports screen: render `RunReport`; show limitations prominently; render
  `aiSummary === null` as "AI summary unavailable", not an error.
