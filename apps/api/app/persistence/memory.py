"""In-memory persistence for the deterministic slice.

STATUS (handoff note): this is a demo repository, NOT durable storage. All run
state lives in process memory and resets when the backend restarts. The
repository interface is intentionally narrow so a SQLite/PostgreSQL
implementation can replace it without touching domain or API code.
"""

from dataclasses import dataclass, field

from app.domain.coverage.models import CoverageResult
from app.domain.detections.models import DetectionRule, RuleMatch
from app.domain.scenarios.models import Scenario
from app.domain.telemetry.models import TelemetryEvent
from app.persistence.models import Run


@dataclass
class RunRecord:
    run: Run
    scenario: Scenario
    events: list[TelemetryEvent] = field(default_factory=list)
    rules: list[DetectionRule] = field(default_factory=list)
    matches: list[RuleMatch] = field(default_factory=list)
    coverage: CoverageResult | None = None


class MemoryRepository:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    # --- runs ---
    def save_run(self, record: RunRecord) -> None:
        self._runs[record.run.id] = record

    def get_run(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[RunRecord]:
        return sorted(self._runs.values(), key=lambda r: r.run.created_at)


repository = MemoryRepository()