#pragma once

#include <cstdint>

namespace ignis {

enum class IpcMessageType : std::uint16_t {
    FrameReady = 1,
    DetectionReady = 2,
    IncidentChanged = 3,
    Heartbeat = 4,
    ConfigurationChanged = 5,
    Shutdown = 6,
};

struct IpcMessage {
    IpcMessageType type{IpcMessageType::Heartbeat};
    std::uint16_t version{1};
    std::uint32_t service_id{0};
    std::uint64_t sequence{0};
    std::uint64_t monotonic_ns{0};
    std::uint64_t value{0};
};

static_assert(sizeof(IpcMessage) <= 40, "IPC metadata must remain small");

}  // namespace ignis

