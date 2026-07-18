#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "ignis/frame_descriptor.hpp"
#include "ignis/result.hpp"

namespace ignis {

struct CapturedFrame {
    FrameDescriptor descriptor;
    std::vector<std::uint8_t> pixels;
};

class IFrameSource {
public:
    virtual ~IFrameSource() = default;
    virtual Result<void> initialize() = 0;
    virtual Result<CapturedFrame> capture() = 0;
    virtual void shutdown() noexcept = 0;
};

class SyntheticFrameSource final : public IFrameSource {
public:
    SyntheticFrameSource(std::uint32_t width = 640, std::uint32_t height = 480)
        : width_(width), height_(height) {}
    Result<void> initialize() override;
    Result<CapturedFrame> capture() override;
    void shutdown() noexcept override { initialized_ = false; }

private:
    std::uint32_t width_;
    std::uint32_t height_;
    std::uint64_t sequence_{0};
    bool initialized_{false};
};

class ReplayFrameSource final : public IFrameSource {
public:
    ReplayFrameSource(std::string root, std::uint32_t width, std::uint32_t height)
        : root_(std::move(root)), width_(width), height_(height) {}
    Result<void> initialize() override;
    Result<CapturedFrame> capture() override;
    void shutdown() noexcept override { initialized_ = false; }

private:
    std::string root_;
    std::uint32_t width_;
    std::uint32_t height_;
    std::uint64_t sequence_{0};
    bool initialized_{false};
};

class QnxSensorFrameSource final : public IFrameSource {
public:
    Result<void> initialize() override;
    Result<CapturedFrame> capture() override;
    void shutdown() noexcept override;
};

}  // namespace ignis

