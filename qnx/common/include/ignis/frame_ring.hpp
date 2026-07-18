#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <vector>

#include "ignis/frame_descriptor.hpp"

namespace ignis {

// In-process representation used by portable tests. The QNX adapter maps the same
// bounded slot metadata onto POSIX shared memory and signals consumers with pulses.
class FrameRing {
public:
    FrameRing(std::size_t slots, std::size_t bytes_per_slot)
        : slots_(slots), storage_(slots * bytes_per_slot), bytes_per_slot_(bytes_per_slot) {}

    bool write(const FrameDescriptor& descriptor, const std::uint8_t* data, std::size_t size) {
        if (slots_.empty() || size > bytes_per_slot_) return false;
        const std::size_t index = static_cast<std::size_t>(write_sequence_++ % slots_.size());
        const std::size_t offset = index * bytes_per_slot_;
        std::copy(data, data + size, storage_.begin() + offset);
        slots_[index] = descriptor;
        slots_[index].slot = static_cast<std::uint32_t>(index);
        slots_[index].payload_bytes = static_cast<std::uint32_t>(size);
        latest_slot_.store(index, std::memory_order_release);
        return true;
    }

    bool latest(FrameDescriptor& descriptor, std::vector<std::uint8_t>& data) const {
        if (slots_.empty()) return false;
        const std::size_t index = latest_slot_.load(std::memory_order_acquire);
        descriptor = slots_[index];
        if (descriptor.payload_bytes == 0) return false;
        const std::size_t offset = index * bytes_per_slot_;
        data.assign(storage_.begin() + offset, storage_.begin() + offset + descriptor.payload_bytes);
        return true;
    }

private:
    mutable std::vector<FrameDescriptor> slots_;
    mutable std::vector<std::uint8_t> storage_;
    std::size_t bytes_per_slot_;
    std::uint64_t write_sequence_{0};
    std::atomic<std::size_t> latest_slot_{0};
};

}  // namespace ignis

