"""Deterministic rule evaluation.

Semantics (documented in docs/MVP.md §5):
- A rule considers an event only when rule.logsource.service == event.source.
- All selection expressions must match (AND). Exact: equality. Contains: substring.
- Stage status over the stage's EXPECTED events:
    detected — every expected event matched by at least one valid rule
    partial  — some, but not all, expected events matched
    missed   — no expected event matched
    error    — the stage has rules but NONE are validly parseable, so no
               evaluation was possible. A parser error is not a security miss;
               it is reported in StageResult.errors and CoverageResult.evaluator_errors.
- A stage with no rules at all is `missed` (no detection configured).
- Background (non-expected) events still produce RuleMatch records — useful for
  inspecting rule noise — but never affect stage status.
"""

from collections import defaultdict

from app.domain.detections.models import DetectionRule, RuleMatch, StageResult
from app.domain.detections.parser import parse_rule
from app.domain.telemetry.models import TelemetryEvent
from app.shared.vocab import StageStatus


def flatten_event(event: TelemetryEvent) -> dict[str, str]:
    """Project an event onto the flat field names the rule language addresses."""
    flat: dict[str, str] = {
        "action": event.action,
        "source": event.source.value,
        "srcIp": event.src_ip,
        "identity.id": event.identity.id,
        "identity.type": event.identity.type,
        "resource.id": event.resource.id,
        "resource.type": event.resource.type,
    }
    for key, value in event.attributes.items():
        flat[f"attributes.{key}"] = str(value)
    return flat


def _match_selection(
    selection: tuple[tuple[str, str, str], ...], flat: dict[str, str]
) -> tuple[bool, dict]:
    details: dict = {}
    for base, operator, expected in selection:
        actual = flat.get(base)
        if actual is None:
            return False, {"unmatched_field": base, "reason": "field absent on event"}
        if operator == "contains":
            ok = expected in actual
        else:
            ok = actual == expected
        if not ok:
            return False, {"unmatched_field": base, "expected": expected, "actual": actual}
        details[base] = {"operator": operator, "value": expected}
    return True, details


def evaluate_stage(
    stage_id: str,
    events: list[TelemetryEvent],
    compiled_rules: list[tuple[DetectionRule, tuple[tuple[str, str, str], ...]]],
    run_id: str,
) -> tuple[StageResult, list[RuleMatch], list[str]]:
    """Evaluate one stage. Returns (stage result, match records, parser errors)."""
    stage_events = [e for e in events if e.stage_id == stage_id]
    expected = [e for e in stage_events if e.expected]
    stage_rules = [rc for rc in compiled_rules if rc[0].stage_id == stage_id]
    valid_rules = [rc for rc in stage_rules if rc[0].parser_status == "valid" and rc[0].enabled]

    parser_errors = [err for rc in stage_rules if rc[0].parser_status == "invalid" for err in rc[0].parser_errors]

    matches: list[RuleMatch] = []
    matched_expected_ids: set[str] = set()
    matched_rule_ids: set[str] = set()

    for rule, selection in valid_rules:
        for event in stage_events:
            if event.source != rule.logsource.service:
                continue
            ok, details = _match_selection(selection, flatten_event(event))
            if ok:
                matches.append(
                    RuleMatch(
                        id=f"match_{rule.id}_{event.id}",
                        run_id=run_id,
                        event_id=event.id,
                        rule_id=rule.id,
                        stage_id=stage_id,
                        matched_at=event.timestamp,
                        details=details,
                    )
                )
                if event.expected:
                    matched_expected_ids.add(event.id)
                    matched_rule_ids.add(rule.id)

    if not expected:
        status = StageStatus.MISSED
    elif not stage_rules:
        status = StageStatus.MISSED  # no detection configured for this stage
    elif not valid_rules:
        status = StageStatus.ERROR  # rules exist but none could be evaluated
    elif len(matched_expected_ids) == len({e.id for e in expected}):
        status = StageStatus.DETECTED
    elif matched_expected_ids:
        status = StageStatus.PARTIAL
    else:
        status = StageStatus.MISSED

    latency_ms: int | None = None
    if matched_expected_ids and expected:
        first_expected = min(e.timestamp for e in expected)
        first_matched = min(
            e.timestamp for e in expected if e.id in matched_expected_ids
        )
        latency_ms = int((first_matched - first_expected).total_seconds() * 1000)

    result = StageResult(
        stage_id=stage_id,
        status=status,
        expected_event_ids=[e.id for e in expected],
        matched_event_ids=sorted(matched_expected_ids),
        matched_rule_ids=sorted(matched_rule_ids),
        detection_latency_ms=latency_ms,
        evidence_ids=(
            [f"stage:{stage_id}"]
            + [f"event:{eid}" for eid in sorted(matched_expected_ids)]
            + [f"rule:{rid}" for rid in sorted(matched_rule_ids)]
        ),
        errors=parser_errors,
    )
    return result, matches, parser_errors


def evaluate_run(
    scenario_stages: list[str],
    events: list[TelemetryEvent],
    rule_sources: list[str],
    run_id: str,
) -> tuple[list[StageResult], list[RuleMatch], list[str], list[DetectionRule]]:
    """Parse all rule sources, evaluate every stage, and collect evaluator errors."""
    compiled = [parse_rule(source) for source in rule_sources]
    rules = [rc[0] for rc in compiled]

    stage_results: list[StageResult] = []
    all_matches: list[RuleMatch] = []
    evaluator_errors: list[str] = []

    events_by_stage: dict[str, list[TelemetryEvent]] = defaultdict(list)
    for event in events:
        events_by_stage[event.stage_id].append(event)

    for stage_id in scenario_stages:
        result, matches, parser_errors = evaluate_stage(
            stage_id, events_by_stage.get(stage_id, []), compiled, run_id
        )
        stage_results.append(result)
        all_matches.extend(matches)
        evaluator_errors.extend(parser_errors)

    return stage_results, all_matches, evaluator_errors, rules