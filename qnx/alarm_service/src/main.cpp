#include <atomic>
#include <chrono>
#include <csignal>
#include <thread>

#include "ignis/logging.hpp"

namespace {
std::atomic<bool> running{true};
void stop(int) { running = false; }
}

int main() {
    std::signal(SIGINT, stop);
    std::signal(SIGTERM, stop);
    ignis::log_event("alarm_service", ignis::Severity::Info, "startup", "NULL_ALARM_ACTIVE",
                     "alarm output is disabled; no GPIO library has been verified");
    while (running) std::this_thread::sleep_for(std::chrono::seconds(1));
    return 0;
}

