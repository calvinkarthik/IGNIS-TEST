#include "inference_engine.hpp"

namespace ignis {

Result<void> TensorFlowLiteEngine::initialize(const ModelManifest& manifest) {
    auto valid = manifest.validate();
    if (!valid) return valid;
    return Result<void>::failure(
        "TensorFlow Lite target bridge is not linked. Supply the target runtime/model and enable "
        "IGNIS_WITH_TFLITE after validating tensor metadata against the manifest.");
}

Result<DetectionFrame> TensorFlowLiteEngine::infer(
    const FrameDescriptor&, const std::uint8_t*, std::size_t) {
    return Result<DetectionFrame>::failure("TensorFlow Lite target bridge is unavailable");
}

}  // namespace ignis

