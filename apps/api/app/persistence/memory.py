"""In-memory persistence for tests and throwaway demos.

STATUS: non-durable by design — all state dies with the process. Use
DATABASE_URL=memory:// explicitly. Production/demo default is SQLite via
app.persistence.repository.make_repository.
"""

from app.persistence.repository import RunRecord


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

    def clear(self) -> None:
        self._runs.clear()


__all__ = ["MemoryRepository", "RunRecord"]