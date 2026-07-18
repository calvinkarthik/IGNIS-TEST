#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

#include "ignis/geometry.hpp"

namespace ignis {

struct Detection {
    std::string class_name;
    int class_id{0};
    double confidence{0};
    Box bbox;
};

inline bool normalize_detection(Detection& detection) {
    if (!std::isfinite(detection.confidence)) return false;
    detection.confidence = std::max(0.0, std::min(1.0, detection.confidence));
    detection.bbox.x_min = std::max(0.0, std::min(1.0, detection.bbox.x_min));
    detection.bbox.y_min = std::max(0.0, std::min(1.0, detection.bbox.y_min));
    detection.bbox.x_max = std::max(0.0, std::min(1.0, detection.bbox.x_max));
    detection.bbox.y_max = std::max(0.0, std::min(1.0, detection.bbox.y_max));
    return detection.bbox.valid();
}

struct DetectionFrame {
    std::uint64_t frame_sequence{0};
    std::uint64_t monotonic_ns{0};
    double inference_duration_ms{0};
    std::vector<Detection> detections;
};

}  // namespace ignis

