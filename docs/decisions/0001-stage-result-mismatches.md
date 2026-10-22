# Decision 0001 — StageResult gains `mismatches`

**Date:** 2026-10-22 · **Author:** Evin · **Status:** implemented (backend + contracts)
**Affects:** `packages/schemas/json/stage-result.schema.json`, `packages/schemas/ts/contracts.ts`, `GET /api/runs/{id}/coverage`, stage detail views

## Old shape

`StageResult` had no mismatch information. A missed stage said *that* it
missed; the only per-rule diagnostics were parser errors. The UI could not
show "why the rule failed" (MVP demo step 8) without inventing data.

## New shape

```ts
interface StageResult {
  // ...existing fields unchanged...
  mismatches: RuleMismatch[];   // NEW, capped at 50 per stage
}

interface RuleMismatch {
  ruleId: string;
  eventId: string;
  failedExpressions: {
    field: string;              // e.g. "action", "attributes.policy"
    operator: "exact" | "contains";
    expected: string;           // what the rule wanted
    actual: string | null;      // what the event had; null = field absent
  }[];
}
```

## Reason

The improvement workflow needs a human-readable mismatch reason per rule and
event. `actual: null` is deliberate: "field absent on event" is a different
failure from "value differed" and should be phrased differently in the UI.

## Semantics (do not violate in the UI)

- Mismatches exist only for **expected** events. Background noise failing to
  match is correct behavior, not a gap — never render it as one.
- Matched (rule, event) pairs never appear in `mismatches`.
- `failedExpressions` lists **every** failing expression, not just the first.
- Cap is 50 per stage; order is deterministic (rules in fixture order, events
  in timeline order).

## Screens to update

- Stage detail / detection workspace: render mismatch reasons per rule.
- Attack graph: no change required (statuses unchanged).

## Related additions (same batch)

Two new endpoints, both serving existing data:

```text
GET /api/runs/{run_id}/rules                # run's rule snapshot incl. parserStatus/parserErrors
GET /api/runs/{run_id}/stages/{stage_id}    # StageDetail: result (with mismatches) + stage events
```

`StageDetail` references rules by ID (`result.matchedRuleIds`); resolve them
via the `/rules` endpoint rather than expecting duplicated payloads.

## Example (real output, default seed)

Stage S2, rule `rule_s2_mfa_device_deletion`, event `evt_s2_03`:

```json
{
  "ruleId": "rule_s2_mfa_device_deletion",
  "eventId": "evt_s2_03",
  "failedExpressions": [
    { "field": "action", "operator": "exact",
      "expected": "DeleteVirtualMfaDevice", "actual": "UpdateMfaPreference" }
  ]
}
```
