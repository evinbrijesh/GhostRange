"""Run lifecycle endpoints: create, inspect, graph, telemetry, coverage.

Orchestration lives here (per CLAUDE.md: api/ = validation and orchestration);
all authoritative computation lives in domain/.
"""

from fastapi import APIRouter, Query

from app.api.pipeline import execute_run
from app.domain.coverage.baseline import BaselineError, DetectionOpsBaseline, load_baseline
from app.domain.coverage.detection_ops import (
    DetectionOpsMetrics,
    RegressionAnalysisResult,
    analyze_regression,
    compute_detection_ops_metrics,
    evaluate_gate,
    generate_ci_report_markdown,
)
from app.domain.detections.loader import load_default_rules
from app.domain.detections.models import StageResult
from app.domain.scenarios.loader import SCENARIO_ID, load_default_scenario
from app.domain.scenarios.models import ContractModel
from app.domain.simulation.variants import (
    VARIANTS,
    calculate_variant_resilience,
    evaluate_variant,
)
from app.domain.telemetry.models import TelemetryEvent
from app.persistence.instance import repository
from app.persistence.models import Run, now_utc
from app.persistence.repository import RunRecord
from app.shared.errors import ApiError, ErrorCode
from app.shared.ids import new_id
from app.shared.vocab import RunStatus

router = APIRouter(prefix="/api", tags=["runs"])


class StageDetail(ContractModel):
    """Response shape for GET /api/runs/{run_id}/stages/{stage_id}.

    Rules are referenced by ID (result.matchedRuleIds) and resolved via
    GET /api/runs/{run_id}/rules — not duplicated here.
    """

    run_id: str
    stage_id: str
    name: str
    description: str
    result: StageResult
    events: list[TelemetryEvent]


def _get_record(run_id: str) -> RunRecord:
    record = repository.get_run(run_id)
    if record is None:
        raise ApiError(ErrorCode.RUN_NOT_FOUND, f"run '{run_id}' does not exist")
    return record


def _committed_baseline(record: RunRecord) -> DetectionOpsBaseline:
    """Load the committed baseline for the run's scenario.

    A missing or mismatched baseline is an internal configuration error, not a
    security result: it must never be reported as detected/missed.
    """
    try:
        return load_baseline(record.scenario)
    except BaselineError as exc:
        raise ApiError(ErrorCode.INTERNAL_ERROR, str(exc)) from exc


@router.post("/runs", status_code=201)
def create_run(body: dict) -> Run:
    scenario_id = body.get("scenarioId")
    if not isinstance(scenario_id, str) or not scenario_id:
        raise ApiError(ErrorCode.VALIDATION_ERROR,
                       "body must include 'scenarioId' (string)")
    if scenario_id != SCENARIO_ID:
        raise ApiError(ErrorCode.SCENARIO_NOT_FOUND,
                       f"scenario '{scenario_id}' is not available in the MVP")
    seed = body.get("seed")
    if seed is not None and not isinstance(seed, int):
        raise ApiError(ErrorCode.VALIDATION_ERROR, "'seed' must be an integer")

    scenario = load_default_scenario()
    seed = seed if seed is not None else scenario.seed
    run = Run(
        id=new_id("run"),
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        seed=seed,
        status=RunStatus.RUNNING,
        created_at=now_utc(),
        started_at=now_utc(),
    )
    try:
        record = execute_run(scenario, [r.source for r, _ in load_default_rules()], run)
    except Exception as exc:
        failed = run.model_copy(update={
            "status": RunStatus.FAILED,
            "completed_at": now_utc(),
            "error": f"run execution failed: {type(exc).__name__}",
        })
        repository.save_run(RunRecord(run=failed, scenario=scenario))
        raise ApiError(ErrorCode.INTERNAL_ERROR,
                       "run execution failed; the failed run state is preserved") from exc

    completed = record.run.model_copy(update={
        "status": RunStatus.COMPLETED,
        "completed_at": now_utc(),
    })
    repository.save_run(RunRecord(
        run=completed, scenario=record.scenario, events=record.events,
        rules=record.rules, matches=record.matches, coverage=record.coverage,
    ))
    return completed


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> Run:
    return _get_record(run_id).run


@router.get("/runs/{run_id}/graph")
def get_run_graph(run_id: str) -> dict:
    record = _get_record(run_id)
    assert record.coverage is not None
    stages = []
    for stage in record.scenario.stages:
        result = next(r for r in record.coverage.stages if r.stage_id == stage.id)
        stages.append({
            "stageId": stage.id,
            "name": stage.name,
            "status": result.status.value,
            "detectionLatencyMs": result.detection_latency_ms,
            "matchedRuleIds": result.matched_rule_ids,
        })
    return {"runId": record.run.id, "scenarioId": record.scenario.id, "stages": stages}


@router.get("/runs/{run_id}/telemetry")
def get_run_telemetry(
    run_id: str,
    stage: str | None = Query(default=None),
    source: str | None = Query(default=None),
    expected: bool | None = Query(default=None),
) -> dict:
    record = _get_record(run_id)
    events = record.events
    if stage is not None:
        events = [e for e in events if e.stage_id == stage]
    if source is not None:
        events = [e for e in events if e.source == source]
    if expected is not None:
        events = [e for e in events if e.expected == expected]
    return {"runId": record.run.id, "total": len(events), "events": events}


@router.get("/runs/{run_id}/rules")
def get_run_rules(run_id: str) -> dict:
    record = _get_record(run_id)
    return {"runId": record.run.id, "rules": record.rules}


@router.get("/runs/{run_id}/stages/{stage_id}")
def get_run_stage(run_id: str, stage_id: str) -> StageDetail:
    record = _get_record(run_id)
    stage = next((s for s in record.scenario.stages if s.id == stage_id), None)
    if stage is None:
        raise ApiError(ErrorCode.NOT_FOUND,
                       f"stage '{stage_id}' does not exist in scenario '{record.scenario.id}'")
    assert record.coverage is not None
    result = next(r for r in record.coverage.stages if r.stage_id == stage_id)
    return StageDetail(
        run_id=record.run.id,
        stage_id=stage_id,
        name=stage.name,
        description=stage.description,
        result=result,
        events=[e for e in record.events if e.stage_id == stage_id],
    )


@router.get("/runs/{run_id}/coverage")
def get_run_coverage(run_id: str):
    record = _get_record(run_id)
    assert record.coverage is not None
    return record.coverage


@router.get("/runs/{run_id}/matches")
def get_run_matches(run_id: str) -> dict:
    """Return all deterministic event-to-rule match records."""
    record = _get_record(run_id)
    return {"runId": record.run.id, "total": len(record.matches), "matches": record.matches}


@router.get("/runs/{run_id}/variants")
def get_run_variants(run_id: str) -> dict:
    """Evaluate detection rules across all behavioral scenario variants."""
    record = _get_record(run_id)
    assert record.coverage is not None
    variant_summaries = [
        evaluate_variant(var_id, record.rules, record.scenario, run_id)
        for var_id in VARIANTS
    ]
    resilience = calculate_variant_resilience(record.coverage.score, variant_summaries)
    return {
        "runId": record.run.id,
        "variantResilience": resilience,
        "variants": variant_summaries,
    }


@router.get("/runs/{run_id}/detection-ops")
def get_run_detection_ops(run_id: str) -> DetectionOpsMetrics:
    """Get the 4-tier DetectionOps metrics compared to the committed baseline."""
    record = _get_record(run_id)
    assert record.coverage is not None
    baseline = _committed_baseline(record)
    return compute_detection_ops_metrics(
        run_id=record.run.id,
        rules=record.rules,
        scenario=record.scenario,
        coverage=record.coverage,
        baseline_coverage=baseline.attack_coverage,
    )


@router.post("/runs/{run_id}/regression-analysis")
def post_run_regression_analysis(run_id: str, body: dict | None = None) -> RegressionAnalysisResult:
    """Compare candidate run coverage against a baseline run or committed baseline."""
    candidate_record = _get_record(run_id)
    assert candidate_record.coverage is not None

    baseline_run_id = (body or {}).get("baselineRunId")
    if baseline_run_id:
        baseline_record = _get_record(baseline_run_id)
        assert baseline_record.coverage is not None
        baseline_score = baseline_record.coverage.score
    else:
        baseline = _committed_baseline(candidate_record)
        baseline_run_id = f"committed-baseline:{baseline.scenario_id}"
        baseline_score = baseline.attack_coverage

    return analyze_regression(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_record.run.id,
        baseline_coverage=baseline_score,
        candidate_coverage=candidate_record.coverage.score,
    )


@router.get("/runs/{run_id}/ci-report")
def get_run_ci_report(run_id: str) -> dict:
    """Export the DetectionOps gate decision as GitHub Actions Markdown."""
    record = _get_record(run_id)
    assert record.coverage is not None
    baseline = _committed_baseline(record)
    metrics = compute_detection_ops_metrics(
        run_id=record.run.id,
        rules=record.rules,
        scenario=record.scenario,
        coverage=record.coverage,
        baseline_coverage=baseline.attack_coverage,
    )
    gate = evaluate_gate(metrics, baseline)
    markdown = generate_ci_report_markdown(record.scenario, metrics, gate=gate)
    return {
        "runId": record.run.id,
        "scenarioId": record.scenario.id,
        "decision": "PASS" if gate.status == "pass" else "BLOCKED",
        "gate": gate.model_dump(mode="json", by_alias=True),
        "markdown": markdown,
    }