"""Rule-proposal endpoints: create, generate (Nemotron/fallback), validate, list.

The proposal flow is deterministic: parsing and before/after evaluation are
done by the local engine (app.api.pipeline.validate_proposal). Nemotron
produces proposed Sigma YAML; whether a proposal improves coverage is decided
by the local evaluator alone.

The stored original rule is never modified by a proposal.
"""

from fastapi import APIRouter

from app.ai.client import propose_rule_with_nemotron
from app.api.pipeline import validate_proposal
from app.domain.detections.parser import parse_rule
from app.persistence.instance import repository
from app.persistence.models import AIArtifact, ProposalValidation, RuleProposal, now_utc
from app.shared.errors import ApiError, ErrorCode
from app.shared.ids import new_id

router = APIRouter(prefix="/api", tags=["proposals"])


def _get_record_or_404(run_id: str):
    record = repository.get_run(run_id)
    if record is None:
        raise ApiError(ErrorCode.RUN_NOT_FOUND, f"run '{run_id}' does not exist")
    return record


@router.post("/runs/{run_id}/rule-proposals", status_code=201)
def create_proposal(run_id: str, body: dict) -> RuleProposal:
    _get_record_or_404(run_id)

    original_rule_id = body.get("originalRuleId")
    if not isinstance(original_rule_id, str) or not original_rule_id:
        raise ApiError(ErrorCode.VALIDATION_ERROR,
                       "body must include 'originalRuleId' (string)")
    proposed_source = body.get("proposedSource")
    if not isinstance(proposed_source, str) or not proposed_source.strip():
        raise ApiError(ErrorCode.VALIDATION_ERROR,
                       "body must include 'proposedSource' (non-empty YAML string)")
    rationale = body.get("rationale", "")
    if not isinstance(rationale, str):
        raise ApiError(ErrorCode.VALIDATION_ERROR, "'rationale' must be a string")

    # Parse immediately so parser errors surface at creation time.
    parsed, _ = parse_rule(proposed_source)
    status = "proposed" if parsed.parser_status == "valid" else "rejected"

    proposal = RuleProposal(
        id=new_id("prop"),
        run_id=run_id,
        original_rule_id=original_rule_id,
        proposed_source=proposed_source,
        rationale=rationale,
        status=status,
        validation=ProposalValidation(
            parser_status=parsed.parser_status,
            parser_errors=parsed.parser_errors,
        ),
        created_at=now_utc(),
    )
    repository.save_proposal(proposal)
    return proposal


@router.post("/runs/{run_id}/rule-proposals/generate", status_code=201)
@router.post("/runs/{run_id}/rule-proposals/ai-generate", status_code=201)
def generate_proposal_endpoint(run_id: str, body: dict) -> dict:
    record = _get_record_or_404(run_id)

    original_rule_id = body.get("originalRuleId")
    if not isinstance(original_rule_id, str) or not original_rule_id:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            "body must include 'originalRuleId' (string)",
        )

    original_rule = next((r for r in record.rules if r.id == original_rule_id), None)
    if original_rule is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"rule '{original_rule_id}' not found in run rules")

    stage_id = original_rule.stage_id
    scenario_stage = next((s for s in record.scenario.stages if s.id == stage_id), None)
    stage_name = scenario_stage.name if scenario_stage else stage_id

    # Find stage result mismatches
    stage_result = (
        next((r for r in record.coverage.stages if r.stage_id == stage_id), None)
        if record.coverage
        else None
    )
    stage_mismatches = (
        [m for m in stage_result.mismatches if m.rule_id == original_rule_id]
        if stage_result
        else []
    )

    # Find relevant mismatched event
    event_id = body.get("eventId")
    mismatched_event = None
    if isinstance(event_id, str) and event_id:
        mismatched_event = next((e for e in record.events if e.id == event_id), None)
    elif stage_mismatches:
        mismatched_event = next(
            (e for e in record.events if e.id == stage_mismatches[0].event_id), None
        )

    if mismatched_event is None:
        mismatched_event = next((e for e in record.events if e.stage_id == stage_id), None)

    if mismatched_event is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"no telemetry events found for stage '{stage_id}'")

    ai_result = propose_rule_with_nemotron(
        stage_id=stage_id,
        stage_name=stage_name,
        original_rule=original_rule.model_dump(mode="json"),
        mismatched_event=mismatched_event.model_dump(mode="json"),
        mismatches=[m.model_dump(mode="json") for m in stage_mismatches],
    )

    proposed_source = ai_result["proposed_source"]
    rationale = ai_result["rationale"]

    parsed, _ = parse_rule(proposed_source)
    status = "proposed" if parsed.parser_status == "valid" else "rejected"

    proposal_id = new_id("prop")
    proposal = RuleProposal(
        id=proposal_id,
        run_id=run_id,
        original_rule_id=original_rule_id,
        proposed_source=proposed_source,
        rationale=rationale,
        status=status,
        validation=ProposalValidation(
            parser_status=parsed.parser_status,
            parser_errors=parsed.parser_errors,
        ),
        created_at=now_utc(),
    )
    repository.save_proposal(proposal)

    artifact_id = new_id("ai_prop")
    artifact = AIArtifact(
        id=artifact_id,
        run_id=run_id,
        stage_id=stage_id,
        task_type="rule_proposal",
        status=ai_result["status"],
        model=ai_result["model"],
        input_evidence_ids=ai_result["input_evidence_ids"],
        output={
            "proposalId": proposal_id,
            "originalRuleId": original_rule_id,
            "proposedSource": proposed_source,
            "rationale": rationale,
            "citedEvidenceIds": ai_result["cited_evidence_ids"],
            "referencedEvidenceIds": ai_result.get("referenced_evidence_ids", ai_result["cited_evidence_ids"]),
            "isDeterministicFallback": ai_result.get("is_deterministic_fallback", False),
        },
        validation_errors=[],
        created_at=now_utc(),
    )
    repository.save_ai_artifact(artifact)

    return {
        **proposal.model_dump(mode="json", by_alias=True),
        "aiArtifact": artifact.model_dump(mode="json", by_alias=True),
    }


@router.post("/runs/{run_id}/rule-proposals/{proposal_id}/validate")
def validate_proposal_endpoint(
    run_id: str,
    proposal_id: str,
    cumulative: bool = False,
) -> RuleProposal:
    record = _get_record_or_404(run_id)
    proposal = repository.get_proposal(run_id, proposal_id)
    if proposal is None:
        raise ApiError(ErrorCode.NOT_FOUND,
                       f"proposal '{proposal_id}' does not exist for run '{run_id}'")

    prior = None
    if cumulative:
        all_proposals = repository.list_proposals(run_id)
        prior = [
            (p.original_rule_id, p.proposed_source)
            for p in all_proposals
            if p.id != proposal_id
            and p.status == "validated"
            and p.validation.improves_coverage is True
        ]

    improves, before, after = validate_proposal(
        record,
        proposal.original_rule_id,
        proposal.proposed_source,
        prior_improvements=prior,
    )
    updated = proposal.model_copy(update={
        "status": "validated",
        "validation": proposal.validation.model_copy(update={
            "improves_coverage": improves,
            "coverage_before": before,
            "coverage_after": after,
        }),
    })
    repository.save_proposal(updated)
    return updated


@router.get("/runs/{run_id}/rule-proposals")
def list_proposals(run_id: str) -> dict:
    _get_record_or_404(run_id)
    proposals = repository.list_proposals(run_id)
    return {"runId": run_id, "proposals": proposals}