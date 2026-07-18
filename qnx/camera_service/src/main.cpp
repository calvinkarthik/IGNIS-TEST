#include <atomic>
#include <chrono>
#include <csignal>
#include <memory>
#include <string>
#include <thread>

#include "frame_source.hpp"
#include "ignis/logging.hpp"

namespace {
std::atomic<bool> running{true};
void stop(int) { running = false; }
}  // namespace

int main(int argc, char** argv) {
    std::signal(SIGINT, stop);
    std::signal(SIGTERM, stop);
    const std::string mode = argc > 1 ? argv[1] : "qnx";
    std::unique_ptr<ignis::IFrameSource> source;
    if (mode == "synthetic") source.reset(new ignis::SyntheticFrameSource());
    else if (mode == "replay" && argc > 2)
        source.reset(new ignis::ReplayFrameSource(argv[2], 640, 480));
    else source.reset(new ignis::QnxSensorFrameSource());
    auto initialized = source->initialize();
    if (!initialized) {
        ignis::log_event("camera_service", ignis::Severity::Critical, "startup",
                         "CAMERA_INITIALIZATION_FAILED", initialized.error());
        return 78;
    }
    std::uint64_t frames = 0;
    while (running) {
        auto captured = source->capture();
        if (!captured) {
            ignis::log_event("camera_service", ignis::Severity::Error, "startup",
                             "CAMERA_CAPTURE_FAILED", captured.error());
            std::this_thread::sleep_for(std::chrono::milliseconds(250));
            continue;
        }
        ++frames;
        if (frames % 12 == 0)
            ignis::log_event("camera_service", ignis::Severity::Info, "startup",
                             "HEARTBEAT", "camera capture healthy");
        // Target integration writes captured.value() into the shared frame ring and sends a pulse.
        std::this_thread::sleep_for(std::chrono::milliseconds(83));
    }
    source->shutdown();
    return 0;
}

