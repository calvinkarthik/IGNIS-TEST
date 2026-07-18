from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from ignis_simulator.protocol import PacketType, packet  # noqa: E402

from app.protocol import PacketParser as BackendParser  # noqa: E402
from app.protocol import PacketType as BackendType  # noqa: E402


def test_simulator_packet_is_backend_compatible() -> None:
    encoded = packet(PacketType.HEALTH_UPDATE, {"camera": "HEALTHY"}, 7, 99)
    decoded = BackendParser().feed(encoded)[0]
    assert decoded.packet_type == BackendType.HEALTH_UPDATE
    assert decoded.sequence == 7
    assert decoded.monotonic_ns == 99
    assert decoded.json() == {"camera": "HEALTHY"}

