"""Repository interface and factory.

The API layer depends only on the RunRecord dataclass and the three methods
of the Repository protocol. Which implementation backs those methods is
decided here, from DATABASE_URL:

    sqlite:///./ghostrange.db -> SqliteRepository (durable, default)
    memory://                 -> MemoryRepository (tests, throwaway demos)

Swapping implementations must never require changes in domain/ or api/ code.
"""

from dataclasses import dataclass, field
from typing import Protocol

from app.domain.coverage.models import CoverageResult
from app.domain.detections.models import DetectionRule, RuleMatch
from app.domain.scenarios.models import Scenario
from app.domain.telemetry.models import TelemetryEvent
from app.persistence.models import RuleProposal, Run


@dataclass
class RunRecord:
    """Everything a run produced, plus the scenario it ran against."""
    run: Run
    scenario: Scenario
    events: list[TelemetryEvent] = field(default_factory=list)
    rules: list[DetectionRule] = field(default_factory=list)
    matches: list[RuleMatch] = field(default_factory=list)
    coverage: CoverageResult | None = None


class Repository(Protocol):
    def save_run(self, record: RunRecord) -> None: ...
    def get_run(self, run_id: str) -> RunRecord | None: ...
    def list_runs(self) -> list[RunRecord]: ...
    def clear(self) -> None: ...
    def save_proposal(self, proposal: RuleProposal) -> None: ...
    def get_proposal(self, run_id: str, proposal_id: str) -> RuleProposal | None: ...
    def list_proposals(self, run_id: str) -> list[RuleProposal]: ...


def make_repository(database_url: str):
    if database_url == "memory://":
        from app.persistence.memory import MemoryRepository
        return MemoryRepository()
    if database_url.startswith("sqlite:///"):
        from app.persistence.sqlite import SqliteRepository
        return SqliteRepository(database_url)
    raise ValueError(f"unsupported database URL: {database_url!r}")