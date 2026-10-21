"""Rule parser: supported subset acceptance and unsupported-syntax rejection."""

from app.domain.detections.parser import parse_rule

VALID_RULE = """
title: Test Rule
id: rule_test_one
stage: S1
logsource:
  product: cloud
  service: auth
selection:
  action: ConsoleLogin
  srcIp|contains: "203.0.113."
condition: selection
level: high
"""


def test_valid_rule_parses() -> None:
    rule, selection = parse_rule(VALID_RULE)
    assert rule.parser_status == "valid"
    assert rule.id == "rule_test_one"
    assert rule.stage_id == "S1"
    assert rule.level == "high"
    assert ("action", "exact", "ConsoleLogin") in selection
    assert ("srcIp", "contains", "203.0.113.") in selection


def test_missing_title_rejected() -> None:
    rule, _ = parse_rule("id: rule_x\nstage: S1\nlogsource: {product: cloud, service: auth}\n"
                         "selection: {action: A}\ncondition: selection\n")
    assert rule.parser_status == "invalid"
    assert any("title" in e for e in rule.parser_errors)


def test_unsupported_operator_rejected() -> None:
    rule, selection = parse_rule(VALID_RULE.replace("srcIp|contains", "srcIp|re"))
    assert rule.parser_status == "invalid"
    assert any("|re" in e or "re" in e for e in rule.parser_errors)
    assert selection == ()


def test_unsupported_condition_rejected() -> None:
    rule, _ = parse_rule(VALID_RULE.replace("condition: selection",
                                            "condition: selection and filter"))
    assert rule.parser_status == "invalid"
    assert any("condition" in e for e in rule.parser_errors)


def test_unknown_top_level_key_rejected() -> None:
    rule, _ = parse_rule(VALID_RULE + "detection: {}\n")
    assert rule.parser_status == "invalid"
    assert any("detection" in e for e in rule.parser_errors)


def test_list_value_rejected() -> None:
    rule, _ = parse_rule(VALID_RULE.replace("action: ConsoleLogin", "action: [A, B]"))
    assert rule.parser_status == "invalid"
    assert any("scalar" in e for e in rule.parser_errors)


def test_unknown_field_rejected() -> None:
    rule, _ = parse_rule(VALID_RULE.replace("action: ConsoleLogin", "host: web01"))
    assert rule.parser_status == "invalid"
    assert any("unsupported field" in e for e in rule.parser_errors)


def test_invalid_stage_rejected() -> None:
    rule, _ = parse_rule(VALID_RULE.replace("stage: S1", "stage: S9"))
    assert rule.parser_status == "invalid"
    assert any("stage" in e for e in rule.parser_errors)


def test_invalid_yaml_handled_safely() -> None:
    rule, selection = parse_rule("title: [unclosed\n  bad yaml: {")
    assert rule.parser_status == "invalid"
    assert selection == ()
    assert rule.parser_errors