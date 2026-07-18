#pragma once

#include <cstdint>
#include <deque>
#include <string>

#include "ignis/geometry.hpp"

namespace ignis {

enum class HazardState {
    Clear,
    Suspected,
    Verifying,
    Confirmed,
    VisualSignatureLost,
    Resolved,
    Degraded,
};

enum class ResponseState {
    Idle,
    AwaitingResponse,
    Cancelled,
    Escalating,
    CallRequested,
    CallInitiated,
    CallConnected,
    CallCompleted,
    CallFailed,
};

const char* to_string(HazardState state) noexcept;
const char* to_string(ResponseState state) noexcept;

struct IncidentThresholds {
    double suspected_fire_confidence{0.55};
    double suspected_smoke_confidence{0.65};
    std::size_t persistence_window_frames{10};
    std::size_t persistence_required_frames{6};
    double confirmed_fire_confidence{0.75};
    std::uint64_t confirmed_fire_duration_ns{2'000'000'000ULL};
    std::uint64_t confirmed_visible_duration_ns{4'000'000'000ULL};
    std::uint64_t clear_grace_period_ns{2'000'000'000ULL};
    std::uint64_t growth_window_ns{3'000'000'000ULL};
    double growth_minimum_percent{20.0};
    double growth_minimum_area{0.005};
    double timing_uncertainty_seconds{0.5};
};

struct FrameEvidence {
    std::uint64_t sequence{0};
    std::uint64_t monotonic_ns{0};
    double fire_confidence{0};
    double smoke_confidence{0};
    Box fire_box;
    Box smoke_box;
    std::string zone{"Unconfigured area"};
};

struct IncidentSnapshot {
    std::string incident_id;
    HazardState hazard_state{HazardState::Clear};
    ResponseState response_state{ResponseState::Idle};
    std::uint64_t first_detection_ns{0};
    std::uint64_t updated_ns{0};
    double peak_fire_confidence{0};
    double peak_smoke_confidence{0};
    double seconds_persistent{0};
    std::string first_zone{"Unconfigured area"};
    std::string current_zone{"Unconfigured area"};
    double fire_region_growth_percent{0};
    bool growth_stable{false};
    bool smoke_first_known{false};
    bool smoke_first{false};
    double smoke_to_fire_delay_seconds{0};
    bool was_confirmed{false};
};

class IncidentEngine {
public:
    IncidentEngine(std::string device_id, std::string boot_id, IncidentThresholds thresholds = {});
    const IncidentSnapshot& process(const FrameEvidence& evidence);
    bool cancel(const std::string& reason);
    bool confirm_occupant();
    bool manual_reset();
    void set_degraded(bool degraded);
    const IncidentSnapshot& snapshot() const noexcept { return snapshot_; }

private:
    bool relevant(const FrameEvidence& evidence) const noexcept;
    std::size_t persistence_count() const noexcept;
    bool confirmation_rule_met(std::uint64_t now);
    void update_growth(std::uint64_t now);
    void update_sequence_observation();
    void begin_incident(const FrameEvidence& evidence);
    void confirm_visual(std::uint64_t now);

    std::string device_id_;
    std::string boot_id_;
    std::uint64_t incident_counter_{0};
    IncidentThresholds thresholds_;
    IncidentSnapshot snapshot_;
    std::deque<FrameEvidence> window_;
    std::uint64_t last_sequence_{0};
    std::uint64_t last_relevant_ns_{0};
    std::uint64_t first_fire_ns_{0};
    std::uint64_t first_smoke_ns_{0};
    std::uint64_t sustained_high_fire_start_ns_{0};
    bool degraded_{false};
};

}  // namespace ignis

