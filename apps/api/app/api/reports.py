"""Report endpoints: structured run report and AI executive summary."""

from fastapi import APIRouter

from app.ai.client import summarize_report_with_nemotron
from app.domain.reports.builder import build_report
from app.persistence.instance import repository
from app.persistence.models import AIArtifact, now_utc
from app.shared.errors import ApiError, ErrorCode
from app.shared.ids import new_id

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/runs/{run_id}/report")
def get_run_report(run_id: str):
    record = repository.get_run(run_id)
    if record is None:
        raise ApiError(ErrorCode.RUN_NOT_FOUND, f"run '{run_id}' does not exist")
    proposals = repository.list_proposals(run_id)
    artifacts = repository.list_ai_artifacts(run_id, task_type="report_summary")
    ai_summary = artifacts[-1].model_dump(mode="json", by_alias=True) if artifacts else None
    if ai_summary and artifacts:
        latest_artifact = artifacts[-1]
        validated_proposals = [
            p for p in proposals
            if p.status == "validated" and p.validation.improves_coverage is True
        ]
        is_stale = any(
            (p.validation.validated_at or p.created_at) > latest_artifact.created_at
            for p in validated_proposals
        )
        ai_summary["isStale"] = is_stale
        if is_stale:
            ai_summary["staleReason"] = (
                "New rule proposals were validated after this executive summary was generated. "
                "Regenerate for updated coverage metrics."
            )
    return build_report(record, proposals, ai_summary=ai_summary)


@router.post("/runs/{run_id}/report/summary")
def generate_run_report_summary(run_id: str):
    record = repository.get_run(run_id)
    if record is None:
        raise ApiError(ErrorCode.RUN_NOT_FOUND, f"run '{run_id}' does not exist")
    proposals = repository.list_proposals(run_id)

    assert record.coverage is not None
    improvements = [
        {
            "proposal_id": p.id,
            "original_rule_id": p.original_rule_id,
            "coverage_before": p.validation.coverage_before,
            "coverage_after": p.validation.coverage_after,
        }
        for p in proposals
        if p.status == "validated" and p.validation.improves_coverage is True
    ]
    scenario_stages = {s.id: s for s in record.scenario.stages}
    stage_results = [
        {
            "stage_id": s.stage_id,
            "status": s.status.value,
            "weight": scenario_stages[s.stage_id].weight if s.stage_id in scenario_stages else 0.15,
            "errors": s.errors,
        }
        for s in record.coverage.stages
    ]

    ai_result = summarize_report_with_nemotron(
        scenario_name=record.scenario.name,
        scenario_version=record.scenario.version,
        run_id=record.run.id,
        seed=record.run.seed,
        coverage_score=record.coverage.score,
        formula_version=record.coverage.formula_version,
        stage_results=stage_results,
        improvements=improvements,
    )

    artifact_id = new_id("ai_sum")
    artifact = AIArtifact(
        id=artifact_id,
        run_id=run_id,
        stage_id=None,
        task_type="report_summary",
        status=ai_result["status"],
        model=ai_result["model"],
        input_evidence_ids=ai_result["input_evidence_ids"],
        output={
            "executiveSummary": ai_result["executive_summary"],
            "attackNarrative": ai_result["attack_narrative"],
            "detectionGaps": ai_result["detection_gaps"],
            "remediationImpact": ai_result["remediation_impact"],
            "recommendations": ai_result["recommendations"],
            "citedEvidenceIds": ai_result["cited_evidence_ids"],
            "referencedEvidenceIds": ai_result.get("referenced_evidence_ids", ai_result["cited_evidence_ids"]),
            "isDeterministicFallback": ai_result.get("is_deterministic_fallback", False),
        },
        validation_errors=[],
        created_at=now_utc(),
    )
    repository.save_ai_artifact(artifact)

    return build_report(record, proposals, ai_summary=artifact.model_dump(mode="json", by_alias=True))