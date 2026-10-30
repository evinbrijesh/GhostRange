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


def test_report_summary_deterministic_generation(monkeypatch) -> None:
    from app.config import settings
    from app.persistence.instance import repository
    monkeypatch.setattr(settings, "nebius_api_key", None)

    run_id = _run_with_improvement()
    # Initially None
    initial_report = client.get(f"/api/runs/{run_id}/report").json()
    assert initial_report["aiSummary"] is None

    # Generate summary
    gen_res = client.post(f"/api/runs/{run_id}/report/summary")
    assert gen_res.status_code == 200
    report = gen_res.json()

    assert report["aiSummary"] is not None
    summary_artifact = report["aiSummary"]
    assert summary_artifact["taskType"] == "report_summary"
    assert summary_artifact["status"] == "unavailable"
    assert summary_artifact["model"] is None
    assert "Deterministic executive audit" in summary_artifact["output"]["executiveSummary"]
    assert summary_artifact["output"]["recommendations"]

    # Verify subsequent GET returns the persisted summary
    refetched = client.get(f"/api/runs/{run_id}/report").json()
    assert refetched["aiSummary"] is not None
    assert refetched["aiSummary"]["id"] == summary_artifact["id"]

    # Verify repository persistence
    stored = repository.get_ai_artifact(run_id, summary_artifact["id"])
    assert stored is not None
    assert stored.task_type == "report_summary"


def test_report_summary_live_nemotron_mock(monkeypatch) -> None:
    from app.ai import client as ai_client
    from app.config import settings
    monkeypatch.setattr(settings, "nebius_api_key", "test-key")
    monkeypatch.setattr(settings, "nebius_model", "test-model")

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"executive_summary": "Nemotron executive analysis.",'
                                ' "attack_narrative": "Adversary progressed across cloud identity.",'
                                ' "detection_gaps": "MFA manipulation missed in S2.",'
                                ' "remediation_impact": "Coverage jumped 50 to 60.",'
                                ' "recommendations": ["Audit MFA", "Monitor IAM"],'
                                ' "cited_evidence_ids": ["stage:S2", "rule:rule_s2_mfa_device_deletion"]}'
                            )
                        }
                    }
                ]
            }

    class FakeHttpClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

        def post(self, *args, **kwargs) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(ai_client.httpx, "Client", FakeHttpClient)

    run_id = _run_with_improvement()
    gen_res = client.post(f"/api/runs/{run_id}/report/summary")
    assert gen_res.status_code == 200
    report = gen_res.json()

    assert report["aiSummary"]["status"] == "succeeded"
    assert report["aiSummary"]["model"] == "test-model"
    assert report["aiSummary"]["output"]["executiveSummary"] == "Nemotron executive analysis."
    assert "stage:S2" in report["aiSummary"]["output"]["citedEvidenceIds"]


def test_report_summary_marked_stale_when_proposal_validated_afterward() -> None:
    """When a new proposal is validated after an AI summary was generated, report marks summary as stale."""
    # 1. Create run and generate AI summary first
    res = client.post("/api/runs", json={"scenarioId": SCENARIO_ID})
    run_id = res.json()["id"]
    gen_res = client.post(f"/api/runs/{run_id}/report/summary")
    assert gen_res.status_code == 200
    report_initial = client.get(f"/api/runs/{run_id}/report").json()
    assert report_initial["aiSummary"] is not None
    assert report_initial["aiSummary"]["isStale"] is False

    # 2. Now submit and validate an improving proposal afterwards
    prop_res = client.post(f"/api/runs/{run_id}/rule-proposals", json={
        "originalRuleId": "rule_s2_mfa_device_deletion",
        "proposedSource": GOOD_S2_PROPOSAL,
        "rationale": "later proposal",
    })
    prop_id = prop_res.json()["id"]
    val_res = client.post(f"/api/runs/{run_id}/rule-proposals/{prop_id}/validate")
    assert val_res.status_code == 200

    # 3. Fetch report again: aiSummary should now be marked isStale == True
    report_after = client.get(f"/api/runs/{run_id}/report").json()
    assert report_after["aiSummary"] is not None
    assert report_after["aiSummary"]["isStale"] is True
    assert "staleReason" in report_after["aiSummary"]


def test_report_summary_marked_stale_when_existing_proposal_validated_afterward() -> None:
    """A proposal created before the summary but validated after it still makes the summary stale."""
    res = client.post("/api/runs", json={"scenarioId": SCENARIO_ID})
    run_id = res.json()["id"]
    prop_id = client.post(f"/api/runs/{run_id}/rule-proposals", json={
        "originalRuleId": "rule_s2_mfa_device_deletion",
        "proposedSource": GOOD_S2_PROPOSAL,
        "rationale": "created before the summary",
    }).json()["id"]

    assert client.post(f"/api/runs/{run_id}/report/summary").status_code == 200
    report_initial = client.get(f"/api/runs/{run_id}/report").json()
    assert report_initial["aiSummary"]["isStale"] is False

    assert client.post(f"/api/runs/{run_id}/rule-proposals/{prop_id}/validate").status_code == 200

    report_after = client.get(f"/api/runs/{run_id}/report").json()
    assert report_after["aiSummary"]["isStale"] is True
    assert "staleReason" in report_after["aiSummary"]