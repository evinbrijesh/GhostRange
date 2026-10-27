"""Standalone rule validation and playground evaluation endpoints.

Per Master Prompt:
POST /api/rules/validate
POST /api/rules/evaluate
"""

from fastapi import APIRouter
from pydantic import Field

from app.domain.detections.evaluator import _evaluate_selection, flatten_event
from app.domain.detections.parser import parse_rule
from app.domain.scenarios.loader import load_default_scenario
from app.domain.scenarios.models import ContractModel
from app.domain.simulation.benign import generate_benign_corpus
from app.domain.simulation.engine import generate_telemetry
from app.persistence.instance import repository
from app.shared.errors import ApiError, ErrorCode

router = APIRouter(prefix="/api/rules", tags=["rules"])


class ValidateRuleRequest(ContractModel):
    yaml_source: str = Field(..., alias="yamlSource")


class ValidateRuleResponse(ContractModel):
    valid: bool
    rule_id: str | None = None
    title: str | None = None
    stage_id: str | None = None
    level: str | None = None
    errors: list[str] = Field(default_factory=list)


class EvaluateRuleRequest(ContractModel):
    yaml_source: str = Field(..., alias="yamlSource")
    run_id: str | None = Field(default=None, alias="runId")


class EvaluateRuleResponse(ContractModel):
    valid: bool
    rule_id: str
    title: str
    stage_id: str
    attack_matches_count: int
    attack_matches: list[dict]
    noise_hits_count: int
    noise_hits: list[dict]
    benign_suppressed: bool
    errors: list[str] = Field(default_factory=list)


@router.post("/validate")
def validate_rule_syntax(payload: ValidateRuleRequest) -> ValidateRuleResponse:
    """Validate standalone Sigma YAML syntax against GhostRange specifications."""
    rule, _selection = parse_rule(payload.yaml_source)
    if rule.parser_status == "valid":
        return ValidateRuleResponse(
            valid=True,
            rule_id=rule.id,
            title=rule.title,
            stage_id=rule.stage_id,
            level=rule.level.value if rule.level else None,
            errors=[],
        )
    return ValidateRuleResponse(
        valid=False,
        rule_id=rule.id if rule.id != "rule_unparsed" else None,
        title=None,
        stage_id=None,
        level=None,
        errors=rule.parser_errors,
    )


@router.post("/evaluate")
def evaluate_rule_standalone(payload: EvaluateRuleRequest) -> EvaluateRuleResponse:
    """Evaluate a candidate rule against attack telemetry and the benign noise corpus."""
    rule, selection = parse_rule(payload.yaml_source)
    if rule.parser_status != "valid":
        raise ApiError(ErrorCode.VALIDATION_ERROR, f"Rule syntax invalid: {', '.join(rule.parser_errors)}")

    # Get attack events from specified run or generate fresh baseline
    if payload.run_id:
        record = repository.get_run(payload.run_id)
        if record is None:
            raise ApiError(ErrorCode.RUN_NOT_FOUND, f"Run '{payload.run_id}' not found")
        attack_events = record.events
    else:
        scenario = load_default_scenario()
        attack_events = generate_telemetry(scenario, "eval-scratch", scenario.seed)

    # Evaluate against attack events
    attack_matches: list[dict] = []
    for event in attack_events:
        if rule.logsource.service != event.source:
            continue
        flat = flatten_event(event)
        matched, matched_details, _failed = _evaluate_selection(selection, flat)
        if matched:
            attack_matches.append({
                "eventId": event.id,
                "stageId": event.stage_id,
                "action": event.action,
                "identity": event.identity.id,
                "resource": event.resource.id,
                "srcIp": event.src_ip,
                "expected": event.expected,
                "matchedFields": matched_details,
            })

    # Evaluate against benign noise corpus
    benign_events = generate_benign_corpus()
    noise_hits: list[dict] = []
    for event in benign_events:
        if rule.logsource.service != event.source:
            continue
        flat = flatten_event(event)
        matched, matched_details, _failed = _evaluate_selection(selection, flat)
        if matched:
            noise_hits.append({
                "eventId": event.id,
                "action": event.action,
                "identity": event.identity.id,
                "resource": event.resource.id,
                "srcIp": event.src_ip,
                "matchedFields": matched_details,
            })

    return EvaluateRuleResponse(
        valid=True,
        rule_id=rule.id,
        title=rule.title,
        stage_id=rule.stage_id,
        attack_matches_count=len(attack_matches),
        attack_matches=attack_matches,
        noise_hits_count=len(noise_hits),
        noise_hits=noise_hits,
        benign_suppressed=len(noise_hits) == 0,
        errors=[],
    )
