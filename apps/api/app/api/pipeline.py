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
    record: RunRecord,
    original_rule_id: str,
    proposed_source: str,
    prior_improvements: list[tuple[str, str]] | None = None,
) -> tuple[bool, float | None, float | None]:
    """Deterministically validate a proposed rule against the run's own telemetry.

    The proposed rule REPLACES the original in the rule set (proposals are
    modifications, not additions). When `prior_improvements` is provided, those
    previously validated replacements are applied cumulatively. The stored original
    rule is never modified.

    Returns (improves_coverage, coverage_before, coverage_after).
    """
    assert record.coverage is not None

    proposed_rule, _selection = parse_rule(proposed_source)
    if proposed_rule.parser_status != "valid":
        return False, record.coverage.score, None

    prior_map = dict(prior_improvements) if prior_improvements else {}

    # Compute coverage_before (baseline score or cumulative baseline)
    if prior_map:
        base_sources = []
        for rule in record.rules:
            if rule.id in prior_map:
                base_sources.append(prior_map[rule.id])
            else:
                base_sources.append(rule.source)
        st_res, _m, errs, _r = evaluate_run(
            [s.id for s in record.scenario.stages], record.events, base_sources, record.run.id
        )
        before_cov = calculate_coverage(
            run_id=record.run.id,
            stage_results=st_res,
            stage_weights={s.id: s.weight for s in record.scenario.stages},
            evaluator_errors=errs,
        )
        coverage_before = before_cov.score
    else:
        coverage_before = record.coverage.score

    # Compute coverage_after with the new proposal plus prior improvements
    rule_sources = []
    replaced = False
    for rule in record.rules:
        if rule.id == original_rule_id:
            rule_sources.append(proposed_source)
            replaced = True
        elif rule.id in prior_map:
            rule_sources.append(prior_map[rule.id])
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