"""Run model. Shape mirrors packages/schemas/json/run.schema.json."""

from datetime import UTC, datetime

from pydantic import field_serializer

from app.domain.scenarios.models import ContractModel
from app.domain.telemetry.models import iso_z
from app.shared.vocab import RunStatus


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