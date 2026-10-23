"""Run report model. Shape mirrors packages/schemas/json/report.schema.json."""

from datetime import datetime

from pydantic import field_serializer

from app.domain.coverage.models import CoverageResult
from app.domain.scenarios.models import ContractModel
from app.domain.telemetry.models import iso_z


class ReportScenario(ContractModel):
    id: str
    name: str
    version: str


class ReportImprovement(ContractModel):
    proposal_id: str
    original_rule_id: str
    improves_coverage: bool
    coverage_before: float
    coverage_after: float


class RunReport(ContractModel):
    run_id: str
    scenario: ReportScenario
    seed: int
    generated_at: datetime
    coverage: CoverageResult
    improvements: list[ReportImprovement]
    assumptions: list[str]
    limitations: list[str]
    ai_summary: dict | None = None  # AiArtifact payload (days 7-8); null = unavailable

    @field_serializer("generated_at", when_used="json")
    def _serialize_generated_at(self, value: datetime) -> str:
        return iso_z(value)