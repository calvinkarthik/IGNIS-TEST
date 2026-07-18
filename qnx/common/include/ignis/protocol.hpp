#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "ignis/result.hpp"

namespace ignis {

constexpr std::size_t kPacketHeaderSize = 32;
constexpr std::uint8_t kProtocolVersion = 1;
constexpr std::size_t kDefaultMaximumPayload = 2'097'152;

enum class PacketType : std::uint8_t {
    Hello = 1,
    HelloAck = 2,
    Frame = 10,
    Detections = 11,
    IncidentUpdate = 12,
    IncidentTimelineEvent = 13,
    HealthUpdate = 14,
    EvidenceManifest = 15,
    LogEvent = 16,
    ConfigAck = 20,
    ConfigUpdate = 100,
    OccupantConfirm = 101,
    OccupantCancel = 102,
    ManualReset = 103,
    CallStatusUpdate = 104,
    Ping = 105,
    Pong = 106,
};

struct Packet {
    PacketType type{PacketType::Ping};
    std::uint16_t flags{0};
    std::uint64_t sequence{0};
    std::uint64_t monotonic_ns{0};
    std::vector<std::uint8_t> payload;
};

bool known_packet_type(std::uint8_t value) noexcept;
std::uint32_t crc32(const std::uint8_t* data, std::size_t size) noexcept;
std::vector<std::uint8_t> serialize_packet(const Packet& packet);

class PacketParser {
public:
    explicit PacketParser(std::size_t maximum_payload = kDefaultMaximumPayload)
        : maximum_payload_(maximum_payload) {}

    Result<std::vector<Packet>> feed(const std::uint8_t* data, std::size_t size);
    Result<std::vector<Packet>> feed(const std::vector<std::uint8_t>& data) {
        return feed(data.data(), data.size());
    }

private:
    std::size_t maximum_payload_;
    std::vector<std::uint8_t> buffer_;
};

std::vector<std::uint8_t> make_frame_payload(
    const std::string& metadata_json, const std::vector<std::uint8_t>& jpeg);

}  // namespace ignis

