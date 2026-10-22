"""Run lifecycle endpoints: create, inspect, graph, telemetry, coverage.

Orchestration lives here (per CLAUDE.md: api/ = validation and orchestration);
all authoritative computation lives in domain/.
"""

from fastapi import APIRouter, Query

from app.api.pipeline import execute_run
from app.domain.detections.loader import load_default_rules
from app.domain.detections.models import StageResult
from app.domain.scenarios.loader import SCENARIO_ID, load_default_scenario
from app.domain.scenarios.models import ContractModel
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