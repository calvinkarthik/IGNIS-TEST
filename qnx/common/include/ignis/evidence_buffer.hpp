#pragma once

#include <cstddef>
#include <cstdint>
#include <deque>
#include <vector>

namespace ignis {

struct EvidenceFrame {
    std::uint64_t sequence{0};
    std::uint64_t monotonic_ns{0};
    std::vector<std::uint8_t> jpeg;
};

class EvidenceBuffer {
public:
    explicit EvidenceBuffer(std::uint64_t duration_ns, std::size_t maximum_bytes)
        : duration_ns_(duration_ns), maximum_bytes_(maximum_bytes) {}

    void push(EvidenceFrame frame) {
        bytes_ += frame.jpeg.size();
        frames_.push_back(std::move(frame));
        while (!frames_.empty() &&
               ((frames_.back().monotonic_ns - frames_.front().monotonic_ns > duration_ns_) ||
                bytes_ > maximum_bytes_)) {
            bytes_ -= frames_.front().jpeg.size();
            frames_.pop_front();
        }
    }

    const std::deque<EvidenceFrame>& frames() const noexcept { return frames_; }
    std::size_t bytes() const noexcept { return bytes_; }

private:
    std::uint64_t duration_ns_;
    std::size_t maximum_bytes_;
    std::size_t bytes_{0};
    std::deque<EvidenceFrame> frames_;
};

}  // namespace ignis

