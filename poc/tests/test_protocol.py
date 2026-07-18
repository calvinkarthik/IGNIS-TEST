from __future__ import annotations

from app.protocol import PacketParser, PacketType as BackendPacketType, decode_frame_payload
from ignis_poc.protocol import PacketType, encode_packet, frame_payload


def test_poc_packets_are_read_by_production_backend() -> None:
    raw = encode_packet(PacketType.DETECTIONS, {"detections": []}, 42, 123456)
    packet = PacketParser().feed(raw)[0]
    assert packet.packet_type == BackendPacketType.DETECTIONS
    assert packet.sequence == 42
    assert packet.json() == {"detections": []}


def test_poc_frame_payload_is_read_by_production_backend() -> None:
    jpeg = b"\xff\xd8poc-frame\xff\xd9"
    payload = frame_payload({"width": 640, "height": 480}, jpeg)
    metadata, decoded = decode_frame_payload(payload)
    assert metadata == {"width": 640, "height": 480}
    assert decoded == jpeg
