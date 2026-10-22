"""Rule mismatch details: the 'why did this rule fail' data for the UI."""

from app.domain.detections.evaluator import MISMATCH_CAP, evaluate_run
from app.domain.detections.loader import load_default_rules
from app.domain.scenarios.loader import SCENARIO_ID, load_scenario
from app.domain.simulation.engine import generate_telemetry

SCENARIO = load_scenario(SCENARIO_ID)
RULE_SOURCES = [rule.source for rule, _ in load_default_rules()]


def _run(seed: int = 1337):
    events = generate_telemetry(SCENARIO, "run_test", seed)
    stages, matches, _errors, _rules = evaluate_run(
        [s.id for s in SCENARIO.stages], events, RULE_SOURCES, "run_test"
    )
    return {s.stage_id: s for s in stages}, matches


def test_missed_stage_explains_value_mismatch() -> None:
    stages, _ = _run()
    s2 = stages["S2"]
    assert s2.status == "missed"
    assert s2.mismatches, "S2's rule must produce a mismatch explanation"
    mismatch = next(m for m in s2.mismatches if m.rule_id == "rule_s2_mfa_device_deletion")
    action_failure = next(f for f in mismatch.failed_expressions if f.field == "action")
    assert action_failure.operator == "exact"
    assert action_failure.expected == "DeleteVirtualMfaDevice"
    assert action_failure.actual == "UpdateMfaPreference"


def test_partial_stage_explains_the_unmatched_event() -> None:
    stages, _ = _run()
    s4 = stages["S4"]
    assert s4.status == "partial"
    # evt_s4_10 (AssumeRole) is the expected event the rule did not match.
    mismatch = next(m for m in s4.mismatches
                    if m.rule_id == "rule_s4_admin_policy_attachment"
                    and m.event_id == "evt_s4_10")
    action_failure = next(f for f in mismatch.failed_expressions if f.field == "action")
    assert action_failure.expected == "AttachRolePolicy"
    assert action_failure.actual == "AssumeRole"


def test_absent_field_reported_as_null_actual() -> None:
    stages, _ = _run()
    # rule_s4 checks attributes.policy; evt_s4_10 (AssumeRole) has no policy
    # attribute, so the failure must surface as actual=None, not a fake value.
    mismatch = next(m for m in stages["S4"].mismatches if m.event_id == "evt_s4_10")
    policy_failure = next(f for f in mismatch.failed_expressions if f.field == "attributes.policy")
    assert policy_failure.actual is None


def test_detected_stage_has_no_mismatches() -> None:
    stages, _ = _run()
    assert stages["S1"].mismatches == []
    assert stages["S3"].mismatches == []
    assert stages["S5"].mismatches == []


def test_matched_pairs_never_appear_in_mismatches() -> None:
    stages, matches = _run()
    matched_pairs = {(m.rule_id, m.event_id) for m in matches}
    for stage in stages.values():
        for mismatch in stage.mismatches:
            assert (mismatch.rule_id, mismatch.event_id) not in matched_pairs


def test_background_events_never_produce_mismatches() -> None:
    stages, _ = _run()
    background_ids = {"evt_s1_02", "evt_s2_04", "evt_s3_08", "evt_s4_11",
                      "evt_s5_13", "evt_s6_15"}
    for stage in stages.values():
        for mismatch in stage.mismatches:
            assert mismatch.event_id not in background_ids


def test_mismatch_cap_is_enforced() -> None:
    # 60 valid non-matching rules for S1 -> 60 candidate mismatches -> capped.
    many_rules = RULE_SOURCES + [
        f"""
title: Non-matching {i}
id: rule_cap_test_{i:02d}
stage: S1
logsource:
  product: cloud
  service: auth
selection:
  action: NonexistentAction{i:02d}
condition: selection
level: low
"""
        for i in range(60)
    ]
    events = generate_telemetry(SCENARIO, "run_test", 1337)
    stages, _, _, _ = evaluate_run(
        [s.id for s in SCENARIO.stages], events, many_rules, "run_test"
    )
    s1 = next(s for s in stages if s.stage_id == "S1")
    assert len(s1.mismatches) == MISMATCH_CAP