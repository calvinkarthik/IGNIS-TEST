from __future__ import annotations

import json
import struct
import zlib
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

MAGIC = b"IGNS"
VERSION = 1
HEADER = struct.Struct("!4sBBHIQQI")
HEADER_SIZE = HEADER.size


class ProtocolError(ValueError):
    pass


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


@dataclass(frozen=True, slots=True)
class Packet:
    packet_type: PacketType
    flags: int
    sequence: int
    monotonic_ns: int
    payload: bytes

    def json(self) -> dict[str, Any]:
        try:
            value = json.loads(self.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProtocolError("invalid JSON payload") from exc
        if not isinstance(value, dict):
            raise ProtocolError("JSON payload must be an object")
        return value


def encode_packet(
    packet_type: PacketType,
    payload: bytes | dict[str, Any],
    sequence: int,
    monotonic_ns: int,
    flags: int = 0,
) -> bytes:
    if isinstance(payload, dict):
        payload = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    return HEADER.pack(
        MAGIC,
        VERSION,
        int(packet_type),
        flags,
        len(payload),
        sequence,
        monotonic_ns,
        crc,
    ) + payload


class PacketParser:
    def __init__(self, max_payload_bytes: int = 2_097_152):
        self.max_payload_bytes = max_payload_bytes
        self._buffer = bytearray()
        self._expected: tuple[PacketType, int, int, int, int, int] | None = None

    @property
    def buffered_bytes(self) -> int:
        return len(self._buffer)

    def feed(self, chunk: bytes) -> list[Packet]:
        if len(self._buffer) + len(chunk) > self.max_payload_bytes + HEADER_SIZE:
            raise ProtocolError("connection buffer exceeded maximum packet size")
        self._buffer.extend(chunk)
        packets: list[Packet] = []
        while True:
            if self._expected is None:
                if len(self._buffer) < HEADER_SIZE:
                    break
                raw_header = bytes(self._buffer[:HEADER_SIZE])
                del self._buffer[:HEADER_SIZE]
                magic, version, raw_type, flags, length, sequence, monotonic_ns, crc = (
                    HEADER.unpack(raw_header)
                )
                if magic != MAGIC:
                    raise ProtocolError("invalid packet magic")
                if version != VERSION:
                    raise ProtocolError("unsupported protocol version")
                try:
                    packet_type = PacketType(raw_type)
                except ValueError as exc:
                    raise ProtocolError("unknown packet type") from exc
                if length > self.max_payload_bytes:
                    raise ProtocolError("payload exceeds configured maximum")
                self._expected = (packet_type, flags, length, sequence, monotonic_ns, crc)
            packet_type, flags, length, sequence, monotonic_ns, crc = self._expected
            if len(self._buffer) < length:
                break
            payload = bytes(self._buffer[:length])
            del self._buffer[:length]
            self._expected = None
            if zlib.crc32(payload) & 0xFFFFFFFF != crc:
                raise ProtocolError("payload CRC mismatch")
            packets.append(Packet(packet_type, flags, sequence, monotonic_ns, payload))
        return packets


def encode_frame_payload(metadata: dict[str, Any], jpeg: bytes) -> bytes:
    encoded = json.dumps(metadata, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return struct.pack("!I", len(encoded)) + encoded + jpeg


def decode_frame_payload(payload: bytes) -> tuple[dict[str, Any], bytes]:
    if len(payload) < 4:
        raise ProtocolError("truncated frame metadata length")
    (length,) = struct.unpack("!I", payload[:4])
    if length == 0 or 4 + length >= len(payload):
        raise ProtocolError("invalid frame metadata length")
    try:
        metadata = json.loads(payload[4 : 4 + length].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid frame metadata JSON") from exc
    jpeg = payload[4 + length :]
    if not isinstance(metadata, dict):
        raise ProtocolError("frame metadata must be an object")
    if len(jpeg) < 4 or not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9"):
        raise ProtocolError("truncated or invalid JPEG")
    return metadata, jpeg

