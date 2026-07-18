from __future__ import annotations

from pathlib import Path

from app.database import Database


def test_sqlite_persists_across_restart(tmp_path: Path, confirmed_incident: dict) -> None:
    path = tmp_path / "persist.db"
    database = Database(path)
    database.initialize()
    database.upsert_incident(confirmed_incident, "ignis-qnxpi-01", "boot-test")
    database.add_event(confirmed_incident["incident_id"], "CONFIRMED", "qnx", {})
    database.close()

    reopened = Database(path)
    reopened.initialize()
    incident = reopened.get_incident(confirmed_incident["incident_id"])
    assert incident is not None
    assert incident["hazard_state"] == "CONFIRMED"
    assert len(reopened.list_events(confirmed_incident["incident_id"])) == 1
    reopened.close()


def test_device_replay_does_not_downgrade_backend_escalation(
    tmp_path: Path, confirmed_incident: dict
) -> None:
    database = Database(tmp_path / "authority.db")
    database.initialize()
    database.upsert_incident(confirmed_incident, "ignis-qnxpi-01", "boot-test")
    database.update_incident_response(
        confirmed_incident["incident_id"], "ESCALATING", "no_response"
    )
    database.upsert_incident(confirmed_incident, "ignis-qnxpi-01", "boot-test")
    stored = database.get_incident(confirmed_incident["incident_id"])
    assert stored is not None
    assert stored["response_state"] == "ESCALATING"
    assert stored["occupant_response"] == "no_response"
    database.close()
