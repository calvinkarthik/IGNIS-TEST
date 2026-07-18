#pragma once

#include <cstddef>
#include <cstdint>

namespace ignis {

enum class PixelFormat : std::uint32_t { Unknown = 0, Rgb888 = 1, Bgr888 = 2, Yuyv = 3 };

struct FrameDescriptor {
    std::uint64_t sequence{0};
    std::uint64_t monotonic_ns{0};
    std::uint32_t width{0};
    std::uint32_t height{0};
    std::uint32_t stride{0};
    PixelFormat pixel_format{PixelFormat::Unknown};
    std::uint32_t slot{0};
    std::uint32_t payload_bytes{0};
};

}  // namespace ignis

