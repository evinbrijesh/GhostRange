"""Tests for POST /api/runs/{run_id}/explanations."""

from fastapi.testclient import TestClient

from app.api.pipeline import execute_run
from app.domain.detections.loader import load_default_rules
from app.domain.scenarios.loader import load_default_scenario
from app.main import app
from app.persistence.instance import repository
from app.persistence.models import Run, now_utc
from app.shared.ids import new_id
from app.shared.vocab import RunStatus

client = TestClient(app)


def test_stage_explanation_endpoint_grounded_response():
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

    # Request explanation for stage S2 (MFA manipulation, missed stage)
    res = client.post(f"/api/runs/{run.id}/explanations", json={"stageId": "S2"})
    assert res.status_code == 200
    data = res.json()

    assert data["runId"] == run.id
    assert data["stageId"] == "S2"
    assert data["taskType"] == "explanation"
    assert "explanation" in data
    assert "summary" in data["explanation"]
    assert "gapAnalysis" in data["explanation"]
    assert "recommendedRemediation" in data["explanation"]
    assert len(data["inputEvidenceIds"]) > 0
    # Every cited ID must start with event: or rule:
    for cid in data["inputEvidenceIds"]:
        assert cid.startswith("event:") or cid.startswith("rule:")


def test_stage_explanation_invalid_stage():
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

    res = client.post(f"/api/runs/{run.id}/explanations", json={"stageId": "S99"})
    assert res.status_code == 404
