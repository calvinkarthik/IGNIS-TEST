#include "ignis/protocol.hpp"

#include <algorithm>
#include <array>
#include <cstring>

namespace ignis {

namespace {

void write_u16(std::uint8_t* output, std::uint16_t value) {
    output[0] = static_cast<std::uint8_t>(value >> 8);
    output[1] = static_cast<std::uint8_t>(value);
}

void write_u32(std::uint8_t* output, std::uint32_t value) {
    for (int index = 0; index < 4; ++index)
        output[index] = static_cast<std::uint8_t>(value >> (24 - 8 * index));
}

void write_u64(std::uint8_t* output, std::uint64_t value) {
    for (int index = 0; index < 8; ++index)
        output[index] = static_cast<std::uint8_t>(value >> (56 - 8 * index));
}

std::uint16_t read_u16(const std::uint8_t* input) {
    return static_cast<std::uint16_t>((input[0] << 8) | input[1]);
}

std::uint32_t read_u32(const std::uint8_t* input) {
    std::uint32_t value = 0;
    for (int index = 0; index < 4; ++index) value = (value << 8) | input[index];
    return value;
}

std::uint64_t read_u64(const std::uint8_t* input) {
    std::uint64_t value = 0;
    for (int index = 0; index < 8; ++index) value = (value << 8) | input[index];
    return value;
}

}  // namespace

bool known_packet_type(std::uint8_t value) noexcept {
    switch (static_cast<PacketType>(value)) {
        case PacketType::Hello:
        case PacketType::HelloAck:
        case PacketType::Frame:
        case PacketType::Detections:
        case PacketType::IncidentUpdate:
        case PacketType::IncidentTimelineEvent:
        case PacketType::HealthUpdate:
        case PacketType::EvidenceManifest:
        case PacketType::LogEvent:
        case PacketType::ConfigAck:
        case PacketType::ConfigUpdate:
        case PacketType::OccupantConfirm:
        case PacketType::OccupantCancel:
        case PacketType::ManualReset:
        case PacketType::CallStatusUpdate:
        case PacketType::Ping:
        case PacketType::Pong: return true;
    }
    return false;
}

std::uint32_t crc32(const std::uint8_t* data, std::size_t size) noexcept {
    std::uint32_t crc = 0xFFFFFFFFU;
    for (std::size_t index = 0; index < size; ++index) {
        crc ^= data[index];
        for (int bit = 0; bit < 8; ++bit) {
            const std::uint32_t mask = static_cast<std::uint32_t>(-(crc & 1U));
            crc = (crc >> 1U) ^ (0xEDB88320U & mask);
        }
    }
    return ~crc;
}

std::vector<std::uint8_t> serialize_packet(const Packet& packet) {
    std::vector<std::uint8_t> result(kPacketHeaderSize + packet.payload.size());
    result[0] = 'I';
    result[1] = 'G';
    result[2] = 'N';
    result[3] = 'S';
    result[4] = kProtocolVersion;
    result[5] = static_cast<std::uint8_t>(packet.type);
    write_u16(result.data() + 6, packet.flags);
    write_u32(result.data() + 8, static_cast<std::uint32_t>(packet.payload.size()));
    write_u64(result.data() + 12, packet.sequence);
    write_u64(result.data() + 20, packet.monotonic_ns);
    write_u32(result.data() + 28, crc32(packet.payload.data(), packet.payload.size()));
    std::copy(packet.payload.begin(), packet.payload.end(), result.begin() + kPacketHeaderSize);
    return result;
}

Result<std::vector<Packet>> PacketParser::feed(const std::uint8_t* data, std::size_t size) {
    if (buffer_.size() + size > maximum_payload_ + kPacketHeaderSize)
        return Result<std::vector<Packet>>::failure("connection buffer exceeds maximum packet size");
    buffer_.insert(buffer_.end(), data, data + size);
    std::vector<Packet> packets;
    while (buffer_.size() >= kPacketHeaderSize) {
        const std::uint8_t* header = buffer_.data();
        if (std::memcmp(header, "IGNS", 4) != 0)
            return Result<std::vector<Packet>>::failure("invalid magic");
        if (header[4] != kProtocolVersion)
            return Result<std::vector<Packet>>::failure("unsupported version");
        if (!known_packet_type(header[5]))
            return Result<std::vector<Packet>>::failure("unknown packet type");
        const std::uint32_t payload_length = read_u32(header + 8);
        if (payload_length > maximum_payload_)
            return Result<std::vector<Packet>>::failure("payload exceeds maximum");
        if (buffer_.size() < kPacketHeaderSize + payload_length) break;
        Packet packet;
        packet.type = static_cast<PacketType>(header[5]);
        packet.flags = read_u16(header + 6);
        packet.sequence = read_u64(header + 12);
        packet.monotonic_ns = read_u64(header + 20);
        packet.payload.assign(
            buffer_.begin() + kPacketHeaderSize,
            buffer_.begin() + kPacketHeaderSize + payload_length);
        const std::uint32_t expected_crc = read_u32(header + 28);
        if (crc32(packet.payload.data(), packet.payload.size()) != expected_crc)
            return Result<std::vector<Packet>>::failure("payload CRC mismatch");
        packets.push_back(std::move(packet));
        buffer_.erase(buffer_.begin(), buffer_.begin() + kPacketHeaderSize + payload_length);
    }
    return Result<std::vector<Packet>>::success(std::move(packets));
}

std::vector<std::uint8_t> make_frame_payload(
    const std::string& metadata_json, const std::vector<std::uint8_t>& jpeg) {
    std::vector<std::uint8_t> payload(4 + metadata_json.size() + jpeg.size());
    write_u32(payload.data(), static_cast<std::uint32_t>(metadata_json.size()));
    std::copy(metadata_json.begin(), metadata_json.end(), payload.begin() + 4);
    std::copy(jpeg.begin(), jpeg.end(), payload.begin() + 4 + metadata_json.size());
    return payload;
}

}  // namespace ignis

