"""Scenario fixture validation."""

import pytest

from app.domain.scenarios.loader import SCENARIO_ID, load_scenario
from app.shared.vocab import STAGE_IDS


def test_default_scenario_loads() -> None:
    scenario = load_scenario(SCENARIO_ID)
    assert scenario.id == SCENARIO_ID
    assert scenario.synthetic_only is True
    assert isinstance(scenario.seed, int)


def test_scenario_has_seven_stages_in_order() -> None:
    scenario = load_scenario(SCENARIO_ID)
    assert [s.id for s in scenario.stages] == list(STAGE_IDS)


def test_stage_weights_sum_to_one() -> None:
    scenario = load_scenario(SCENARIO_ID)
    assert abs(sum(s.weight for s in scenario.stages) - 1.0) < 1e-6


def test_unknown_scenario_rejected() -> None:
    with pytest.raises(ValueError, match="not found"):
        load_scenario("does-not-exist")