from __future__ import annotations

import socket
import time

from fastapi.testclient import TestClient

from app.protocol import PacketType, encode_packet


def test_valid_device_handshake_and_fragmented_packet(client: TestClient) -> None:
    port = client.app.state.tcp_server.bound_port
    hello = encode_packet(
        PacketType.HELLO,
        {
            "device_id": "ignis-qnxpi-01",
            "boot_id": "tcp-test",
            "protocol_version": 1,
            "software_version": "test",
            "device_token": "test-device-token",
            "capabilities": ["simulator"],
        },
        1,
        1,
    )
    with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
        connection.sendall(hello[:7])
        connection.sendall(hello[7:])
        ack = connection.recv(4096)
        assert ack.startswith(b"IGNS")
        deadline = time.time() + 2
        while time.time() < deadline:
            devices = client.get("/api/devices").json()
            if devices:
                break
            time.sleep(0.02)
        assert devices[0]["connected"] is True


def test_invalid_device_token_is_rejected(client: TestClient) -> None:
    port = client.app.state.tcp_server.bound_port
    hello = encode_packet(
        PacketType.HELLO,
        {
            "device_id": "ignis-qnxpi-01",
            "boot_id": "bad-token",
            "protocol_version": 1,
            "software_version": "test",
            "device_token": "wrong",
        },
        1,
        1,
    )
    with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
        connection.sendall(hello)
        connection.settimeout(2)
        assert connection.recv(1024) == b""
    assert all(device["boot_id"] != "bad-token" for device in client.get("/api/devices").json())

