"""Run lifecycle APIs: creation, graph, telemetry, coverage, errors, reproducibility."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SCENARIO_ID = "cloud-identity-compromise-v1"


def _create_run(seed: int | None = None) -> dict:
    body = {"scenarioId": SCENARIO_ID}
    if seed is not None:
        body["seed"] = seed
    response = client.post("/api/runs", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_run_completes() -> None:
    run = _create_run()
    assert run["status"] == "completed"
    assert run["scenarioId"] == SCENARIO_ID
    assert run["seed"] == 1337
    assert run["error"] is None
    assert run["startedAt"] and run["completedAt"]


def test_run_lifecycle_states_are_explicit() -> None:
    run = _create_run()
    fetched = client.get(f"/api/runs/{run['id']}").json()
    assert fetched["status"] in {"queued", "running", "completed", "failed"}


def test_graph_reports_all_seven_stages() -> None:
    run = _create_run()
    graph = client.get(f"/api/runs/{run['id']}/graph").json()
    assert graph["runId"] == run["id"]
    assert [s["stageId"] for s in graph["stages"]] == [f"S{i}" for i in range(1, 8)]
    statuses = {s["stageId"]: s["status"] for s in graph["stages"]}
    assert statuses["S1"] == "detected"
    assert statuses["S4"] == "partial"
    assert statuses["S2"] == "missed"


def test_telemetry_endpoint_and_filters() -> None:
    run = _create_run()
    page = client.get(f"/api/runs/{run['id']}/telemetry").json()
    assert page["total"] > 0
    assert all(e["synthetic"] is True for e in page["events"])

    s4 = client.get(f"/api/runs/{run['id']}/telemetry", params={"stage": "S4"}).json()
    assert all(e["stageId"] == "S4" for e in s4["events"])

    expected_only = client.get(f"/api/runs/{run['id']}/telemetry", params={"expected": True}).json()
    assert all(e["expected"] is True for e in expected_only["events"])


def test_coverage_endpoint_matches_expected_demo_score() -> None:
    run = _create_run()
    coverage = client.get(f"/api/runs/{run['id']}/coverage").json()
    assert coverage["score"] == 50.0
    assert coverage["stageCounts"] == {"detected": 3, "partial": 1, "missed": 3, "error": 0}
    assert coverage["formulaVersion"] == "coverage-v1"
    assert len(coverage["evaluatorErrors"]) == 1  # the intentionally invalid rule


def test_same_seed_reproduces_same_coverage() -> None:
    first = client.get(f"/api/runs/{_create_run(1337)['id']}/coverage").json()
    second = client.get(f"/api/runs/{_create_run(1337)['id']}/coverage").json()
    assert first["score"] == second["score"]
    assert [s["matchedEventIds"] for s in first["stages"]] == [
        s["matchedEventIds"] for s in second["stages"]
    ]


def test_unknown_run_returns_stable_error_envelope() -> None:
    response = client.get("/api/runs/run_does_not_exist")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "RUN_NOT_FOUND"
    assert "message" in body
    assert "Traceback" not in body["message"]


def test_unknown_scenario_rejected() -> None:
    response = client.post("/api/runs", json={"scenarioId": "nope"})
    assert response.status_code == 404
    assert response.json()["code"] == "SCENARIO_NOT_FOUND"


def test_invalid_body_rejected_with_validation_error() -> None:
    response = client.post("/api/runs", json={})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_scenarios_endpoints() -> None:
    listing = client.get("/api/scenarios").json()
    assert listing == [{"id": SCENARIO_ID, "name": "Cloud Identity Compromise",
                        "version": "1.0.0", "stageCount": 7, "available": True}]
    detail = client.get(f"/api/scenarios/{SCENARIO_ID}").json()
    assert len(detail["stages"]) == 7
    assert detail["syntheticOnly"] is True