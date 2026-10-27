"""In-memory persistence for tests and throwaway demos.

STATUS: non-durable by design — all state dies with the process. Use
DATABASE_URL=memory:// explicitly. Production/demo default is SQLite via
app.persistence.repository.make_repository.
"""

from app.persistence.models import AIArtifact, RuleProposal
from app.persistence.repository import RunRecord


class MemoryRepository:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._proposals: dict[tuple[str, str], RuleProposal] = {}
        self._ai_artifacts: dict[tuple[str, str], AIArtifact] = {}

    # --- runs ---
    def save_run(self, record: RunRecord) -> None:
        self._runs[record.run.id] = record
        self.clear_proposals(record.run.id)
        self.clear_ai_artifacts(record.run.id)

    def get_run(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[RunRecord]:
        return sorted(self._runs.values(), key=lambda r: r.run.created_at)

    def clear(self) -> None:
        self._runs.clear()
        self._proposals.clear()
        self._ai_artifacts.clear()

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

    def clear_proposals(self, run_id: str) -> None:
        self._proposals = {
            k: v for k, v in self._proposals.items() if k[0] != run_id
        }

    # --- AI artifacts ---
    def save_ai_artifact(self, artifact: AIArtifact) -> None:
        self._ai_artifacts[(artifact.run_id, artifact.id)] = artifact

    def get_ai_artifact(self, run_id: str, artifact_id: str) -> AIArtifact | None:
        return self._ai_artifacts.get((run_id, artifact_id))

    def list_ai_artifacts(self, run_id: str, task_type: str | None = None) -> list[AIArtifact]:
        items = [
            a for (rid, _), a in self._ai_artifacts.items()
            if rid == run_id and (task_type is None or a.task_type == task_type)
        ]
        return sorted(items, key=lambda a: a.created_at)

    def clear_ai_artifacts(self, run_id: str) -> None:
        self._ai_artifacts = {
            k: v for k, v in self._ai_artifacts.items() if k[0] != run_id
        }


__all__ = ["MemoryRepository", "RunRecord"]