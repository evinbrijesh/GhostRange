"""Run pipeline orchestration: telemetry -> evaluation -> coverage -> RunRecord.

This module is the single place that knows the *order* of a run's execution.
Both the API (POST /api/runs) and the demo CLI (app/demo.py seed) call it, so
there is exactly one implementation of the deterministic path and no chance of
the two drifting apart.

It contains no HTTP concerns and no persistence decisions: it receives a Run,
produces a RunRecord, and the caller decides where that record goes.
"""

from app.domain.coverage.calculator import calculate_coverage
from app.domain.detections.evaluator import evaluate_run
from app.domain.detections.parser import parse_rule
from app.domain.scenarios.models import Scenario
from app.domain.simulation.engine import generate_telemetry
from app.persistence.models import Run
from app.persistence.repository import RunRecord


def execute_run(scenario: Scenario, rule_sources: list[str], run: Run) -> RunRecord:
    """Execute the deterministic pipeline for a prepared run.

    Inputs: a validated scenario, raw rule YAML sources, and a Run whose id and
    seed are already fixed (determinism depends on both).
    Output: a complete RunRecord — events, parsed rules, matches, coverage.
    """
    events = generate_telemetry(scenario, run.id, run.seed)
    stage_results, matches, evaluator_errors, rules = evaluate_run(
        [s.id for s in scenario.stages], events, rule_sources, run.id
    )
    coverage = calculate_coverage(
        run_id=run.id,
        stage_results=stage_results,
        stage_weights={s.id: s.weight for s in scenario.stages},
        evaluator_errors=evaluator_errors,
    )
    return RunRecord(run=run, scenario=scenario, events=events,
                     rules=rules, matches=matches, coverage=coverage)


def validate_proposal(
    record: RunRecord, original_rule_id: str, proposed_source: str
) -> tuple[bool, float | None, float | None]:
    """Deterministically validate a proposed rule against the run's own telemetry.

    The proposed rule REPLACES the original in the rule set (proposals are
    modifications, not additions). The stored original rule is never modified.

    Returns (improves_coverage, coverage_before, coverage_after).
    coverage_before is the run's stored score — never recomputed, the stored
    result is authoritative. Returns (False, before, None) when the proposal
    does not parse: a parser error is not a security miss.
    """
    assert record.coverage is not None
    coverage_before = record.coverage.score

    proposed_rule, _selection = parse_rule(proposed_source)
    if proposed_rule.parser_status != "valid":
        return False, coverage_before, None

    rule_sources = []
    replaced = False
    for rule in record.rules:
        if rule.id == original_rule_id:
            rule_sources.append(proposed_source)
            replaced = True
        else:
            rule_sources.append(rule.source)
    if not replaced:
        # Original not in the run's rule set: treat the proposal as an addition.
        rule_sources.append(proposed_source)

    stage_results, _matches, evaluator_errors, _rules = evaluate_run(
        [s.id for s in record.scenario.stages], record.events, rule_sources, record.run.id
    )
    after = calculate_coverage(
        run_id=record.run.id,
        stage_results=stage_results,
        stage_weights={s.id: s.weight for s in record.scenario.stages},
        evaluator_errors=evaluator_errors,
    )
    return after.score > coverage_before, coverage_before, after.score