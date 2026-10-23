"""Run and proposal models. Shapes mirror packages/schemas/json/*.schema.json."""

from datetime import UTC, datetime

from pydantic import Field, field_serializer

from app.domain.scenarios.models import ContractModel
from app.domain.telemetry.models import iso_z
from app.shared.vocab import ParserStatus, RunStatus


def now_utc() -> datetime:
    return datetime.now(UTC)


class Run(ContractModel):
    id: str
    scenario_id: str
    scenario_version: str
    seed: int
    status: RunStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    @field_serializer("created_at", "started_at", "completed_at", when_used="json")
    def _serialize_datetimes(self, value: datetime | None) -> str | None:
        return iso_z(value) if value is not None else None


class ProposalValidation(ContractModel):
    """Validation block of a rule proposal. improvesCoverage stays null until
    the deterministic evaluator has compared before/after coverage."""

    parser_status: ParserStatus
    parser_errors: list[str] = Field(default_factory=list)
    improves_coverage: bool | None = None
    coverage_before: float | None = None
    coverage_after: float | None = None


class RuleProposal(ContractModel):
    id: str
    run_id: str
    original_rule_id: str
    proposed_source: str
    rationale: str = ""
    status: str = "proposed"  # proposed | validated | rejected | accepted
    validation: ProposalValidation
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def _serialize_created_at(self, value: datetime) -> str:
        return iso_z(value)