"""Demo state CLI: seed and reset.

Usage (from apps/api):
    uv run python -m app.demo seed
    uv run python -m app.demo reset

seed executes the same shared pipeline as POST /api/runs (app.api.pipeline)
with a FIXED demo run ID and the scenario's default seed, then upserts it.
Running seed twice produces the same stored state — idempotent by design.

reset empties the repository. Resetting an empty database is fine — also
idempotent. Both commands are safe to run repeatedly.
"""

import argparse
import sys

from app.api.pipeline import execute_run
from app.config import settings
from app.domain.detections.loader import load_default_rules
from app.domain.scenarios.loader import load_default_scenario
from app.persistence.models import Run, now_utc
from app.persistence.repository import Repository, make_repository
from app.shared.vocab import RunStatus

DEMO_RUN_ID = "run_demo_seed_0001"


def seed(repo: Repository | None = None) -> Run:
    """Create (or refresh) the fixed demo run. Returns the stored run."""
    repository = repo if repo is not None else make_repository(settings.database_url)
    scenario = load_default_scenario()
    rule_sources = [rule.source for rule, _ in load_default_rules()]

    run = Run(
        id=DEMO_RUN_ID,
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        seed=scenario.seed,
        status=RunStatus.COMPLETED,
        created_at=now_utc(),
        started_at=now_utc(),
        completed_at=now_utc(),
    )
    record = execute_run(scenario, rule_sources, run)
    repository.save_run(record)
    repository.clear_proposals(run.id)

    assert record.coverage is not None
    counts = record.coverage.stage_counts
    print(f"Seeded demo run: {run.id}")
    print(f"  scenario: {scenario.id} (version {scenario.version}, seed {run.seed})")
    print(f"  coverage: {record.coverage.score}% "
          f"(detected {counts['detected']}, partial {counts['partial']}, "
          f"missed {counts['missed']}, error {counts['error']})")
    print(f"  events: {len(record.events)}, matches: {len(record.matches)}, "
          f"evaluator errors: {len(record.coverage.evaluator_errors)}")
    return run


def reset(repo: Repository | None = None) -> None:
    """Remove all demo state. Idempotent."""
    repository = repo if repo is not None else make_repository(settings.database_url)
    repository.clear()
    print("Demo state cleared.")


def main() -> int:
    parser = argparse.ArgumentParser(description="GhostRange demo state CLI")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed", help="Create or refresh the fixed demo run")
    commands.add_parser("reset", help="Clear all demo state")
    args = parser.parse_args()

    if args.command == "seed":
        seed()
        return 0
    reset()
    return 0


if __name__ == "__main__":
    sys.exit(main())