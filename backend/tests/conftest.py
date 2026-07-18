from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        qnx_tcp_host="127.0.0.1",
        qnx_tcp_port=0,
        device_token="test-device-token",
        database_url=f"sqlite:///{tmp_path / 'ignis.db'}",
        incident_storage_root=tmp_path / "incidents",
        response_timeout_seconds=30,
    )


@pytest.fixture
def client(settings: Settings):
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def confirmed_incident() -> dict:
    return {
        "incident_id": "ignis-qnxpi-01-boot-test-1",
        "device_id": "ignis-qnxpi-01",
        "boot_id": "boot-test",
        "hazard_state": "CONFIRMED",
        "response_state": "AWAITING_RESPONSE",
        "first_detection_monotonic_ns": 1_000_000_000,
        "updated_monotonic_ns": 6_000_000_000,
        "fire_confidence": 0.91,
        "smoke_confidence": 0.76,
        "seconds_persistent": 5.0,
        "first_zone": "Stovetop",
        "current_zone": "Stovetop",
        "primary_fire_bbox": [0.2, 0.2, 0.5, 0.6],
        "primary_smoke_bbox": [0.15, 0.1, 0.6, 0.7],
        "fire_region_growth_percent": 38.0,
        "smoke_first": True,
        "smoke_to_fire_delay_seconds": 4.1,
        "occupant_visible": None,
        "camera_health": "HEALTHY",
        "inference_health": "HEALTHY",
    }

