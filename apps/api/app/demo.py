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


def ci(baseline_path: str | None = None, threshold: float | None = None) -> int:
    """Run the DetectionOps CI gate against the committed baseline and optional threshold.

    Fails (exit 1) when the current rule set regresses attack coverage, variant
    resilience, benign suppression, or noise risk relative to
    scenarios/<scenario>/detection-baseline.json, or fails the minimum coverage threshold.
    A missing or mismatched baseline is also a gate failure: CI must never silently pass without one.
    """
    import json
    import os
    from pathlib import Path

    from app.domain.coverage.baseline import BaselineError, DetectionOpsBaseline, load_baseline
    from app.domain.coverage.detection_ops import (
        compute_detection_ops_metrics,
        evaluate_gate,
        generate_ci_report_markdown,
    )

    scenario = load_default_scenario()
    rules = [rule for rule, _ in load_default_rules()]
    rule_sources = [r.source for r in rules]

    run = Run(
        id="ci-pipeline-gate",
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        seed=scenario.seed,
        status=RunStatus.COMPLETED,
        created_at=now_utc(),
        started_at=now_utc(),
        completed_at=now_utc(),
    )
    record = execute_run(scenario, rule_sources, run)
    assert record.coverage is not None

    if baseline_path:
        try:
            raw = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
            baseline = DetectionOpsBaseline.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"\n❌ CI GATE FAILED: Failed to load baseline from '{baseline_path}': {exc}", file=sys.stderr)
            return 1
    else:
        try:
            baseline = load_baseline(scenario)
        except BaselineError as exc:
            print(f"\n❌ CI GATE FAILED: {exc}", file=sys.stderr)
            return 1

    metrics = compute_detection_ops_metrics(
        run_id=run.id,
        rules=record.rules,
        scenario=scenario,
        coverage=record.coverage,
        baseline_coverage=baseline.attack_coverage,
    )
    gate = evaluate_gate(metrics, baseline, threshold=threshold)
    markdown = generate_ci_report_markdown(scenario, metrics, gate=gate)

    # Output to stdout
    print(markdown)

    # If running inside GitHub Actions, append to GITHUB_STEP_SUMMARY
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(markdown + "\n")

    if gate.status != "pass":
        for failure in gate.failures:
            print(f"❌ {failure}", file=sys.stderr)
        print("\n❌ CI GATE FAILED: Detection metric regression detected!", file=sys.stderr)
        return 1

    print("\n✅ CI GATE PASSED: All DetectionOps metrics meet or exceed baseline.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="GhostRange demo state CLI")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed", help="Create or refresh the fixed demo run")
    commands.add_parser("reset", help="Clear all demo state")
    ci_cmd = commands.add_parser("ci", help="Run the DetectionOps CI gate check")
    ci_cmd.add_argument("--baseline", type=str, default=None, help="Path to custom baseline JSON file")
    ci_cmd.add_argument("--threshold", type=float, default=None, help="Explicit minimum attack coverage threshold (e.g. 50.0)")
    args = parser.parse_args()

    if args.command == "seed":
        seed()
        return 0
    if args.command == "ci":
        return ci(baseline_path=args.baseline, threshold=args.threshold)
    reset()
    return 0


if __name__ == "__main__":
    sys.exit(main())