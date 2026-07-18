#pragma once

#include <cstdint>
#include <iostream>
#include <string>

#include "ignis/time.hpp"

namespace ignis {

enum class Severity { Debug, Info, Warning, Error, Critical };

inline const char* severity_name(Severity severity) {
    switch (severity) {
        case Severity::Debug: return "DEBUG";
        case Severity::Info: return "INFO";
        case Severity::Warning: return "WARNING";
        case Severity::Error: return "ERROR";
        case Severity::Critical: return "CRITICAL";
    }
    return "UNKNOWN";
}

inline void log_event(
    const std::string& service,
    Severity severity,
    const std::string& boot_id,
    const std::string& event_code,
    const std::string& message,
    const std::string& incident_id = "") {
    // The target adapter may replace this with slog2 while preserving fields.
    std::clog << "service=" << service << " severity=" << severity_name(severity)
              << " boot_id=" << boot_id << " monotonic_ns=" << monotonic_now_ns()
              << " incident_id=" << (incident_id.empty() ? "-" : incident_id)
              << " event_code=" << event_code << " message=\"" << message << "\"\n";
}

}  // namespace ignis

