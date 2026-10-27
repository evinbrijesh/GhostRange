"""Proposal validation: the deterministic improvement loop."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SCENARIO_ID = "cloud-identity-compromise-v1"


def _create_run() -> str:
    response = client.post("/api/runs", json={"scenarioId": SCENARIO_ID})
    assert response.status_code == 201
    return response.json()["id"]


def _propose(run_id: str, source: str, original: str = "rule_s2_mfa_device_deletion") -> dict:
    response = client.post(f"/api/runs/{run_id}/rule-proposals", json={
        "originalRuleId": original,
        "proposedSource": source,
        "rationale": "test proposal",
    })
    assert response.status_code == 201, response.text
    return response.json()


# A corrected S2 rule: matches UpdateMfaPreference (what the scenario emits)
# instead of DeleteVirtualMfaDevice (what the starter rule wrongly watches).
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


def test_create_proposal_parses_and_stores() -> None:
    run_id = _create_run()
    proposal = _propose(run_id, GOOD_S2_PROPOSAL)
    assert proposal["status"] == "proposed"
    assert proposal["validation"]["parserStatus"] == "valid"
    assert proposal["validation"]["improvesCoverage"] is None  # not validated yet
    assert proposal["originalRuleId"] == "rule_s2_mfa_device_deletion"


def test_validate_good_proposal_improves_coverage() -> None:
    run_id = _create_run()
    before_score = client.get(f"/api/runs/{run_id}/coverage").json()["score"]
    proposal = _propose(run_id, GOOD_S2_PROPOSAL)
    validated = client.post(
        f"/api/runs/{run_id}/rule-proposals/{proposal['id']}/validate").json()
    assert validated["status"] == "validated"
    assert validated["validation"]["improvesCoverage"] is True
    assert validated["validation"]["coverageBefore"] == before_score
    assert validated["validation"]["coverageAfter"] > before_score


def test_validate_worse_proposal_does_not_improve() -> None:
    run_id = _create_run()
    # Replace a WORKING rule (S1) with one that never matches.
    worse = GOOD_S2_PROPOSAL.replace("rule_s2_mfa_preference_change", "rule_s1_worse")
    worse = worse.replace("stage: S2", "stage: S1")
    worse = worse.replace("action: UpdateMfaPreference", "action: Nonexistent")
    proposal = _propose(run_id, worse, original="rule_s1_unusual_location_login")
    validated = client.post(
        f"/api/runs/{run_id}/rule-proposals/{proposal['id']}/validate").json()
    assert validated["validation"]["improvesCoverage"] is False
    assert validated["validation"]["coverageAfter"] < validated["validation"]["coverageBefore"]


def test_unparseable_proposal_rejected_with_null_comparison() -> None:
    run_id = _create_run()
    bad = GOOD_S2_PROPOSAL.replace("action: UpdateMfaPreference", "action|re: \".*\"")
    proposal = _propose(run_id, bad)
    assert proposal["status"] == "rejected"
    assert proposal["validation"]["parserStatus"] == "invalid"
    assert proposal["validation"]["parserErrors"]
    assert proposal["validation"]["improvesCoverage"] is None
    # Validation on a rejected proposal: still deterministic, still no improvement.
    validated = client.post(
        f"/api/runs/{run_id}/rule-proposals/{proposal['id']}/validate").json()
    assert validated["validation"]["improvesCoverage"] is False
    assert validated["validation"]["coverageAfter"] is None


def test_original_rule_never_modified_by_proposal() -> None:
    run_id = _create_run()
    proposal = _propose(run_id, GOOD_S2_PROPOSAL)
    client.post(f"/api/runs/{run_id}/rule-proposals/{proposal['id']}/validate")
    rules = client.get(f"/api/runs/{run_id}/rules").json()["rules"]
    original = next(r for r in rules if r["id"] == "rule_s2_mfa_device_deletion")
    assert original["source"] != GOOD_S2_PROPOSAL
    assert "DeleteVirtualMfaDevice" in original["source"]  # untouched starter rule
    # And the run's coverage is unchanged.
    assert client.get(f"/api/runs/{run_id}/coverage").json()["score"] == 50.0


def test_list_proposals_for_run() -> None:
    run_id = _create_run()
    _propose(run_id, GOOD_S2_PROPOSAL)
    listing = client.get(f"/api/runs/{run_id}/rule-proposals").json()
    assert listing["runId"] == run_id
    assert len(listing["proposals"]) == 1


def test_proposal_for_unknown_run_404() -> None:
    response = client.post("/api/runs/run_missing/rule-proposals", json={
        "originalRuleId": "rule_x", "proposedSource": "title: x",
    })
    assert response.status_code == 404
    assert response.json()["code"] == "RUN_NOT_FOUND"


def test_proposal_missing_fields_400() -> None:
    run_id = _create_run()
    response = client.post(f"/api/runs/{run_id}/rule-proposals", json={})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_validate_unknown_proposal_404() -> None:
    run_id = _create_run()
    response = client.post(f"/api/runs/{run_id}/rule-proposals/prop_missing/validate")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_generate_proposal_deterministic_fallback(monkeypatch) -> None:
    from app.config import settings
    from app.persistence.instance import repository
    monkeypatch.setattr(settings, "nebius_api_key", None)

    run_id = _create_run()
    res = client.post(f"/api/runs/{run_id}/rule-proposals/generate", json={
        "originalRuleId": "rule_s2_mfa_device_deletion",
    })
    assert res.status_code == 201
    data = res.json()

    assert data["status"] == "proposed"
    assert "UpdateMfaPreference" in data["proposedSource"]
    assert data["validation"]["parserStatus"] == "valid"
    assert data["validation"]["improvesCoverage"] is None

    # Check embedded aiArtifact
    artifact = data["aiArtifact"]
    assert artifact["status"] == "unavailable"
    assert artifact["model"] is None
    assert artifact["taskType"] == "rule_proposal"
    assert "event:evt_s2_03" in artifact["output"]["citedEvidenceIds"]

    # Verify repository persistence of the artifact
    stored_artifact = repository.get_ai_artifact(run_id, artifact["id"])
    assert stored_artifact is not None
    assert stored_artifact.task_type == "rule_proposal"

    # Validate that this generated proposal improves coverage from 50 to 60
    val_res = client.post(f"/api/runs/{run_id}/rule-proposals/{data['id']}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["status"] == "validated"
    assert val_data["validation"]["improvesCoverage"] is True
    assert val_data["validation"]["coverageBefore"] == 50.0
    assert val_data["validation"]["coverageAfter"] == 60.0


def test_generate_proposal_live_nemotron_mock(monkeypatch) -> None:
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
                                '{"proposed_source": "title: Detect UpdateMfaPreference\\nid: rule_s2_nemotron_fix\\nstage: S2\\nlogsource:\\n  product: cloud\\n  service: iam\\nselection:\\n  action: UpdateMfaPreference\\ncondition: selection\\nlevel: high",'
                                ' "rationale": "Nemotron proposed rule to detect MFA modification.",'
                                ' "cited_evidence_ids": ["event:evt_s2_03", "rule:rule_s2_mfa_device_deletion"]}'
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

    run_id = _create_run()
    res = client.post(f"/api/runs/{run_id}/rule-proposals/generate", json={
        "originalRuleId": "rule_s2_mfa_device_deletion",
    })
    assert res.status_code == 201
    data = res.json()

    assert data["status"] == "proposed"
    assert data["aiArtifact"]["status"] == "succeeded"
    assert data["aiArtifact"]["model"] == "test-model"
    assert "rule_s2_nemotron_fix" in data["proposedSource"]
    assert "event:evt_s2_03" in data["aiArtifact"]["output"]["citedEvidenceIds"]

    # Validate the Nemotron proposal improves coverage
    val_res = client.post(f"/api/runs/{run_id}/rule-proposals/{data['id']}/validate")
    assert val_res.status_code == 200
    assert val_res.json()["validation"]["improvesCoverage"] is True
    assert val_res.json()["validation"]["coverageAfter"] == 60.0


def test_generate_proposal_unknown_rule_404() -> None:
    run_id = _create_run()
    res = client.post(f"/api/runs/{run_id}/rule-proposals/generate", json={
        "originalRuleId": "rule_nonexistent",
    })
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_cumulative_proposal_validation() -> None:
    run_id = _create_run()
    # First proposal for S2: 50 -> 60
    prop1 = _propose(run_id, GOOD_S2_PROPOSAL, original="rule_s2_mfa_device_deletion")
    val1 = client.post(
        f"/api/runs/{run_id}/rule-proposals/{prop1['id']}/validate?cumulative=true"
    ).json()
    assert val1["validation"]["improvesCoverage"] is True
    assert val1["validation"]["coverageBefore"] == 50.0
    assert val1["validation"]["coverageAfter"] == 60.0

    # Second proposal for S6: fix the broken tor rule with a valid GetObject rule
    good_s6 = """
title: Detect S6 Storage Access
id: rule_s6_storage_access_fixed
stage: S6
logsource:
  product: cloud
  service: storage
selection:
  action: GetObject
condition: selection
level: high
"""
    prop2 = _propose(run_id, good_s6, original="rule_s6_tor_exit_access")
    val2 = client.post(
        f"/api/runs/{run_id}/rule-proposals/{prop2['id']}/validate?cumulative=true"
    ).json()
    assert val2["validation"]["improvesCoverage"] is True
    assert val2["validation"]["coverageBefore"] == 60.0
    assert val2["validation"]["coverageAfter"] == 75.0