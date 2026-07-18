#include <atomic>
#include <chrono>
#include <csignal>
#include <thread>

#include "ignis/incident.hpp"
#include "ignis/logging.hpp"

namespace {
std::atomic<bool> running{true};
void stop(int) { running = false; }
}

int main() {
    std::signal(SIGINT, stop);
    std::signal(SIGTERM, stop);
    ignis::IncidentEngine engine("ignis-qnxpi-01", "startup");
    while (running) {
        ignis::log_event("incident_engine", ignis::Severity::Info, "startup", "HEARTBEAT",
                         std::string("hazard_state=") + ignis::to_string(engine.snapshot().hazard_state));
        // Target integration receives normalized detections over QNX IPC and persists every transition.
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    return 0;
}

