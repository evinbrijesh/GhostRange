"""Run report: deterministic assembly, improvements, limitations, AI slot."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SCENARIO_ID = "cloud-identity-compromise-v1"

GOOD_S2_PROPOSAL = """
title: MFA Preference Change For Compromised Identity
id: rule_s2_mfa_preference_change
stage: S2
logsource:
  product: cloud
  service: iam
selection:
  action: UpdateMfaPreference
  identity.id: user-alice-morgan
condition: selection
level: high
"""


def _run_with_improvement() -> str:
    response = client.post("/api/runs", json={"scenarioId": SCENARIO_ID})
    assert response.status_code == 201
    run_id = response.json()["id"]
    proposal = client.post(f"/api/runs/{run_id}/rule-proposals", json={
        "originalRuleId": "rule_s2_mfa_device_deletion",
        "proposedSource": GOOD_S2_PROPOSAL,
        "rationale": "starter rule watched the wrong action",
    }).json()
    client.post(f"/api/runs/{run_id}/rule-proposals/{proposal['id']}/validate")
    return run_id


def test_report_contains_required_sections() -> None:
    run_id = _run_with_improvement()
    report = client.get(f"/api/runs/{run_id}/report").json()
    assert report["runId"] == run_id
    assert report["scenario"]["id"] == SCENARIO_ID
    assert report["scenario"]["name"] == "Cloud Identity Compromise"
    assert report["seed"] == 1337
    assert report["coverage"]["score"] == 50.0
    assert report["aiSummary"] is None  # degraded-AI slot, report still valid


def test_report_lists_only_validated_improving_proposals() -> None:
    run_id = _run_with_improvement()
    report = client.get(f"/api/runs/{run_id}/report").json()
    assert len(report["improvements"]) == 1
    improvement = report["improvements"][0]
    assert improvement["originalRuleId"] == "rule_s2_mfa_device_deletion"
    assert improvement["improvesCoverage"] is True
    assert improvement["coverageBefore"] == 50.0
    assert improvement["coverageAfter"] == 60.0


def test_report_excludes_never_validated_proposals() -> None:
    response = client.post("/api/runs", json={"scenarioId": SCENARIO_ID})
    run_id = response.json()["id"]
    client.post(f"/api/runs/{run_id}/rule-proposals", json={
        "originalRuleId": "rule_s2_mfa_device_deletion",
        "proposedSource": GOOD_S2_PROPOSAL,
    })  # created but never validated
    report = client.get(f"/api/runs/{run_id}/report").json()
    assert report["improvements"] == []


def test_report_states_limitations_and_assumptions() -> None:
    run_id = _run_with_improvement()
    report = client.get(f"/api/runs/{run_id}/report").json()
    assert report["limitations"], "reports must state limitations"
    assert any("synthetic" in item for item in report["limitations"])
    assert any("do not prove production security" in item for item in report["limitations"])
    assert report["assumptions"], "reports must state assumptions"


def test_report_unknown_run_404() -> None:
    response = client.get("/api/runs/run_missing/report")
    assert response.status_code == 404
    assert response.json()["code"] == "RUN_NOT_FOUND"