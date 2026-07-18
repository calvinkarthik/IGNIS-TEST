from __future__ import annotations

import json
import socket
import struct
import zlib
from enum import IntEnum
from typing import Any

HEADER = struct.Struct("!4sBBHIQQI")


class PacketType(IntEnum):
    HELLO = 1
    HELLO_ACK = 2
    FRAME = 10
    DETECTIONS = 11
    INCIDENT_UPDATE = 12
    INCIDENT_TIMELINE_EVENT = 13
    HEALTH_UPDATE = 14


def encode_packet(
    packet_type: PacketType,
    payload: bytes | dict[str, Any],
    sequence: int,
    monotonic_ns: int,
) -> bytes:
    if isinstance(payload, dict):
        payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return HEADER.pack(
        b"IGNS",
        1,
        packet_type,
        0,
        len(payload),
        sequence,
        monotonic_ns,
        zlib.crc32(payload) & 0xFFFFFFFF,
    ) + payload


def frame_payload(metadata: dict[str, Any], jpeg: bytes) -> bytes:
    encoded = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
    return struct.pack("!I", len(encoded)) + encoded + jpeg


def receive_exact(connection: socket.socket, length: int) -> bytes:
    result = bytearray()
    while len(result) < length:
        chunk = connection.recv(length - len(result))
        if not chunk:
            raise ConnectionError("backend closed the connection")
        result.extend(chunk)
    return bytes(result)


def receive_ack(connection: socket.socket) -> dict[str, Any]:
    header = receive_exact(connection, HEADER.size)
    magic, version, packet_type, _flags, length, _sequence, _time, crc = HEADER.unpack(header)
    if magic != b"IGNS" or version != 1 or packet_type != PacketType.HELLO_ACK:
        raise ConnectionError("backend returned an invalid HELLO_ACK")
    payload = receive_exact(connection, length)
    if zlib.crc32(payload) & 0xFFFFFFFF != crc:
        raise ConnectionError("HELLO_ACK CRC failed")
    value = json.loads(payload)
    if not isinstance(value, dict) or not value.get("accepted"):
        raise ConnectionError("backend rejected the POC device")
    return value

