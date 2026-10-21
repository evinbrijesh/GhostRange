"""Starter-rule loading: reads every rules/*.yaml fixture for a scenario."""

from functools import lru_cache
from pathlib import Path

from app.domain.detections.models import DetectionRule
from app.domain.detections.parser import parse_rule
from app.domain.scenarios.loader import scenario_dir


def rules_dir(scenario_id: str) -> Path:
    return scenario_dir(scenario_id) / "rules"


def load_rules(scenario_id: str) -> list[tuple[DetectionRule, tuple[tuple[str, str, str], ...]]]:
    """Load and parse all starter rules. Invalid rules are returned with
    parser_status='invalid' so they surface in evaluator_errors instead of
    silently disappearing."""
    directory = rules_dir(scenario_id)
    if not directory.is_dir():
        return []

    compiled: list[tuple[DetectionRule, tuple[tuple[str, str, str], ...]]] = []
    for path in sorted(directory.glob("*.yaml")):
        rule, selection = parse_rule(path.read_text(encoding="utf-8"))
        if rule.source == "":
            # Parser could not even attribute the source (structural failure);
            # keep the raw text so the UI can show what failed.
            rule = rule.model_copy(update={"source": path.read_text(encoding="utf-8")})
        compiled.append((rule, selection))
    return compiled


@lru_cache
def load_default_rules() -> list[tuple[DetectionRule, tuple[tuple[str, str, str], ...]]]:
    from app.domain.scenarios.loader import SCENARIO_ID

    return load_rules(SCENARIO_ID)