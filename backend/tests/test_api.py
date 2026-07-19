from __future__ import annotations

from fastapi.testclient import TestClient


def seed(client: TestClient, incident: dict) -> str:
    client.app.state.database.upsert_incident(
        incident, incident["device_id"], incident["boot_id"]
    )
    return incident["incident_id"]


def test_health_and_websocket_snapshot(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["backend"] == "HEALTHY"
    assert response.json()["demo_system"] is True
    assert response.json()["armed"] is False
    with client.websocket_connect("/ws/live") as websocket:
        snapshot = websocket.receive_json()
        assert snapshot["type"] == "system_snapshot"
        assert snapshot["data"]["demo_system"] is True
        assert snapshot["data"]["armed"] is False


def test_arming_state_updates(client: TestClient) -> None:
    assert client.get("/api/arming").json() == {"armed": False}
    response = client.put("/api/arming", json={"armed": True})
    assert response.status_code == 200
    assert response.json() == {"armed": True}
    assert client.get("/api/health").json()["armed"] is True


def test_confirm_cancel_and_reset_contracts(
    client: TestClient, confirmed_incident: dict
) -> None:
    incident_id = seed(client, confirmed_incident)
    confirmed = client.post(
        f"/api/incidents/{incident_id}/confirm",
        json={"source": "manual", "note": "Occupant confirmed"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["incident"]["response_state"] == "ESCALATING"

    cancelled = client.post(
        f"/api/incidents/{incident_id}/cancel",
        json={"source": "manual", "reason": "controlled_flame", "note": "Cooking"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["incident"]["response_state"] == "CANCELLED"
    assert cancelled.json()["incident"]["hazard_state"] == "CONFIRMED"

    reset = client.post(
        f"/api/incidents/{incident_id}/reset", json={"source": "manual", "note": "reviewed"}
    )
    assert reset.status_code == 200
    assert reset.json()["incident"]["hazard_state"] == "RESOLVED"
    events = client.get(f"/api/incidents/{incident_id}/events").json()
    assert [event["event_type"] for event in events] == [
        "OCCUPANT_CONFIRMED",
        "ESCALATION_CANCELLED",
        "MANUAL_RESET",
    ]


def test_calls_are_disabled_by_default(client: TestClient, confirmed_incident: dict) -> None:
    incident_id = seed(client, confirmed_incident)
    response = client.post(f"/api/incidents/{incident_id}/call-demo-dispatch")
    assert response.status_code == 409
    assert response.json()["detail"] == "system_unarmed"


def test_zones_validate_and_versions_increase(client: TestClient) -> None:
    zones = client.get("/api/config/zones").json()
    assert zones["configuration_version"] == 1
    zones["configuration_version"] = 2
    zones["zones"][0]["name"] = "Cooktop"
    saved = client.put("/api/config/zones", json=zones)
    assert saved.status_code == 200
    stale = client.put("/api/config/zones", json=zones)
    assert stale.status_code == 409


def test_signed_url_never_leaks_key(client: TestClient, confirmed_incident: dict) -> None:
    incident_id = seed(client, confirmed_incident)
    response = client.get(f"/api/voice/signed-url?incident_id={incident_id}")
    assert response.status_code == 409
    assert "api_key" not in response.text.lower()

