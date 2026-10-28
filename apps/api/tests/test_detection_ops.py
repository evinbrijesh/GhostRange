"""Tests for DetectionOps capabilities:
- Scenario variants and variant resilience
- Benign event corpus and offline noise suppression
- DetectionOps 4-tier metrics
- Regression analysis & CI/CD gate blocking
- Standalone rule validation and playground evaluation
- API endpoints for variants, matches, detection-ops, regression-analysis, and ci-report
"""

from fastapi.testclient import TestClient

from app.domain.coverage.detection_ops import (
    analyze_regression,
    compute_detection_ops_metrics,
    generate_ci_report_markdown,
)
from app.domain.detections.loader import load_default_rules
from app.domain.scenarios.loader import load_default_scenario
from app.domain.simulation.benign import (
    evaluate_benign_suppression,
    generate_benign_corpus,
)
from app.domain.simulation.variants import (
    VARIANTS,
    calculate_variant_resilience,
    evaluate_variant,
    generate_variant_telemetry,
)
from app.main import app

client = TestClient(app)


def test_variants_generation_and_evaluation():
    """All 3 variants produce deterministic synthetic events and evaluate properly."""
    scenario = load_default_scenario()
    rules = [r for r, _ in load_default_rules()]

    assert len(VARIANTS) == 3
    for var_id in VARIANTS:
        events = generate_variant_telemetry(var_id, "test-run")
        assert len(events) >= 15
        assert all(e.synthetic for e in events)

        summary = evaluate_variant(var_id, rules, scenario, "test-run")
        assert summary.variant_id == var_id
        assert 0.0 <= summary.coverage_score <= 100.0
        assert len(summary.stage_statuses) == 7

    summaries = [evaluate_variant(v, rules, scenario, "test-run") for v in VARIANTS]
    resilience = calculate_variant_resilience(50.0, summaries)
    assert 0.0 <= resilience <= 100.0


def test_benign_corpus_and_suppression():
    """Benign events represent everyday cloud ops; baseline rules should have high suppression."""
    events = generate_benign_corpus()
    assert len(events) == 12
    assert all(e.synthetic for e in events)
    assert all(not e.expected for e in events)

    rules = [r for r, _ in load_default_rules()]
    result = evaluate_benign_suppression(rules, events)

    assert result.total_benign_events == 12
    assert result.suppression_rate >= 75.0
    assert result.noise_risk in ("low", "medium", "high")


def test_regression_analysis_blocking():
    """Regression analyzer must block when candidate coverage drops below baseline."""
    # When candidate is lower -> regression detected and blocked
    blocked = analyze_regression("base-1", "cand-1", baseline_coverage=50.0, candidate_coverage=40.0)
    assert blocked.status == "regression_detected"
    assert blocked.is_blocked is True
    assert blocked.coverage_diff == -10.0
    assert "REGRESSION BLOCKED" in blocked.summary

    # When candidate is higher -> pass
    passed = analyze_regression("base-1", "cand-2", baseline_coverage=50.0, candidate_coverage=75.0)
    assert passed.status == "pass"
    assert passed.is_blocked is False
    assert passed.coverage_diff == 25.0
    assert "VALIDATION PASSED" in passed.summary


def test_ci_report_markdown_generation():
    """CI report produces markdown suitable for GitHub PR comments."""
    scenario = load_default_scenario()
    rules = [r for r, _ in load_default_rules()]
    from app.domain.coverage.models import CoverageResult

    fake_coverage = CoverageResult(
        run_id="ci-test-run",
        score=50.0,
        stage_counts={"detected": 3, "partial": 0, "missed": 4, "error": 0},
        stages=[],
        formula_version="coverage-v1",
        evaluator_errors=[],
    )
    metrics = compute_detection_ops_metrics("ci-test-run", rules, scenario, fake_coverage)
    md = generate_ci_report_markdown(scenario, metrics)

    assert "## 🛡️ GhostRange DetectionOps CI/CD Report" in md
    assert "Attack Coverage" in md
    assert "Variant Resilience" in md
    assert "Benign Suppression" in md
    assert "Behavioral Variant Matrix" in md


def test_api_rules_validate():
    """POST /api/rules/validate tests syntax for valid and invalid Sigma YAML."""
    valid_yaml = """
title: Test Valid Admin Attachment
id: rule_s4_test_admin
stage: S4
logsource:
  product: cloud
  service: iam
selection:
  action: AttachRolePolicy
  attributes.policy|contains: AdministratorAccess
condition: selection
level: high
"""
    res = client.post("/api/rules/validate", json={"yamlSource": valid_yaml})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["ruleId"] == "rule_s4_test_admin"
    assert data["stageId"] == "S4"

    invalid_yaml = "invalid: yaml: [broken"
    res_bad = client.post("/api/rules/validate", json={"yamlSource": invalid_yaml})
    assert res_bad.status_code == 200
    data_bad = res_bad.json()
    assert data_bad["valid"] is False
    assert len(data_bad["errors"]) > 0


def test_api_rules_evaluate():
    """POST /api/rules/evaluate tests candidate rule against attack & benign telemetry."""
    rule_yaml = """
title: Test MFA Detection
id: rule_s2_test_mfa
stage: S2
logsource:
  product: cloud
  service: iam
selection:
  action: UpdateMfaPreference
condition: selection
level: high
"""
    res = client.post("/api/rules/evaluate", json={"yamlSource": rule_yaml})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["ruleId"] == "rule_s2_test_mfa"
    assert data["attackMatchesCount"] >= 1
    assert data["noiseHitsCount"] == 0
    assert data["benignSuppressed"] is True


def test_api_runs_detection_ops_endpoints():
    """Test /variants, /matches, /detection-ops, /regression-analysis, and /ci-report."""
    res_create = client.post("/api/runs", json={"scenarioId": "cloud-identity-compromise-v1"})
    assert res_create.status_code == 201
    run_id = res_create.json()["id"]

    # 1. Matches endpoint
    res_matches = client.get(f"/api/runs/{run_id}/matches")
    assert res_matches.status_code == 200
    assert "matches" in res_matches.json()
    assert res_matches.json()["total"] >= 1

    # 2. Variants endpoint
    res_variants = client.get(f"/api/runs/{run_id}/variants")
    assert res_variants.status_code == 200
    v_data = res_variants.json()
    assert len(v_data["variants"]) == 3
    assert "variantResilience" in v_data

    # 3. DetectionOps endpoint
    res_ops = client.get(f"/api/runs/{run_id}/detection-ops")
    assert res_ops.status_code == 200
    ops_data = res_ops.json()
    assert ops_data["attackCoverage"] == 50.0
    assert "variantResilience" in ops_data
    assert "benignSuppression" in ops_data
    assert ops_data["noiseRisk"] in ("low", "medium", "high")
    assert ops_data["regressionStatus"] == "pass"

    # 4. Regression Analysis endpoint
    res_reg = client.post(f"/api/runs/{run_id}/regression-analysis", json={})
    assert res_reg.status_code == 200
    reg_data = res_reg.json()
    assert "coverageDiff" in reg_data
    assert reg_data["isBlocked"] is False
    assert reg_data["baselineRunId"] == "committed-baseline:cloud-identity-compromise-v1"

    # 5. CI Report endpoint
    res_ci = client.get(f"/api/runs/{run_id}/ci-report")
    assert res_ci.status_code == 200
    ci_data = res_ci.json()
    assert ci_data["decision"] == "PASS"
    assert ci_data["gate"]["status"] == "pass"
    assert ci_data["gate"]["failures"] == []
    assert "## 🛡️ GhostRange DetectionOps CI/CD Report" in ci_data["markdown"]



# --- Committed baseline and gate ---


def _write_baseline(path, **overrides):
    import json

    payload = {
        "scenarioId": "cloud-identity-compromise-v1",
        "scenarioVersion": "1.0.0",
        "formulaVersion": "coverage-v1",
        "seed": 1337,
        "attackCoverage": 50.0,
        "variantResilience": 48.8,
        "benignSuppression": 100.0,
        "noiseRisk": "low",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _current_metrics(rules, scenario):
    from app.api.pipeline import execute_run
    from app.persistence.models import Run, now_utc

    run = Run(
        id="gate-test-run",
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        seed=scenario.seed,
        status="completed",
        created_at=now_utc(),
        started_at=now_utc(),
        completed_at=now_utc(),
    )
    record = execute_run(scenario, [r.source for r in rules], run)
    assert record.coverage is not None
    return compute_detection_ops_metrics(
        run_id=run.id,
        rules=record.rules,
        scenario=scenario,
        coverage=record.coverage,
    )


def test_gate_passes_on_current_ruleset():
    from app.domain.coverage.baseline import load_baseline
    from app.domain.coverage.detection_ops import evaluate_gate

    scenario = load_default_scenario()
    rules = [r for r, _ in load_default_rules()]
    baseline = load_baseline(scenario)
    metrics = _current_metrics(rules, scenario)

    gate = evaluate_gate(metrics, baseline)
    assert gate.status == "pass"
    assert gate.failures == []
    assert {c.name for c in gate.checks} == {
        "attack_coverage",
        "variant_resilience",
        "benign_suppression",
        "noise_risk",
    }


def test_gate_blocks_when_a_detecting_rule_is_removed():
    from app.domain.coverage.baseline import load_baseline
    from app.domain.coverage.detection_ops import evaluate_gate

    scenario = load_default_scenario()
    rules = [r for r, _ in load_default_rules()]
    baseline = load_baseline(scenario)

    weakened = [r for r in rules if r.id != "rule_s1_unusual_location_login"]
    metrics = _current_metrics(weakened, scenario)

    gate = evaluate_gate(metrics, baseline)
    assert metrics.attack_coverage < baseline.attack_coverage
    assert gate.status == "blocked"
    assert any("attack_coverage" in failure for failure in gate.failures)


def test_ci_cli_fails_when_baseline_requires_higher_coverage(tmp_path, monkeypatch):
    import json

    from app.demo import ci

    baseline_file = tmp_path / "detection-baseline.json"
    _write_baseline(baseline_file, attackCoverage=60.0)
    monkeypatch.setenv("GHOSTRANGE_BASELINE_PATH", str(baseline_file))

    exit_code = ci()
    assert exit_code == 1

    # Sanity: the file is valid JSON and was actually used.
    assert json.loads(baseline_file.read_text())["attackCoverage"] == 60.0


def test_ci_cli_fails_when_baseline_is_missing(tmp_path, monkeypatch):
    from app.demo import ci

    monkeypatch.setenv("GHOSTRANGE_BASELINE_PATH", str(tmp_path / "absent.json"))
    assert ci() == 1


def test_baseline_scenario_mismatch_rejected(tmp_path, monkeypatch):
    import pytest

    from app.domain.coverage.baseline import BaselineError, load_baseline

    baseline_file = tmp_path / "detection-baseline.json"
    _write_baseline(baseline_file, scenarioId="some-other-scenario")
    monkeypatch.setenv("GHOSTRANGE_BASELINE_PATH", str(baseline_file))

    with pytest.raises(BaselineError):
        load_baseline(load_default_scenario())


def test_api_ci_report_blocks_against_stricter_baseline(tmp_path, monkeypatch):
    """The endpoint must return BLOCKED, not a warning, when below baseline."""
    baseline_file = tmp_path / "detection-baseline.json"
    _write_baseline(baseline_file, attackCoverage=60.0)
    monkeypatch.setenv("GHOSTRANGE_BASELINE_PATH", str(baseline_file))

    run_id = client.post(
        "/api/runs", json={"scenarioId": "cloud-identity-compromise-v1"}
    ).json()["id"]

    response = client.get(f"/api/runs/{run_id}/ci-report")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCKED"
    assert data["gate"]["status"] == "blocked"
    assert data["gate"]["failures"]
    assert "❌ BLOCKED" in data["markdown"]


def test_ci_cli_fails_when_threshold_is_not_met():
    from app.demo import ci

    # Base coverage is 50.0%; threshold 60.0% must fail the gate
    exit_code = ci(threshold=60.0)
    assert exit_code == 1

    # Base coverage 50.0% meets threshold 50.0% -> passes
    assert ci(threshold=50.0) == 0


def test_ci_cli_with_custom_baseline_path(tmp_path):
    from app.demo import ci

    custom_baseline = tmp_path / "custom-baseline.json"
    _write_baseline(custom_baseline, attackCoverage=40.0)

    # Candidate has 50.0% >= 40.0% -> passes
    assert ci(baseline_path=str(custom_baseline)) == 0

    # Stricter baseline 70.0% -> blocks
    _write_baseline(custom_baseline, attackCoverage=70.0)
    assert ci(baseline_path=str(custom_baseline)) == 1

