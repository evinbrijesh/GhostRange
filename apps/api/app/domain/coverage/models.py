"""Coverage models. Shapes mirror packages/schemas."""

from pydantic import Field

from app.domain.detections.models import StageResult
from app.domain.scenarios.models import ContractModel


class CoverageResult(ContractModel):
    run_id: str
    score: float = Field(ge=0, le=100)
    stage_counts: dict[str, int]
    stages: list[StageResult]
    formula_version: str
    evaluator_errors: list[str]