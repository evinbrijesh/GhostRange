"""Tests for Tavily threat intelligence endpoints and fallback."""

from fastapi.testclient import TestClient

from app.ai import tavily as tavily_module
from app.config import settings
from app.main import app

client = TestClient(app)


def test_stage_threat_intel_deterministic_fallback(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", None)
    res = client.get("/api/threat-intel/stages/S2")
    assert res.status_code == 200
    data = res.json()

    assert data["stageId"] == "S2"
    assert data["techniqueId"] == "T1556"
    assert data["liveSearch"] is False
    assert "Modify Authentication Process" in data["techniqueName"]
    assert len(data["sources"]) > 0
    assert "mitre.org" in data["sources"][0]["url"]


def test_threat_intel_search_live_mock(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "tvly-test-key")

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "answer": "Scattered Spider abuses cloud identity MFA modifications via Okta and AWS.",
                "results": [
                    {
                        "title": "Adversary TTPs in Cloud Compromises",
                        "url": "https://example.com/adversary-mfa",
                        "content": "Detailed telemetry on MFA preference updates and session token theft.",
                    }
                ],
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

    monkeypatch.setattr(tavily_module.httpx, "Client", FakeHttpClient)

    res = client.get("/api/threat-intel/stages/S2")
    assert res.status_code == 200
    data = res.json()

    assert data["liveSearch"] is True
    assert "Scattered Spider abuses cloud identity" in data["summary"]
    assert len(data["sources"]) == 1
    assert data["sources"][0]["title"] == "Adversary TTPs in Cloud Compromises"
    assert data["sources"][0]["url"] == "https://example.com/adversary-mfa"
