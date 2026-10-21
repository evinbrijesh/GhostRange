"""Scenario fixture loading and validation.

Loads scenarios/<scenario-id>/scenario.yaml from the repository root and
validates it strictly: exactly the seven MVP stages, in order, with weights
summing to 1.0 and the synthetic-only flag set.
"""

import re
from functools import lru_cache
from pathlib import Path

import yaml

from app.domain.scenarios.models import Scenario
from app.shared.vocab import STAGE_IDS

REPO_ROOT = Path(__file__).resolve().parents[5]
SCENARIOS_DIR = REPO_ROOT / "scenarios"

SCENARIO_ID = "cloud-identity-compromise-v1"

# Scenario ids carry a version suffix ("...-v1"); fixture directories do not.
_VERSION_SUFFIX = re.compile(r"-v\d+$")


class ScenarioValidationError(ValueError):
    """Raised when a scenario fixture is malformed. Never leaks to API clients raw."""


def scenario_dir(scenario_id: str) -> Path:
    if not all(part.isalnum() for part in scenario_id.split("-")):
        raise ScenarioValidationError(f"invalid scenario id: {scenario_id}")
    return SCENARIOS_DIR / _VERSION_SUFFIX.sub("", scenario_id)


def scenario_path(scenario_id: str) -> Path:
    return scenario_dir(scenario_id) / "scenario.yaml"


def load_scenario(scenario_id: str) -> Scenario:
    path = scenario_path(scenario_id)
    if not path.is_file():
        raise ScenarioValidationError(f"scenario not found: {scenario_id}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ScenarioValidationError("scenario fixture must be a YAML mapping")

    stages = raw.get("stages")
    if not isinstance(stages, list) or len(stages) != len(STAGE_IDS):
        raise ScenarioValidationError(f"scenario must define exactly {len(STAGE_IDS)} stages")

    stage_ids = [s.get("id") for s in stages]
    if stage_ids != list(STAGE_IDS):
        raise ScenarioValidationError(
            f"stage ids must be {list(STAGE_IDS)} in order, got {stage_ids}"
        )

    weights = [float(s.get("weight", 0.0)) for s in stages]
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ScenarioValidationError(f"stage weights must sum to 1.0, got {sum(weights)}")

    if raw.get("synthetic_only") is not True:
        raise ScenarioValidationError("scenario must set synthetic_only: true")

    scenario = Scenario.model_validate(raw)
    if scenario.id != scenario_id:
        raise ScenarioValidationError(
            f"scenario id mismatch: fixture says {scenario.id}, requested {scenario_id}"
        )
    return scenario


@lru_cache
def load_default_scenario() -> Scenario:
    return load_scenario(SCENARIO_ID)