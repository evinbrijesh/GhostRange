"""Detection rule and match models. Shapes mirror packages/schemas."""

from datetime import datetime
from typing import Any

from pydantic import field_serializer

from app.domain.scenarios.models import ContractModel
from app.domain.telemetry.models import iso_z
from app.shared.vocab import EventSource, ParserStatus, RuleLevel, StageStatus


class LogSource(ContractModel):
    product: str
    service: EventSource


class DetectionRule(ContractModel):
    id: str
    version: str
    title: str
    stage_id: str
    logsource: LogSource
    source: str
    parser_status: ParserStatus
    parser_errors: list[str]
    level: RuleLevel | None = None
    enabled: bool = True


class RuleMatch(ContractModel):
    id: str
    run_id: str
    event_id: str
    rule_id: str
    stage_id: str
    matched_at: datetime
    details: dict[str, Any]

    @field_serializer("matched_at", when_used="json")
    def _serialize_matched_at(self, value: datetime) -> str:
        return iso_z(value)


class StageResult(ContractModel):
    stage_id: str
    status: StageStatus
    expected_event_ids: list[str]
    matched_event_ids: list[str]
    matched_rule_ids: list[str]
    detection_latency_ms: int | None = None
    evidence_ids: list[str]
    errors: list[str]


__all__ = ["DetectionRule", "LogSource", "RuleMatch", "StageStatus"]