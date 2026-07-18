#include "frame_source.hpp"

#include <fstream>
#include <sstream>

#include "ignis/time.hpp"

namespace ignis {

Result<void> SyntheticFrameSource::initialize() {
    if (width_ == 0 || height_ == 0) return Result<void>::failure("invalid synthetic dimensions");
    initialized_ = true;
    return Result<void>::success();
}

Result<CapturedFrame> SyntheticFrameSource::capture() {
    if (!initialized_) return Result<CapturedFrame>::failure("source is not initialized");
    CapturedFrame frame;
    frame.descriptor.sequence = ++sequence_;
    frame.descriptor.monotonic_ns = monotonic_now_ns();
    frame.descriptor.width = width_;
    frame.descriptor.height = height_;
    frame.descriptor.stride = width_ * 3;
    frame.descriptor.pixel_format = PixelFormat::Rgb888;
    frame.pixels.resize(static_cast<std::size_t>(frame.descriptor.stride) * height_);
    for (std::uint32_t y = 0; y < height_; ++y) {
        for (std::uint32_t x = 0; x < width_; ++x) {
            const std::size_t offset = static_cast<std::size_t>(y) * frame.descriptor.stride + x * 3;
            frame.pixels[offset] = static_cast<std::uint8_t>((x + sequence_) % 128);
            frame.pixels[offset + 1] = static_cast<std::uint8_t>((y + sequence_) % 96);
            frame.pixels[offset + 2] = 32;
        }
    }
    return Result<CapturedFrame>::success(std::move(frame));
}

Result<void> ReplayFrameSource::initialize() {
    std::ifstream probe(root_ + "/frame-000001.rgb", std::ios::binary);
    if (!probe) return Result<void>::failure("replay root must contain frame-000001.rgb");
    initialized_ = true;
    return Result<void>::success();
}

Result<CapturedFrame> ReplayFrameSource::capture() {
    if (!initialized_) return Result<CapturedFrame>::failure("source is not initialized");
    ++sequence_;
    std::ostringstream path;
    path << root_ << "/frame-";
    path.width(6);
    path.fill('0');
    path << sequence_ << ".rgb";
    std::ifstream input(path.str(), std::ios::binary);
    if (!input) {
        sequence_ = 1;
        input.open(root_ + "/frame-000001.rgb", std::ios::binary);
    }
    const std::size_t expected = static_cast<std::size_t>(width_) * height_ * 3;
    CapturedFrame frame;
    frame.pixels.resize(expected);
    input.read(reinterpret_cast<char*>(frame.pixels.data()), static_cast<std::streamsize>(expected));
    if (static_cast<std::size_t>(input.gcount()) != expected)
        return Result<CapturedFrame>::failure("replay RGB frame has an invalid byte length");
    frame.descriptor = {sequence_, monotonic_now_ns(), width_, height_, width_ * 3,
                        PixelFormat::Rgb888, 0, static_cast<std::uint32_t>(expected)};
    return Result<CapturedFrame>::success(std::move(frame));
}

Result<void> QnxSensorFrameSource::initialize() {
    return Result<void>::failure(
        "QNX Sensor Framework bridge is not bound. Copy the proven Camera Module 3 sample adapter "
        "into qnx/camera_service/target and build with IGNIS_QNX_CAMERA_BRIDGE=1.");
}

Result<CapturedFrame> QnxSensorFrameSource::capture() {
    return Result<CapturedFrame>::failure("QNX Sensor Framework bridge is unavailable");
}

void QnxSensorFrameSource::shutdown() noexcept {}

}  // namespace ignis

