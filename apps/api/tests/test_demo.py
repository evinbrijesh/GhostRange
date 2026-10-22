"""Demo CLI: seed idempotency, reset idempotency, seed-after-reset."""

from app.demo import DEMO_RUN_ID, reset, seed
from app.persistence.memory import MemoryRepository


def test_seed_creates_demo_run() -> None:
    repo = MemoryRepository()
    seed(repo)
    record = repo.get_run(DEMO_RUN_ID)
    assert record is not None
    assert record.run.id == DEMO_RUN_ID
    assert record.run.status == "completed"
    assert record.coverage is not None
    assert record.coverage.score == 50.0


def test_seed_is_idempotent() -> None:
    repo = MemoryRepository()
    first = seed(repo)
    second = seed(repo)
    assert first.id == second.id == DEMO_RUN_ID
    assert len(repo.list_runs()) == 1  # upsert, never duplicate
    a = repo.get_run(DEMO_RUN_ID)
    b = repo.get_run(DEMO_RUN_ID)
    assert a is not None and b is not None
    # Deterministic payload: same seed -> same events, matches, coverage.
    assert [e.id for e in a.events] == [e.id for e in b.events]
    assert a.coverage.score == b.coverage.score


def test_reset_clears_state() -> None:
    repo = MemoryRepository()
    seed(repo)
    assert len(repo.list_runs()) == 1
    reset(repo)
    assert repo.list_runs() == []
    assert repo.get_run(DEMO_RUN_ID) is None


def test_reset_is_idempotent() -> None:
    repo = MemoryRepository()
    reset(repo)
    reset(repo)
    assert repo.list_runs() == []


def test_seed_after_reset_works() -> None:
    repo = MemoryRepository()
    seed(repo)
    reset(repo)
    seed(repo)
    assert repo.get_run(DEMO_RUN_ID) is not None
