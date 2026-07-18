#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <deque>
#include <map>
#include <spawn.h>
#include <string>
#include <thread>
#include <vector>

#include <sys/wait.h>
#include <unistd.h>

#include "ignis/logging.hpp"

extern char** environ;

namespace {

std::atomic<bool> running{true};
void stop(int) { running = false; }

struct Child {
    std::string name;
    std::vector<std::string> arguments;
    pid_t pid{-1};
    std::deque<std::chrono::steady_clock::time_point> restarts;
    bool exhausted{false};
};

bool spawn_child(Child& child, const std::string& bin_dir) {
    const std::string executable = bin_dir + "/" + child.name;
    std::vector<char*> argv;
    argv.push_back(const_cast<char*>(executable.c_str()));
    for (std::string& argument : child.arguments) argv.push_back(const_cast<char*>(argument.c_str()));
    argv.push_back(nullptr);
    const int status = posix_spawn(&child.pid, executable.c_str(), nullptr, nullptr, argv.data(), environ);
    return status == 0;
}

}  // namespace

int main(int argc, char** argv) {
    std::signal(SIGINT, stop);
    std::signal(SIGTERM, stop);
    const std::string bin_dir = argc > 1 ? argv[1] : "/data/home/qnxuser/ignis/bin";
    const char* camera_mode_value = std::getenv("IGNIS_CAMERA_MODE");
    const std::string camera_mode = camera_mode_value ? camera_mode_value : "qnx";
    std::vector<Child> children{
        {"camera_service", {camera_mode}},
        {"inference_service", {}},
        {"incident_engine", {}},
        {"stream_service", {}},
        {"alarm_service", {}},
    };
    const std::string boot_id = std::to_string(static_cast<unsigned long long>(getpid()));
    for (Child& child : children) {
        if (!spawn_child(child, bin_dir)) {
            child.exhausted = true;
            ignis::log_event("watchdog_service", ignis::Severity::Error, boot_id,
                             "CHILD_START_FAILED", child.name);
        }
    }

    while (running) {
        for (Child& child : children) {
            if (child.pid <= 0 || child.exhausted) continue;
            int status = 0;
            const pid_t result = waitpid(child.pid, &status, WNOHANG);
            if (result != child.pid) continue;
            const auto now = std::chrono::steady_clock::now();
            while (!child.restarts.empty() &&
                   now - child.restarts.front() > std::chrono::seconds(60))
                child.restarts.pop_front();
            if (child.restarts.size() >= 3) {
                child.exhausted = true;
                child.pid = -1;
                ignis::log_event("watchdog_service", ignis::Severity::Critical, boot_id,
                                 "RESTART_BUDGET_EXHAUSTED", child.name);
                continue;
            }
            child.restarts.push_back(now);
            ignis::log_event("watchdog_service", ignis::Severity::Warning, boot_id,
                             "CHILD_RESTARTING", child.name);
            if (!spawn_child(child, bin_dir)) child.exhausted = true;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(250));
    }
    for (Child& child : children) {
        if (child.pid > 0) kill(child.pid, SIGTERM);
    }
    for (Child& child : children) {
        if (child.pid > 0) waitpid(child.pid, nullptr, 0);
    }
    return 0;
}

