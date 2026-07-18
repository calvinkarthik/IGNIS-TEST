#pragma once

#include <string>

#include "ignis/incident.hpp"
#include "ignis/protocol.hpp"
#include "ignis/result.hpp"

namespace ignis {

struct DeviceConfiguration {
    std::string device_id{"ignis-qnxpi-01"};
    std::string mode{"replay"};
    std::string backend_host{"127.0.0.1"};
    unsigned backend_port{9001};
    unsigned capture_fps{12};
    unsigned inference_fps{8};
    unsigned stream_fps{7};
    std::size_t maximum_payload_bytes{kDefaultMaximumPayload};
    IncidentThresholds incident;

    Result<void> validate() const {
        if (device_id.empty()) return Result<void>::failure("device_id is required");
        if (mode != "qnx" && mode != "replay" && mode != "synthetic")
            return Result<void>::failure("mode must be qnx, replay, or synthetic");
        if (backend_port == 0 || backend_port > 65535)
            return Result<void>::failure("backend port is invalid");
        if (incident.persistence_required_frames == 0 ||
            incident.persistence_required_frames > incident.persistence_window_frames)
            return Result<void>::failure("persistence thresholds are invalid");
        return Result<void>::success();
    }
};

}  // namespace ignis
