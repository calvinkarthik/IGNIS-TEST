#pragma once

#include "ignis/detections.hpp"
#include "ignis/frame_descriptor.hpp"
#include "ignis/model_manifest.hpp"
#include "ignis/result.hpp"

namespace ignis {

class IInferenceEngine {
public:
    virtual ~IInferenceEngine() = default;
    virtual Result<void> initialize(const ModelManifest& manifest) = 0;
    virtual Result<DetectionFrame> infer(
        const FrameDescriptor& descriptor, const std::uint8_t* pixels, std::size_t size) = 0;
};

class TensorFlowLiteEngine final : public IInferenceEngine {
public:
    Result<void> initialize(const ModelManifest& manifest) override;
    Result<DetectionFrame> infer(
        const FrameDescriptor& descriptor, const std::uint8_t* pixels, std::size_t size) override;
};

}  // namespace ignis

