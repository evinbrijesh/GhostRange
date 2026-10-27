"""Tests for POST /api/runs/{run_id}/explanations."""

from fastapi.testclient import TestClient

from app.ai import client as ai_client
from app.api.pipeline import execute_run
from app.config import settings
from app.domain.detections.loader import load_default_rules
from app.domain.scenarios.loader import load_default_scenario
from app.main import app
from app.persistence.instance import repository
from app.persistence.models import Run, now_utc
from app.shared.ids import new_id
from app.shared.vocab import RunStatus

client = TestClient(app)


def _save_run() -> Run:
    scenario = load_default_scenario()
    rules = [r.source for r, _ in load_default_rules()]
    run = Run(
        id=new_id("run"),
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        seed=1337,
        status=RunStatus.COMPLETED,
        created_at=now_utc(),
        completed_at=now_utc(),
    )
    record = execute_run(scenario, rules, run)
    repository.save_run(record)
    return run


def test_stage_explanation_endpoint_grounded_response(monkeypatch):
    monkeypatch.setattr(settings, "nebius_api_key", None)
    run = _save_run()

    res = client.post(f"/api/runs/{run.id}/explanations", json={"stageId": "S2"})
    assert res.status_code == 200
    data = res.json()

    assert data["runId"] == run.id
    assert data["stageId"] == "S2"
    assert data["taskType"] == "explanation"
    assert data["status"] == "unavailable"
    assert data["model"] is None

    # inputEvidenceIds is the evidence supplied to the analysis.
    assert "event:evt_s2_03" in data["inputEvidenceIds"]
    assert "rule:rule_s2_mfa_device_deletion" in data["inputEvidenceIds"]
    for cid in data["inputEvidenceIds"]:
        assert cid.startswith(("event:", "rule:"))

    # Citations are the deterministic mismatch evidence, never invented IDs.
    observed_ids = [
        item["evidenceId"] for item in data["explanation"]["evidenceObserved"]
    ]
    assert set(observed_ids) == {
        "event:evt_s2_03",
        "rule:rule_s2_mfa_device_deletion",
    }
    assert all(cid in data["inputEvidenceIds"] for cid in observed_ids)

    assert "Deterministic fallback analysis" in data["explanation"]["summary"]
    assert "gr-rule-" not in data["explanation"]["recommendedRemediation"]
    assert "rule_s2_mfa_device_deletion" in data["explanation"]["recommendedRemediation"]

    # Verify AIArtifact persistence
    stored = repository.get_ai_artifact(run.id, data["id"])
    assert stored is not None
    assert stored.model is None
    assert stored.status == "unavailable"
    assert stored.task_type == "explanation"
    assert stored.output["summary"] == data["explanation"]["summary"]

    list_res = client.get(f"/api/runs/{run.id}/explanations")
    assert list_res.status_code == 200
    assert any(exp["id"] == data["id"] for exp in list_res.json()["explanations"])

    list_art = client.get(f"/api/runs/{run.id}/ai-artifacts")
    assert list_art.status_code == 200
    assert any(art["id"] == data["id"] for art in list_art.json()["artifacts"])


def test_live_model_citations_are_filtered_to_supplied_evidence(monkeypatch):
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
                                '{"summary": "Observed MFA change.",'
                                ' "gap_analysis": "Rule expected deletion.",'
                                ' "recommended_remediation": "Match the observed action.",'
                                ' "cited_evidence_ids": ["event:evt_test", "event:invented"]}'
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

    result = ai_client.explain_stage_with_nemotron(
        stage_id="S2",
        stage_name="MFA manipulation",
        status="missed",
        events=[
            {
                "id": "evt_test",
                "expected": True,
                "action": "UpdateMfaPreference",
                "identity": {"id": "user-test"},
                "resource": {"id": "user-test"},
            }
        ],
        rules=[{"id": "rule_test", "title": "Test rule", "stage_id": "S2"}],
        mismatches=[
            {
                "rule_id": "rule_test",
                "event_id": "evt_test",
                "failed_expressions": [
                    {
                        "field": "action",
                        "operator": "exact",
                        "expected": "DeleteVirtualMfaDevice",
                        "actual": "UpdateMfaPreference",
                    }
                ],
            }
        ],
    )

    assert result["status"] == "succeeded"
    assert result["model"] == "test-model"
    assert result["cited_evidence_ids"] == ["event:evt_test"]


def test_ungrounded_model_output_falls_back_without_fake_attribution(monkeypatch):
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
                                '{"summary": "Ungrounded claim.",'
                                ' "gap_analysis": "",'
                                ' "recommended_remediation": "",'
                                ' "cited_evidence_ids": []}'
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

    result = ai_client.explain_stage_with_nemotron(
        stage_id="S2",
        stage_name="MFA manipulation",
        status="missed",
        events=[
            {
                "id": "evt_test",
                "expected": True,
                "action": "UpdateMfaPreference",
                "identity": {"id": "user-test"},
                "resource": {"id": "user-test"},
            }
        ],
        rules=[{"id": "rule_test", "title": "Test rule", "stage_id": "S2"}],
        mismatches=[
            {
                "rule_id": "rule_test",
                "event_id": "evt_test",
                "failed_expressions": [
                    {
                        "field": "action",
                        "operator": "exact",
                        "expected": "DeleteVirtualMfaDevice",
                        "actual": "UpdateMfaPreference",
                    }
                ],
            }
        ],
    )

    assert result["status"] == "failed"
    assert result["model"] is None
    assert "rejected" in result["summary"]
    # Deterministic fallback may cite the actual mismatch evidence, but never
    # backfills citations the model did not provide.
    assert result["cited_evidence_ids"] == ["rule:rule_test", "event:evt_test"]
    assert "Ungrounded claim." not in result["summary"]


def test_stage_explanation_invalid_stage():
    run = _save_run()

    res = client.post(f"/api/runs/{run.id}/explanations", json={"stageId": "S99"})
    assert res.status_code == 404
