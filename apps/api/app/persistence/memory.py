"""In-memory persistence for tests and throwaway demos.

STATUS: non-durable by design — all state dies with the process. Use
DATABASE_URL=memory:// explicitly. Production/demo default is SQLite via
app.persistence.repository.make_repository.
"""

from app.persistence.models import RuleProposal
from app.persistence.repository import RunRecord


class MemoryRepository:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._proposals: dict[tuple[str, str], RuleProposal] = {}

    # --- runs ---
    def save_run(self, record: RunRecord) -> None:
        self._runs[record.run.id] = record

    def get_run(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[RunRecord]:
        return sorted(self._runs.values(), key=lambda r: r.run.created_at)

    def clear(self) -> None:
        self._runs.clear()
        self._proposals.clear()

    # --- proposals ---
    def save_proposal(self, proposal: RuleProposal) -> None:
        self._proposals[(proposal.run_id, proposal.id)] = proposal

    def get_proposal(self, run_id: str, proposal_id: str) -> RuleProposal | None:
        return self._proposals.get((run_id, proposal_id))

    def list_proposals(self, run_id: str) -> list[RuleProposal]:
        return sorted(
            (p for (rid, _), p in self._proposals.items() if rid == run_id),
            key=lambda p: p.created_at,
        )


__all__ = ["MemoryRepository", "RunRecord"]