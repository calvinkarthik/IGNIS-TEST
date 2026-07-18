#include <chrono>
#include <thread>

#include "ignis/logging.hpp"

int main() {
    ignis::log_event(
        "inference_service", ignis::Severity::Critical, "startup", "TFLITE_BRIDGE_UNAVAILABLE",
        "Install the verified QNX TensorFlow Lite runtime, model, and manifest before hardware mode.");
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    return 78;
}

