"""Evaluator: detected, partial, missed, and error states; parser-error separation."""

from app.domain.detections.evaluator import evaluate_run
from app.domain.detections.loader import load_default_rules
from app.domain.scenarios.loader import SCENARIO_ID, load_scenario
from app.domain.simulation.engine import generate_telemetry

SCENARIO = load_scenario(SCENARIO_ID)
RULE_SOURCES = [rule.source for rule, _ in load_default_rules()]


def _run(seed: int = 1337):
    events = generate_telemetry(SCENARIO, "run_test", seed)
    stages, matches, errors, rules = evaluate_run(
        [s.id for s in SCENARIO.stages], events, RULE_SOURCES, "run_test"
    )
    return {s.stage_id: s for s in stages}, matches, errors, rules


def test_default_seed_produces_mixed_outcomes() -> None:
    stages, _, _, _ = _run()
    detected = {sid for sid, s in stages.items() if s.status == "detected"}
    partial = {sid for sid, s in stages.items() if s.status == "partial"}
    missed = {sid for sid, s in stages.items() if s.status == "missed"}
    assert detected == {"S1", "S3", "S5"}
    assert partial == {"S4"}
    assert missed == {"S2", "S6", "S7"}


def test_partial_stage_matches_some_expected_events() -> None:
    stages, _, _, _ = _run()
    s4 = stages["S4"]
    assert s4.status == "partial"
    assert len(s4.matched_event_ids) < len(s4.expected_event_ids)
    assert s4.matched_event_ids  # at least one matched


def test_parser_error_reported_separately_not_as_security_miss() -> None:
    stages, _, errors, _ = _run()
    # The invalid rule targets S6; S6 still has a valid rule, so it stays
    # `missed` (a security fact) while the parser failure is reported separately.
    assert stages["S6"].status == "missed"
    assert any("rule_s6_tor_exit_access" in e for e in errors)
    assert stages["S6"].errors


def test_detected_stage_has_latency_and_evidence() -> None:
    stages, _, _, _ = _run()
    s1 = stages["S1"]
    assert s1.status == "detected"
    assert s1.detection_latency_ms is not None
    assert s1.detection_latency_ms >= 0
    assert any(ref.startswith("event:") for ref in s1.evidence_ids)
    assert any(ref.startswith("rule:") for ref in s1.evidence_ids)


def test_missed_stage_has_no_matches() -> None:
    stages, matches, _, _ = _run()
    s2 = stages["S2"]
    assert s2.status == "missed"
    assert not s2.matched_event_ids
    assert not any(m.stage_id == "S2" and m.event_id in s2.expected_event_ids for m in matches)


def test_background_events_do_not_affect_stage_status() -> None:
    stages, matches, _, _ = _run()
    # Bob's benign CreateAccessKey (S5 background, event evt_s5_13) must not
    # match the S5 rule (which is scoped to alice) and must not affect status.
    s5 = stages["S5"]
    assert s5.status == "detected"
    assert not any(m.event_id == "evt_s5_13" for m in matches)
    assert s5.matched_event_ids == ["evt_s5_12"]


def test_stage_with_no_rules_is_missed() -> None:
    stages, _, _, _ = _run()
    assert stages["S7"].status == "missed"
    assert stages["S7"].matched_rule_ids == []


def test_stage_where_all_rules_invalid_is_error() -> None:
    # Give S7 only an invalid rule: evaluation is impossible -> error, not missed.
    bad_rule = """
title: Bad
id: rule_s7_bad
stage: S7
logsource:
  product: cloud
  service: storage
selection:
  action|re: ".*"
condition: selection
"""
    events = generate_telemetry(SCENARIO, "run_test", 1337)
    stages, _, errors, _ = evaluate_run(
        [s.id for s in SCENARIO.stages], events, RULE_SOURCES + [bad_rule], "run_test"
    )
    by_id = {s.stage_id: s for s in stages}
    assert by_id["S7"].status == "error"
    assert by_id["S7"].errors
    assert any("rule_s7_bad" in e for e in errors)