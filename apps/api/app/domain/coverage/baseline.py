"""Committed DetectionOps baseline used by the regression gate.

Why a repository artifact instead of a database row or a hard-coded score:

- CI must be able to compare a fresh clone against a known-good baseline
  without seeding a run first.
- The baseline is reviewable in pull requests. A rule change that lowers
  coverage must update this file explicitly, which is the point of a gate.
- The number is never hard-coded in application logic or the frontend.

Override the path with GHOSTRANGE_BASELINE_PATH for tests and forks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.domain.coverage.calculator import FORMULA_VERSION
from app.domain.scenarios.loader import scenario_dir
from app.domain.scenarios.models import ContractModel, Scenario

BASELINE_FILENAME = "detection-baseline.json"
BASELINE_ENV_VAR = "GHOSTRANGE_BASELINE_PATH"


class BaselineError(ValueError):
    """The committed baseline is missing or does not match the scenario."""


class DetectionOpsBaseline(ContractModel):
    scenario_id: str
    scenario_version: str
    formula_version: str
    seed: int
    attack_coverage: float
    variant_resilience: float
    benign_suppression: float
    noise_risk: str


def baseline_path(scenario_id: str) -> Path:
    override = os.environ.get(BASELINE_ENV_VAR)
    if override:
        return Path(override)
    return scenario_dir(scenario_id) / BASELINE_FILENAME


def load_baseline(scenario: Scenario) -> DetectionOpsBaseline:
    """Load and validate the committed baseline for a scenario."""
    path = baseline_path(scenario.id)
    if not path.is_file():
        raise BaselineError(
            f"detection baseline missing: {path} "
            f"(set {BASELINE_ENV_VAR} to use an alternate file)"
        )

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"detection baseline is unreadable: {path}") from exc

    try:
        baseline = DetectionOpsBaseline.model_validate(raw)
    except ValueError as exc:
        raise BaselineError(f"detection baseline is invalid: {path}") from exc

    if baseline.scenario_id != scenario.id:
        raise BaselineError(
            f"baseline scenario '{baseline.scenario_id}' does not match '{scenario.id}'"
        )
    if baseline.scenario_version != scenario.version:
        raise BaselineError(
            f"baseline scenario version '{baseline.scenario_version}' does not match "
            f"'{scenario.version}'"
        )
    if baseline.formula_version != FORMULA_VERSION:
        raise BaselineError(
            f"baseline formula version '{baseline.formula_version}' does not match "
            f"'{FORMULA_VERSION}'"
        )
    if baseline.seed != scenario.seed:
        raise BaselineError(
            f"baseline seed '{baseline.seed}' does not match scenario seed '{scenario.seed}'"
        )

    return baseline
