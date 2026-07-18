from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def test_allowlisted_mock_call_and_duplicate_blocked(
    settings: Settings, confirmed_incident: dict
) -> None:
    settings.demo_calls_enabled = True
    settings.demo_dispatch_number = "+14165550123"
    settings.demo_allowed_numbers = ("+14165550123",)
    settings.call_provider = "mock"
    with make_client(settings) as client:
        client.app.state.database.upsert_incident(
            confirmed_incident, "ignis-qnxpi-01", "boot-test"
        )
        incident_id = confirmed_incident["incident_id"]
        first = client.post(f"/api/incidents/{incident_id}/call-demo-dispatch")
        assert first.status_code == 200
        assert first.json()["status"] == "CALL_REQUEST_ACCEPTED"
        assert first.json()["connection_status"] == "UNKNOWN"
        second = client.post(f"/api/incidents/{incident_id}/call-demo-dispatch")
        assert second.status_code == 409


def test_non_allowlisted_and_emergency_numbers_are_rejected(
    settings: Settings, confirmed_incident: dict
) -> None:
    settings.demo_calls_enabled = True
    settings.call_provider = "mock"
    settings.demo_dispatch_number = "+14165550911"
    settings.demo_allowed_numbers = ("+14165550911",)
    with make_client(settings) as client:
        client.app.state.database.upsert_incident(
            confirmed_incident, "ignis-qnxpi-01", "boot-test"
        )
        response = client.post(
            f"/api/incidents/{confirmed_incident['incident_id']}/call-demo-dispatch"
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "emergency_numbers_are_forbidden"

