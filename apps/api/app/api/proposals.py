"""Rule-proposal endpoints: create, validate, list.

The proposal flow is deterministic: parsing and before/after evaluation are
done by the local engine (app.api.pipeline.validate_proposal). No model is
involved here — Nemotron only ever *produces* proposed YAML (days 7-8);
whether a proposal improves coverage is decided by this code alone.

The stored original rule is never modified by a proposal.
"""

from fastapi import APIRouter

from app.api.pipeline import validate_proposal
from app.persistence.instance import repository
from app.persistence.models import ProposalValidation, RuleProposal, now_utc
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
    from app.domain.detections.parser import parse_rule
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


@router.post("/runs/{run_id}/rule-proposals/{proposal_id}/validate")
def validate_proposal_endpoint(run_id: str, proposal_id: str) -> RuleProposal:
    record = _get_record_or_404(run_id)
    proposal = repository.get_proposal(run_id, proposal_id)
    if proposal is None:
        raise ApiError(ErrorCode.NOT_FOUND,
                       f"proposal '{proposal_id}' does not exist for run '{run_id}'")

    improves, before, after = validate_proposal(
        record, proposal.original_rule_id, proposal.proposed_source
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