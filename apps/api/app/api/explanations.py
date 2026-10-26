"""AI Explanation endpoint: POST /api/runs/{run_id}/explanations."""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.ai.client import explain_stage_with_nemotron
from app.domain.telemetry.models import iso_z
from app.persistence.instance import repository
from app.shared.errors import ApiError, ErrorCode
from app.shared.ids import new_id

router = APIRouter(prefix="/api", tags=["explanations"])


def _describe_evidence(
    evidence_id: str, event_index: dict, rule_index: dict, stage_id: str
) -> str:
    event = event_index.get(evidence_id)
    if event is not None:
        identity = event.get("identity") or {}
        resource = event.get("resource") or {}
        return (
            f"{event.get('action', 'event')} by "
            f"{identity.get('id', 'unknown identity')} on "
            f"{resource.get('id', 'unknown resource')}."
        )

    rule = rule_index.get(evidence_id)
    if rule is not None:
        return f"Rule '{rule.get('title', rule.get('id'))}' evaluated for {stage_id}."
    return "Evidence supplied to this analysis."


@router.post("/runs/{run_id}/explanations", status_code=200)
def create_stage_explanation(run_id: str, body: dict) -> dict:
    record = repository.get_run(run_id)
    if record is None:
        raise ApiError(ErrorCode.RUN_NOT_FOUND, f"run '{run_id}' does not exist")

    stage_id = body.get("stageId")
    if not isinstance(stage_id, str) or not stage_id:
        raise ApiError(ErrorCode.VALIDATION_ERROR, "body must include 'stageId' (string)")

    scenario_stage = next((s for s in record.scenario.stages if s.id == stage_id), None)
    if scenario_stage is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"stage '{stage_id}' not found in scenario")

    assert record.coverage is not None
    stage_result = next((r for r in record.coverage.stages if r.stage_id == stage_id), None)
    if stage_result is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"stage '{stage_id}' results not found in run coverage")

    stage_events = [e.model_dump(mode="json") for e in record.events if e.stage_id == stage_id]
    stage_rules = [r.model_dump(mode="json") for r in record.rules if r.stage_id == stage_id]
    mismatches = [m.model_dump(mode="json") for m in stage_result.mismatches]

    ai_result = explain_stage_with_nemotron(
        stage_id=stage_id,
        stage_name=scenario_stage.name,
        status=stage_result.status.value,
        events=stage_events,
        rules=stage_rules,
        mismatches=mismatches,
    )

    event_index = {f"event:{event.get('id')}": event for event in stage_events}
    rule_index = {f"rule:{rule.get('id')}": rule for rule in stage_rules}
    cited_evidence_ids = ai_result["cited_evidence_ids"]

    return {
        "id": new_id("ai_exp"),
        "runId": run_id,
        "stageId": stage_id,
        "taskType": "explanation",
        "status": ai_result["status"],
        "model": ai_result["model"],
        # inputEvidenceIds is the evidence supplied to the analysis, not the
        # model's citations. The output citations live in evidenceObserved.
        "inputEvidenceIds": ai_result["input_evidence_ids"],
        "explanation": {
            "summary": ai_result["summary"],
            "stageName": scenario_stage.name,
            "status": stage_result.status.value,
            "evidenceObserved": [
                {
                    "evidenceId": cid,
                    "description": _describe_evidence(
                        cid, event_index, rule_index, stage_id
                    ),
                }
                for cid in cited_evidence_ids
            ],
            "gapAnalysis": ai_result["gap_analysis"],
            "recommendedRemediation": ai_result["recommended_remediation"],
            "assumptions": [
                "Analysis strictly grounded in synthetic cloud audit telemetry",
                "Deterministic rule evaluator results are authoritative",
            ],
        },
        "createdAt": iso_z(datetime.now(UTC)),
    }
