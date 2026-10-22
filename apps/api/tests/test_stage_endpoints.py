"""Stage-inspection endpoints: rules snapshot and stage detail."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SCENARIO_ID = "cloud-identity-compromise-v1"


def _demo_run_id() -> str:
    response = client.post("/api/runs", json={"scenarioId": SCENARIO_ID})
    assert response.status_code == 201
    return response.json()["id"]


def test_rules_endpoint_returns_run_snapshot() -> None:
    run_id = _demo_run_id()
    body = client.get(f"/api/runs/{run_id}/rules").json()
    assert body["runId"] == run_id
    rules = body["rules"]
    assert len(rules) == 7
    statuses = {r["id"]: r["parserStatus"] for r in rules}
    assert statuses["rule_s6_tor_exit_access"] == "invalid"
    invalid = next(r for r in rules if r["id"] == "rule_s6_tor_exit_access")
    assert invalid["parserErrors"], "invalid rule must carry its parser errors"
    assert all(status == "valid" for rid, status in statuses.items()
               if rid != "rule_s6_tor_exit_access")


def test_stage_detail_returns_result_and_events() -> None:
    run_id = _demo_run_id()
    body = client.get(f"/api/runs/{run_id}/stages/S2").json()
    assert body["runId"] == run_id
    assert body["stageId"] == "S2"
    assert body["name"] == "MFA manipulation"
    assert body["result"]["status"] == "missed"
    assert body["result"]["mismatches"], "missed stage must carry mismatch reasons"
    assert all(e["stageId"] == "S2" for e in body["events"])
    assert body["events"], "stage detail must include the stage's events"


def test_stage_detail_partial_stage_has_mismatches() -> None:
    run_id = _demo_run_id()
    body = client.get(f"/api/runs/{run_id}/stages/S4").json()
    assert body["result"]["status"] == "partial"
    mismatch_events = {m["eventId"] for m in body["result"]["mismatches"]}
    assert "evt_s4_10" in mismatch_events


def test_unknown_stage_returns_stable_error() -> None:
    run_id = _demo_run_id()
    response = client.get(f"/api/runs/{run_id}/stages/S99")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_unknown_run_propagates_run_error() -> None:
    response = client.get("/api/runs/run_missing/stages/S1")
    assert response.status_code == 404
    assert response.json()["code"] == "RUN_NOT_FOUND"