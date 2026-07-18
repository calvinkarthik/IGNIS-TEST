from __future__ import annotations

import socket

from ignis_poc.edge import BackendStream
from ignis_poc.protocol import PacketType


def test_laptop_outage_does_not_raise_from_edge_loop(monkeypatch) -> None:
    def unavailable(*_args, **_kwargs):
        raise OSError("offline")

    monkeypatch.setattr(socket, "create_connection", unavailable)
    stream = BackendStream("127.0.0.1", 9001, "device", "token", "boot")
    assert stream.send(PacketType.HEALTH_UPDATE, {"status": "HEALTHY"}, 1) is False
    assert stream.connection is None
