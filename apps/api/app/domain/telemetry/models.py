"""Normalized telemetry event models. Shapes mirror packages/schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_serializer

from app.domain.scenarios.models import ContractModel
from app.shared.vocab import EventSource


def iso_z(value: datetime) -> str:
    """Serialize a UTC datetime as ISO 8601 with a Z suffix (contract format)."""
    return value.isoformat().replace("+00:00", "Z")


class EventActor(ContractModel):
    id: str
    type: str


class TelemetryEvent(ContractModel):
    id: str
    run_id: str
    stage_id: str
    expected: bool = Field(
        description="True for events the stage's coverage check requires; false for background noise."
    )
    timestamp: datetime
    source: EventSource
    identity: EventActor
    action: str
    resource: EventActor
    src_ip: str
    attributes: dict[str, Any]
    synthetic: Literal[True] = True

    @field_serializer("timestamp", when_used="json")
    def _serialize_timestamp(self, value: datetime) -> str:
        return iso_z(value)