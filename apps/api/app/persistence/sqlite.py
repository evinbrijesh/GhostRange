"""SQLite-backed repository. Same interface as MemoryRepository.

Storage shape: real columns for identity/lifecycle fields, JSON payloads (in
contract shape, camelCase) for complex objects. With ~17 events per run,
full normalization would buy nothing; JSON columns keep the stored shape
identical to the API shape, which makes parity testing straightforward.

save_run writes the complete record in a single transaction: a run plus its
events, rules, matches, and coverage is one logical unit.
"""

import sqlite3

from app.domain.coverage.models import CoverageResult
from app.domain.detections.models import DetectionRule, RuleMatch
from app.domain.scenarios.models import Scenario
from app.domain.telemetry.models import TelemetryEvent
from app.persistence.database import connect
from app.persistence.models import RuleProposal, Run
from app.persistence.repository import RunRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    scenario_version TEXT NOT NULL,
    seed INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS events (
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    id TEXT NOT NULL,
    stage_id TEXT NOT NULL,
    expected INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (run_id, id)
);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
CREATE TABLE IF NOT EXISTS run_rules (
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    rule_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (run_id, rule_id)
);
CREATE TABLE IF NOT EXISTS matches (
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    stage_id TEXT NOT NULL,
    matched_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (run_id, id)
);
CREATE INDEX IF NOT EXISTS idx_matches_run ON matches(run_id);
CREATE TABLE IF NOT EXISTS coverage (
    run_id TEXT PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE,
    score REAL NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS proposals (
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    id TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (run_id, id)
);
"""


def _json(model) -> str:
    """Serialize a contract model to camelCase JSON (the API response shape)."""
    return model.model_dump_json(by_alias=True)


class SqliteRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        connection = connect(database_url)
        try:
            connection.executescript(_SCHEMA)
            connection.commit()
        finally:
            connection.close()

    # --- runs ---

    def save_run(self, record: RunRecord) -> None:
        connection = connect(self._database_url)
        try:
            with connection:  # single transaction; rolls back on any failure
                run = record.run
                connection.execute(
                    "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
                    (run.id, run.scenario_id, run.scenario_version, run.seed,
                     run.status.value, run.created_at.isoformat(),
                     run.started_at.isoformat() if run.started_at else None,
                     run.completed_at.isoformat() if run.completed_at else None,
                     run.error),
                )
                connection.execute("DELETE FROM events WHERE run_id = ?", (run.id,))
                connection.executemany(
                    "INSERT INTO events VALUES (?,?,?,?,?,?,?)",
                    [(run.id, e.id, e.stage_id, int(e.expected), e.timestamp.isoformat(),
                      e.source.value, _json(e)) for e in record.events],
                )
                connection.execute("DELETE FROM run_rules WHERE run_id = ?", (run.id,))
                connection.executemany(
                    "INSERT INTO run_rules VALUES (?,?,?)",
                    [(run.id, r.id, _json(r)) for r in record.rules],
                )
                connection.execute("DELETE FROM matches WHERE run_id = ?", (run.id,))
                connection.executemany(
                    "INSERT INTO matches VALUES (?,?,?,?,?,?,?)",
                    [(run.id, m.id, m.event_id, m.rule_id, m.stage_id,
                      m.matched_at.isoformat(), _json(m)) for m in record.matches],
                )
                if record.coverage is not None:
                    connection.execute(
                        "INSERT OR REPLACE INTO coverage VALUES (?,?,?)",
                        (run.id, record.coverage.score, _json(record.coverage)),
                    )
        finally:
            connection.close()

    def get_run(self, run_id: str) -> RunRecord | None:
        connection = connect(self._database_url)
        try:
            run_row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if run_row is None:
                return None
            run = Run.model_validate({
                "id": run_row["id"], "scenario_id": run_row["scenario_id"],
                "scenario_version": run_row["scenario_version"], "seed": run_row["seed"],
                "status": run_row["status"], "created_at": run_row["created_at"],
                "started_at": run_row["started_at"], "completed_at": run_row["completed_at"],
                "error": run_row["error"],
            })
            events = [TelemetryEvent.model_validate_json(row["payload"]) for row in
                      connection.execute(
                          "SELECT payload FROM events WHERE run_id = ? ORDER BY timestamp, id",
                          (run_id,))]
            rules = [DetectionRule.model_validate_json(row["payload"]) for row in
                     connection.execute(
                         "SELECT payload FROM run_rules WHERE run_id = ? ORDER BY rule_id",
                         (run_id,))]
            matches = [RuleMatch.model_validate_json(row["payload"]) for row in
                       connection.execute(
                           "SELECT payload FROM matches WHERE run_id = ? ORDER BY id",
                           (run_id,))]
            coverage = None
            coverage_row = connection.execute(
                "SELECT payload FROM coverage WHERE run_id = ?", (run_id,)).fetchone()
            if coverage_row is not None:
                coverage = CoverageResult.model_validate_json(coverage_row["payload"])
            scenario = _reconstruct_scenario(run_row, coverage)
            return RunRecord(run=run, scenario=scenario, events=events,
                             rules=rules, matches=matches, coverage=coverage)
        finally:
            connection.close()

    def list_runs(self) -> list[RunRecord]:
        connection = connect(self._database_url)
        try:
            ids = [row["id"] for row in
                   connection.execute("SELECT id FROM runs ORDER BY created_at, id")]
        finally:
            connection.close()
        return [record for record in (self.get_run(run_id) for run_id in ids)
                if record is not None]

    def clear(self) -> None:
        """Remove all demo state. Idempotent: clearing an empty database is fine."""
        connection = connect(self._database_url)
        try:
            with connection:
                for table in ("proposals", "coverage", "matches", "run_rules", "events", "runs"):
                    connection.execute(f"DELETE FROM {table}")
        finally:
            connection.close()

    # --- proposals ---

    def save_proposal(self, proposal: RuleProposal) -> None:
        connection = connect(self._database_url)
        try:
            with connection:
                connection.execute(
                    "INSERT OR REPLACE INTO proposals VALUES (?,?,?)",
                    (proposal.run_id, proposal.id, _json(proposal)),
                )
        finally:
            connection.close()

    def get_proposal(self, run_id: str, proposal_id: str) -> RuleProposal | None:
        connection = connect(self._database_url)
        try:
            row = connection.execute(
                "SELECT payload FROM proposals WHERE run_id = ? AND id = ?",
                (run_id, proposal_id),
            ).fetchone()
            return RuleProposal.model_validate_json(row["payload"]) if row else None
        finally:
            connection.close()

    def list_proposals(self, run_id: str) -> list[RuleProposal]:
        connection = connect(self._database_url)
        try:
            rows = connection.execute(
                "SELECT payload FROM proposals WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
            return [RuleProposal.model_validate_json(row["payload"]) for row in rows]
        finally:
            connection.close()


def _reconstruct_scenario(run_row: sqlite3.Row, coverage: CoverageResult | None) -> Scenario:
    """Rebuild the scenario shell attached to a stored run.

    The full scenario fixture is the authoritative source; a stored run only
    needs the identity and stage metadata for graph rendering. If the fixture
    has changed since the run was stored, the stored coverage still wins for
    evaluation results — this only supplies display metadata.
    """
    from app.domain.scenarios.loader import load_scenario

    try:
        return load_scenario(run_row["scenario_id"])
    except ValueError:
        # Fixture removed/renamed since the run was stored: return a minimal
        # shell so old runs remain inspectable instead of 500-ing.
        stages = []
        if coverage is not None:
            for stage in coverage.stages:
                stages.append({"id": stage.stage_id, "name": stage.stage_id,
                               "description": "", "weight": 0.0})
        return Scenario.model_validate({
            "id": run_row["scenario_id"], "name": run_row["scenario_id"],
            "description": "", "version": run_row["scenario_version"],
            "seed": run_row["seed"], "synthetic_only": True,
            "environment": {"organization": "unknown", "compromised_identity": "",
                            "note": "scenario fixture unavailable for this stored run"},
            "stages": stages,
        })