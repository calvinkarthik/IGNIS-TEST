from __future__ import annotations

import json
import struct
import zlib
from enum import IntEnum
from typing import Any

MAGIC = b"IGNS"
VERSION = 1
HEADER = struct.Struct("!4sBBHIQQI")


class PacketType(IntEnum):
    HELLO = 1
    HELLO_ACK = 2
    FRAME = 10
    DETECTIONS = 11
    INCIDENT_UPDATE = 12
    INCIDENT_TIMELINE_EVENT = 13
    HEALTH_UPDATE = 14
    EVIDENCE_MANIFEST = 15
    LOG_EVENT = 16
    CONFIG_ACK = 20
    CONFIG_UPDATE = 100
    OCCUPANT_CONFIRM = 101
    OCCUPANT_CANCEL = 102
    MANUAL_RESET = 103
    CALL_STATUS_UPDATE = 104
    PING = 105
    PONG = 106


def packet(
    packet_type: PacketType,
    payload: bytes | dict[str, Any],
    sequence: int,
    monotonic_ns: int,
) -> bytes:
    if isinstance(payload, dict):
        payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return HEADER.pack(
        MAGIC,
        VERSION,
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

