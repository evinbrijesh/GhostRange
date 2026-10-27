"""SQLite persistence: roundtrip fidelity, parity with memory, idempotency.

The suite's app-level tests run on memory:// (see conftest.py); these tests
construct SqliteRepository directly against a temporary database file.
"""

from dataclasses import replace

import pytest

from app.api.pipeline import execute_run
from app.domain.detections.loader import load_default_rules
from app.domain.scenarios.loader import load_default_scenario
from app.persistence.database import resolve_sqlite_path
from app.persistence.memory import MemoryRepository
from app.persistence.models import AIArtifact, ProposalValidation, RuleProposal, Run, now_utc
from app.persistence.repository import RunRecord, make_repository
from app.persistence.sqlite import SqliteRepository
from app.shared.ids import new_id
from app.shared.vocab import ParserStatus, RunStatus


@pytest.fixture
def sqlite_url(tmp_path):
    # tmp_path is absolute, so this yields the four-slash absolute form.
    return f"sqlite:///{tmp_path}/test.db"


@pytest.fixture
def record():
    scenario = load_default_scenario()
    run = Run(
        id=new_id("run"), scenario_id=scenario.id, scenario_version=scenario.version,
        seed=scenario.seed, status=RunStatus.COMPLETED,
        created_at=now_utc(), started_at=now_utc(), completed_at=now_utc(),
    )
    return execute_run(scenario, [r.source for r, _ in load_default_rules()], run)


def _serialized(record: RunRecord) -> dict:
    return {
        "run": record.run.model_dump_json(by_alias=True),
        "events": [e.model_dump_json(by_alias=True) for e in record.events],
        "rules": [r.model_dump_json(by_alias=True) for r in record.rules],
        "matches": [m.model_dump_json(by_alias=True) for m in record.matches],
        "coverage": record.coverage.model_dump_json(by_alias=True) if record.coverage else None,
    }


def test_sqlite_roundtrip_preserves_every_field(sqlite_url, record) -> None:
    repo = SqliteRepository(sqlite_url)
    repo.save_run(record)
    loaded = repo.get_run(record.run.id)
    assert loaded is not None
    assert _serialized(loaded) == _serialized(record)


def test_sqlite_and_memory_store_identically(sqlite_url, record) -> None:
    sqlite_repo = SqliteRepository(sqlite_url)
    memory_repo = MemoryRepository()
    sqlite_repo.save_run(record)
    memory_repo.save_run(record)
    assert _serialized(sqlite_repo.get_run(record.run.id)) == \
        _serialized(memory_repo.get_run(record.run.id))


def test_get_missing_run_returns_none(sqlite_url) -> None:
    assert SqliteRepository(sqlite_url).get_run("run_missing") is None


def test_save_twice_upserts_without_duplicates(sqlite_url, record) -> None:
    repo = SqliteRepository(sqlite_url)
    repo.save_run(record)
    repo.save_run(record)
    loaded = repo.get_run(record.run.id)
    assert len(loaded.events) == len(record.events)
    assert len(loaded.matches) == len(record.matches)
    assert len(loaded.rules) == len(record.rules)


def test_list_runs_orders_by_created_at(sqlite_url, record) -> None:
    repo = SqliteRepository(sqlite_url)
    earlier = replace(record)
    later_run = record.run.model_copy(update={"id": new_id("run"),
                                              "created_at": record.run.created_at})
    later = replace(record, run=later_run)
    repo.save_run(later)
    repo.save_run(earlier)
    ids = [r.run.id for r in repo.list_runs()]
    assert ids == sorted(ids)
    assert len(ids) == 2


def test_factory_selects_implementation(sqlite_url) -> None:
    assert isinstance(make_repository(sqlite_url), SqliteRepository)
    assert isinstance(make_repository("memory://"), MemoryRepository)


def test_unsupported_url_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported database URL"):
        make_repository("postgres://localhost/db")


def test_relative_sqlite_path_resolves_to_repo_root() -> None:
    from app.persistence.database import REPO_ROOT
    path = resolve_sqlite_path("sqlite:///./ghostrange.db")
    assert path.is_absolute()
    assert path.name == "ghostrange.db"
    assert path == REPO_ROOT / "ghostrange.db"


def test_absolute_sqlite_path_preserved(tmp_path) -> None:
    target = tmp_path / "elsewhere.db"
    assert resolve_sqlite_path(f"sqlite:///{target}") == target


def test_ai_artifact_persistence_roundtrip(sqlite_url, record) -> None:
    sqlite_repo = SqliteRepository(sqlite_url)
    memory_repo = MemoryRepository()
    sqlite_repo.save_run(record)
    memory_repo.save_run(record)

    artifact = AIArtifact(
        id=new_id("ai_exp"),
        run_id=record.run.id,
        stage_id="S2",
        task_type="explanation",
        input_evidence_ids=["event:evt_s2_03", "rule:rule_s2_mfa_device_deletion"],
        output={"summary": "mismatch found", "gap": "preference update"},
        model=None,
        status="unavailable",
        validation_errors=[],
        created_at=now_utc(),
    )

    sqlite_repo.save_ai_artifact(artifact)
    memory_repo.save_ai_artifact(artifact)

    loaded_sqlite = sqlite_repo.get_ai_artifact(record.run.id, artifact.id)
    loaded_memory = memory_repo.get_ai_artifact(record.run.id, artifact.id)

    assert loaded_sqlite is not None
    assert loaded_memory is not None
    assert loaded_sqlite.model is None
    assert loaded_sqlite.status == "unavailable"
    assert loaded_sqlite.output == artifact.output
    assert loaded_sqlite.model_dump_json(by_alias=True) == loaded_memory.model_dump_json(by_alias=True)

    artifacts = sqlite_repo.list_ai_artifacts(record.run.id, task_type="explanation")
    assert len(artifacts) == 1
    assert artifacts[0].id == artifact.id


def test_reseed_or_resave_clears_stale_proposals(sqlite_url, record) -> None:
    repo = SqliteRepository(sqlite_url)
    repo.save_run(record)

    proposal = RuleProposal(
        id=new_id("prop"),
        run_id=record.run.id,
        original_rule_id="rule_s2_mfa_device_deletion",
        proposed_source="title: test\nid: test\nstage: S2\nselection:\n  action: UpdateMfaPreference\ncondition: selection",
        rationale="testing",
        status="proposed",
        validation=ProposalValidation(parser_status=ParserStatus.VALID),
        created_at=now_utc(),
    )
    repo.save_proposal(proposal)
    assert len(repo.list_proposals(record.run.id)) == 1

    # Resaving the run clears stale proposals
    repo.save_run(record)
    assert len(repo.list_proposals(record.run.id)) == 0

