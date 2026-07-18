from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


class DatabaseError(RuntimeError):
    pass


class CallPolicyError(DatabaseError):
    pass


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, check_same_thread=False, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                boot_id TEXT NOT NULL,
                software_version TEXT NOT NULL,
                connected INTEGER NOT NULL DEFAULT 0,
                connected_at TEXT,
                disconnected_at TEXT,
                last_seen_at TEXT NOT NULL,
                capabilities_json TEXT NOT NULL DEFAULT '[]',
                health_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                boot_id TEXT NOT NULL,
                hazard_state TEXT NOT NULL,
                response_state TEXT NOT NULL,
                first_detection_monotonic_ns INTEGER,
                updated_monotonic_ns INTEGER,
                first_detected_at TEXT,
                confirmed_at TEXT,
                resolved_at TEXT,
                first_zone TEXT,
                current_zone TEXT,
                peak_fire_confidence REAL NOT NULL DEFAULT 0,
                peak_smoke_confidence REAL NOT NULL DEFAULT 0,
                max_growth_percent REAL,
                smoke_first INTEGER,
                smoke_to_fire_delay_seconds REAL,
                seconds_persistent REAL NOT NULL DEFAULT 0,
                occupant_visible INTEGER,
                occupant_response TEXT,
                call_status TEXT,
                call_conversation_id TEXT,
                call_sid TEXT,
                primary_fire_bbox_json TEXT,
                primary_smoke_bbox_json TEXT,
                evidence_path TEXT,
                camera_health TEXT,
                inference_health TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS incident_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                device_monotonic_ns INTEGER,
                occurred_at TEXT,
                received_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS call_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                destination_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                provider_conversation_id TEXT,
                provider_call_sid TEXT,
                requested_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error_code TEXT,
                error_message_safe TEXT,
                FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS configurations (
                key TEXT PRIMARY KEY,
                version INTEGER NOT NULL,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_incidents_updated ON incidents(updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_incident ON incident_events(incident_id, id);
            CREATE INDEX IF NOT EXISTS idx_calls_requested ON call_attempts(requested_at DESC);
            """
        )
        connection.commit()
        self._connection = connection

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    @contextmanager
    def _tx(self, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        if self._connection is None:
            raise DatabaseError("database is not initialized")
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
                yield self._connection
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def _all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        if self._connection is None:
            raise DatabaseError("database is not initialized")
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        return [self._decode_row(dict(row)) for row in rows]

    def _one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self._all(sql, params)
        return rows[0] if rows else None

    @staticmethod
    def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
        for key in tuple(row):
            if key.endswith("_json"):
                raw = row.pop(key)
                target = key[:-5]
                try:
                    row[target] = json.loads(raw) if raw is not None else None
                except json.JSONDecodeError:
                    row[target] = None
        for key in ("connected", "smoke_first", "occupant_visible"):
            if key in row and row[key] is not None:
                row[key] = bool(row[key])
        return row

    def upsert_device(self, hello: dict[str, Any], connected: bool = True) -> None:
        now = utc_now()
        with self._tx():
            self._connection.execute(
                """
                INSERT INTO devices (
                    device_id, boot_id, software_version, connected, connected_at,
                    disconnected_at, last_seen_at, capabilities_json, health_json
                ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, '{}')
                ON CONFLICT(device_id) DO UPDATE SET
                    boot_id=excluded.boot_id,
                    software_version=excluded.software_version,
                    connected=excluded.connected,
                    connected_at=excluded.connected_at,
                    disconnected_at=NULL,
                    last_seen_at=excluded.last_seen_at,
                    capabilities_json=excluded.capabilities_json
                """,
                (
                    hello["device_id"],
                    hello["boot_id"],
                    hello.get("software_version", "unknown"),
                    int(connected),
                    now,
                    now,
                    _json(hello.get("capabilities", [])),
                ),
            )

    def mark_device_disconnected(self, device_id: str, boot_id: str) -> None:
        now = utc_now()
        with self._tx():
            self._connection.execute(
                """
                UPDATE devices SET connected=0, disconnected_at=?, last_seen_at=?
                WHERE device_id=? AND boot_id=?
                """,
                (now, now, device_id, boot_id),
            )

    def update_health(self, device_id: str, health: dict[str, Any]) -> None:
        with self._tx():
            self._connection.execute(
                "UPDATE devices SET health_json=?, last_seen_at=? WHERE device_id=?",
                (_json(health), utc_now(), device_id),
            )

    def list_devices(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM devices ORDER BY device_id")

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM devices WHERE device_id=?", (device_id,))

    def upsert_incident(self, data: dict[str, Any], default_device_id: str, boot_id: str) -> None:
        now = utc_now()
        state = data["hazard_state"]
        confirmed_at = now if state == "CONFIRMED" else None
        resolved_at = now if state == "RESOLVED" else None
        smoke_first = data.get("smoke_first")
        occupant_visible = data.get("occupant_visible")
        growth = data.get("fire_region_growth_percent")
        with self._tx():
            self._connection.execute(
                """
                INSERT INTO incidents (
                    incident_id, device_id, boot_id, hazard_state, response_state,
                    first_detection_monotonic_ns, updated_monotonic_ns, first_detected_at,
                    confirmed_at, resolved_at, first_zone, current_zone,
                    peak_fire_confidence, peak_smoke_confidence, max_growth_percent,
                    smoke_first, smoke_to_fire_delay_seconds, seconds_persistent,
                    occupant_visible, primary_fire_bbox_json, primary_smoke_bbox_json,
                    camera_health, inference_health, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    hazard_state=excluded.hazard_state,
                    response_state=CASE
                        WHEN incidents.response_state IN (
                            'CANCELLED','ESCALATING','CALL_REQUESTED','CALL_INITIATED',
                            'CALL_CONNECTED','CALL_COMPLETED','CALL_FAILED')
                        THEN incidents.response_state ELSE excluded.response_state END,
                    updated_monotonic_ns=MAX(
                        incidents.updated_monotonic_ns, excluded.updated_monotonic_ns),
                    confirmed_at=COALESCE(incidents.confirmed_at, excluded.confirmed_at),
                    resolved_at=COALESCE(excluded.resolved_at, incidents.resolved_at),
                    current_zone=excluded.current_zone,
                    peak_fire_confidence=MAX(
                        incidents.peak_fire_confidence, excluded.peak_fire_confidence),
                    peak_smoke_confidence=MAX(
                        incidents.peak_smoke_confidence, excluded.peak_smoke_confidence),
                    max_growth_percent=CASE
                        WHEN excluded.max_growth_percent IS NULL THEN incidents.max_growth_percent
                        WHEN incidents.max_growth_percent IS NULL THEN excluded.max_growth_percent
                        ELSE MAX(incidents.max_growth_percent, excluded.max_growth_percent) END,
                    smoke_first=COALESCE(incidents.smoke_first, excluded.smoke_first),
                    smoke_to_fire_delay_seconds=COALESCE(
                        incidents.smoke_to_fire_delay_seconds,
                        excluded.smoke_to_fire_delay_seconds),
                    seconds_persistent=MAX(
                        incidents.seconds_persistent, excluded.seconds_persistent),
                    occupant_visible=COALESCE(
                        excluded.occupant_visible, incidents.occupant_visible),
                    primary_fire_bbox_json=COALESCE(
                        excluded.primary_fire_bbox_json, incidents.primary_fire_bbox_json),
                    primary_smoke_bbox_json=COALESCE(
                        excluded.primary_smoke_bbox_json, incidents.primary_smoke_bbox_json),
                    camera_health=excluded.camera_health,
                    inference_health=excluded.inference_health,
                    updated_at=excluded.updated_at
                """,
                (
                    data["incident_id"],
                    data.get("device_id") or default_device_id,
                    data.get("boot_id") or boot_id,
                    state,
                    data["response_state"],
                    data.get("first_detection_monotonic_ns"),
                    data.get("updated_monotonic_ns"),
                    now,
                    confirmed_at,
                    resolved_at,
                    data.get("first_zone", "Unconfigured area"),
                    data.get("current_zone", "Unconfigured area"),
                    data.get("fire_confidence", 0),
                    data.get("smoke_confidence", 0),
                    growth,
                    None if smoke_first is None else int(smoke_first),
                    data.get("smoke_to_fire_delay_seconds"),
                    data.get("seconds_persistent", 0),
                    None if occupant_visible is None else int(occupant_visible),
                    _json(data.get("primary_fire_bbox")) if data.get("primary_fire_bbox") else None,
                    _json(data.get("primary_smoke_bbox"))
                    if data.get("primary_smoke_bbox")
                    else None,
                    data.get("camera_health", "UNKNOWN"),
                    data.get("inference_health", "UNKNOWN"),
                    now,
                    now,
                ),
            )

    def list_incidents(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM incidents ORDER BY updated_at DESC LIMIT ?", (limit,))

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM incidents WHERE incident_id=?", (incident_id,))

    def add_event(
        self,
        incident_id: str,
        event_type: str,
        source: str,
        payload: dict[str, Any],
        monotonic_ns: int | None = None,
        occurred_at: str | None = None,
    ) -> dict[str, Any]:
        received_at = utc_now()
        with self._tx():
            cursor = self._connection.execute(
                """
                INSERT INTO incident_events (
                    incident_id, event_type, source, device_monotonic_ns,
                    occurred_at, received_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident_id,
                    event_type[:80],
                    source[:40],
                    monotonic_ns,
                    occurred_at,
                    received_at,
                    _json(payload),
                ),
            )
            event_id = cursor.lastrowid
        return self._one("SELECT * FROM incident_events WHERE id=?", (event_id,)) or {}

    def list_events(self, incident_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM incident_events WHERE incident_id=? ORDER BY id", (incident_id,)
        )

    def update_incident_response(
        self,
        incident_id: str,
        response_state: str,
        occupant_response: str | None = None,
        hazard_state: str | None = None,
    ) -> dict[str, Any]:
        if self.get_incident(incident_id) is None:
            raise DatabaseError("incident not found")
        with self._tx():
            if hazard_state:
                self._connection.execute(
                    """
                    UPDATE incidents SET response_state=?, occupant_response=?, hazard_state=?,
                        resolved_at=CASE WHEN ?='RESOLVED' THEN ? ELSE resolved_at END, updated_at=?
                    WHERE incident_id=?
                    """,
                    (
                        response_state,
                        occupant_response,
                        hazard_state,
                        hazard_state,
                        utc_now(),
                        utc_now(),
                        incident_id,
                    ),
                )
            else:
                self._connection.execute(
                    """
                    UPDATE incidents SET response_state=?,
                        occupant_response=COALESCE(?, occupant_response),
                        updated_at=? WHERE incident_id=?
                    """,
                    (response_state, occupant_response, utc_now(), incident_id),
                )
        return self.get_incident(incident_id) or {}

    def reserve_call_attempt(
        self,
        incident_id: str,
        destination_hash: str,
        cooldown_seconds: int,
        max_calls: int,
    ) -> int:
        now = datetime.now(UTC)
        active_statuses = ("REQUESTED", "INITIATED", "UNKNOWN", "CONNECTED", "COMPLETED")
        with self._tx(immediate=True):
            incident = self._connection.execute(
                "SELECT * FROM incidents WHERE incident_id=?", (incident_id,)
            ).fetchone()
            if incident is None:
                raise CallPolicyError("incident_not_found")
            if incident["confirmed_at"] is None:
                raise CallPolicyError("incident_not_visually_confirmed")
            if incident["response_state"] == "CANCELLED":
                raise CallPolicyError("incident_cancelled")
            placeholders = ",".join("?" for _ in active_statuses)
            count = self._connection.execute(
                "SELECT COUNT(*) FROM call_attempts WHERE incident_id=? "
                f"AND status IN ({placeholders})",
                (incident_id, *active_statuses),
            ).fetchone()[0]
            if count >= max_calls:
                raise CallPolicyError("duplicate_or_max_calls_reached")
            latest = self._connection.execute(
                f"SELECT requested_at FROM call_attempts WHERE status IN ({placeholders}) "
                "ORDER BY requested_at DESC LIMIT 1",
                active_statuses,
            ).fetchone()
            if latest is not None:
                latest_time = datetime.fromisoformat(latest[0])
                if latest_time + timedelta(seconds=cooldown_seconds) > now:
                    raise CallPolicyError("global_call_cooldown")
            timestamp = now.isoformat()
            cursor = self._connection.execute(
                """
                INSERT INTO call_attempts (
                    incident_id, destination_hash, status, requested_at, updated_at
                ) VALUES (?, ?, 'REQUESTED', ?, ?)
                """,
                (incident_id, destination_hash, timestamp, timestamp),
            )
            self._connection.execute(
                "UPDATE incidents SET response_state='CALL_REQUESTED', call_status='REQUESTED', "
                "updated_at=? WHERE incident_id=?",
                (timestamp, incident_id),
            )
            return int(cursor.lastrowid)

    def update_call_attempt(
        self,
        attempt_id: int,
        status: str,
        conversation_id: str | None = None,
        call_sid: str | None = None,
        error_code: str | None = None,
        error_message_safe: str | None = None,
    ) -> dict[str, Any]:
        mapping = {
            "INITIATED": "CALL_INITIATED",
            "UNKNOWN": "CALL_INITIATED",
            "CONNECTED": "CALL_CONNECTED",
            "COMPLETED": "CALL_COMPLETED",
            "FAILED": "CALL_FAILED",
        }
        with self._tx():
            self._connection.execute(
                """
                UPDATE call_attempts SET status=?, provider_conversation_id=?,
                    provider_call_sid=?, error_code=?, error_message_safe=?, updated_at=? WHERE id=?
                """,
                (
                    status,
                    conversation_id,
                    call_sid,
                    error_code,
                    error_message_safe,
                    utc_now(),
                    attempt_id,
                ),
            )
            attempt = self._connection.execute(
                "SELECT incident_id FROM call_attempts WHERE id=?", (attempt_id,)
            ).fetchone()
            if attempt is None:
                raise DatabaseError("call attempt not found")
            self._connection.execute(
                """
                UPDATE incidents SET response_state=?, call_status=?,
                    call_conversation_id=COALESCE(?, call_conversation_id),
                    call_sid=COALESCE(?, call_sid), updated_at=? WHERE incident_id=?
                """,
                (
                    mapping[status],
                    status,
                    conversation_id,
                    call_sid,
                    utc_now(),
                    attempt["incident_id"],
                ),
            )
        return self._one("SELECT * FROM call_attempts WHERE id=?", (attempt_id,)) or {}

    def find_attempt_for_incident(self, incident_id: str) -> dict[str, Any] | None:
        return self._one(
            "SELECT * FROM call_attempts WHERE incident_id=? ORDER BY id DESC LIMIT 1",
            (incident_id,),
        )

    def put_configuration(self, key: str, version: int, value: dict[str, Any]) -> None:
        with self._tx():
            current = self._connection.execute(
                "SELECT version FROM configurations WHERE key=?", (key,)
            ).fetchone()
            if current is not None and version <= current[0]:
                raise DatabaseError("configuration version must increase")
            self._connection.execute(
                """
                INSERT INTO configurations(key, version, value_json, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET version=excluded.version,
                    value_json=excluded.value_json, updated_at=excluded.updated_at
                """,
                (key, version, _json(value), utc_now()),
            )

    def get_configuration(self, key: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM configurations WHERE key=?", (key,))
        if not row:
            return None
        return row.get("value")
