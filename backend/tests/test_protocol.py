from __future__ import annotations

import struct

import pytest

from app.protocol import (
    HEADER_SIZE,
    PacketParser,
    PacketType,
    ProtocolError,
    decode_frame_payload,
    encode_frame_payload,
    encode_packet,
)


def test_header_is_exactly_32_bytes_and_network_order() -> None:
    encoded = encode_packet(PacketType.PING, b"abc", 0x0102030405060708, 9)
    assert HEADER_SIZE == 32
    assert encoded[:4] == b"IGNS"
    assert encoded[12:20] == bytes.fromhex("0102030405060708")


def test_fragmented_and_coalesced_packets() -> None:
    first = encode_packet(PacketType.HELLO, {"hello": True}, 1, 10)
    second = encode_packet(PacketType.PING, {}, 2, 11)
    parser = PacketParser()
    packets = []
    stream = first + second
    for byte in stream[:17]:
        packets.extend(parser.feed(bytes([byte])))
    packets.extend(parser.feed(stream[17:]))
    assert [packet.packet_type for packet in packets] == [PacketType.HELLO, PacketType.PING]
    assert packets[0].json() == {"hello": True}


def test_crc_and_unknown_type_are_rejected() -> None:
    packet = bytearray(encode_packet(PacketType.PING, b"hello", 1, 1))
    packet[-1] ^= 0xFF
    with pytest.raises(ProtocolError, match="CRC"):
        PacketParser().feed(packet)

    packet = bytearray(encode_packet(PacketType.PING, b"", 1, 1))
    packet[5] = 99
    with pytest.raises(ProtocolError, match="unknown"):
        PacketParser().feed(packet)


def test_oversize_and_invalid_magic_are_rejected() -> None:
    packet = bytearray(encode_packet(PacketType.PING, b"", 1, 1))
    packet[:4] = b"NOPE"
    with pytest.raises(ProtocolError, match="magic"):
        PacketParser().feed(packet)

    packet = bytearray(encode_packet(PacketType.PING, b"", 1, 1))
    packet[8:12] = struct.pack("!I", 500)
    with pytest.raises(ProtocolError, match="maximum"):
        PacketParser(max_payload_bytes=32).feed(packet)


def test_frame_payload_roundtrip_and_truncation() -> None:
    jpeg = b"\xff\xd8payload\xff\xd9"
    payload = encode_frame_payload({"width": 640, "height": 480}, jpeg)
    metadata, decoded = decode_frame_payload(payload)
    assert metadata["width"] == 640
    assert decoded == jpeg
    with pytest.raises(ProtocolError, match="JPEG"):
        decode_frame_payload(payload[:-1])


def test_invalid_json_is_rejected() -> None:
    packet = PacketParser().feed(encode_packet(PacketType.PING, b"{", 1, 1))[0]
    with pytest.raises(ProtocolError, match="JSON"):
        packet.json()

