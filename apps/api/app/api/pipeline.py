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