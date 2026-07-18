#include "ignis/incident.hpp"

#include <algorithm>
#include <cmath>
#include <sstream>

namespace ignis {

const char* to_string(HazardState state) noexcept {
    switch (state) {
        case HazardState::Clear: return "CLEAR";
        case HazardState::Suspected: return "SUSPECTED";
        case HazardState::Verifying: return "VERIFYING";
        case HazardState::Confirmed: return "CONFIRMED";
        case HazardState::VisualSignatureLost: return "VISUAL_SIGNATURE_LOST";
        case HazardState::Resolved: return "RESOLVED";
        case HazardState::Degraded: return "DEGRADED";
    }
    return "UNKNOWN";
}

const char* to_string(ResponseState state) noexcept {
    switch (state) {
        case ResponseState::Idle: return "IDLE";
        case ResponseState::AwaitingResponse: return "AWAITING_RESPONSE";
        case ResponseState::Cancelled: return "CANCELLED";
        case ResponseState::Escalating: return "ESCALATING";
        case ResponseState::CallRequested: return "CALL_REQUESTED";
        case ResponseState::CallInitiated: return "CALL_INITIATED";
        case ResponseState::CallConnected: return "CALL_CONNECTED";
        case ResponseState::CallCompleted: return "CALL_COMPLETED";
        case ResponseState::CallFailed: return "CALL_FAILED";
    }
    return "UNKNOWN";
}

IncidentEngine::IncidentEngine(
    std::string device_id, std::string boot_id, IncidentThresholds thresholds)
    : device_id_(std::move(device_id)), boot_id_(std::move(boot_id)), thresholds_(thresholds) {}

bool IncidentEngine::relevant(const FrameEvidence& evidence) const noexcept {
    return evidence.fire_confidence >= thresholds_.suspected_fire_confidence ||
           evidence.smoke_confidence >= thresholds_.suspected_smoke_confidence;
}

std::size_t IncidentEngine::persistence_count() const noexcept {
    return static_cast<std::size_t>(std::count_if(
        window_.begin(), window_.end(), [this](const FrameEvidence& frame) { return relevant(frame); }));
}

void IncidentEngine::begin_incident(const FrameEvidence& evidence) {
    ++incident_counter_;
    std::ostringstream id;
    id << device_id_ << '-' << boot_id_ << '-' << incident_counter_;
    snapshot_ = IncidentSnapshot{};
    snapshot_.incident_id = id.str();
    snapshot_.hazard_state = HazardState::Suspected;
    snapshot_.response_state = ResponseState::Idle;
    snapshot_.first_detection_ns = evidence.monotonic_ns;
    snapshot_.updated_ns = evidence.monotonic_ns;
    snapshot_.first_zone = evidence.zone;
    snapshot_.current_zone = evidence.zone;
    first_fire_ns_ = 0;
    first_smoke_ns_ = 0;
    sustained_high_fire_start_ns_ = 0;
}

const IncidentSnapshot& IncidentEngine::process(const FrameEvidence& evidence) {
    if (evidence.sequence <= last_sequence_ || evidence.monotonic_ns == 0) return snapshot_;
    last_sequence_ = evidence.sequence;
    if (degraded_) {
        snapshot_.hazard_state = HazardState::Degraded;
        snapshot_.updated_ns = evidence.monotonic_ns;
        return snapshot_;
    }

    window_.push_back(evidence);
    while (window_.size() > thresholds_.persistence_window_frames) window_.pop_front();
    const bool is_relevant = relevant(evidence);
    if (is_relevant) {
        last_relevant_ns_ = evidence.monotonic_ns;
        if (snapshot_.hazard_state == HazardState::Clear || snapshot_.hazard_state == HazardState::Resolved) {
            begin_incident(evidence);
        }
        snapshot_.peak_fire_confidence =
            std::max(snapshot_.peak_fire_confidence, evidence.fire_confidence);
        snapshot_.peak_smoke_confidence =
            std::max(snapshot_.peak_smoke_confidence, evidence.smoke_confidence);
        snapshot_.current_zone = evidence.zone;
        if (evidence.fire_confidence >= thresholds_.suspected_fire_confidence && first_fire_ns_ == 0)
            first_fire_ns_ = evidence.monotonic_ns;
        if (evidence.smoke_confidence >= thresholds_.suspected_smoke_confidence && first_smoke_ns_ == 0)
            first_smoke_ns_ = evidence.monotonic_ns;
        if (evidence.fire_confidence >= thresholds_.confirmed_fire_confidence) {
            if (sustained_high_fire_start_ns_ == 0) sustained_high_fire_start_ns_ = evidence.monotonic_ns;
        } else {
            sustained_high_fire_start_ns_ = 0;
        }
    } else {
        sustained_high_fire_start_ns_ = 0;
    }

    if (snapshot_.first_detection_ns != 0) {
        snapshot_.updated_ns = evidence.monotonic_ns;
        snapshot_.seconds_persistent = static_cast<double>(
            evidence.monotonic_ns - snapshot_.first_detection_ns) / 1'000'000'000.0;
    }

    if (!snapshot_.was_confirmed && persistence_count() >= thresholds_.persistence_required_frames) {
        snapshot_.hazard_state = HazardState::Verifying;
    }
    update_growth(evidence.monotonic_ns);
    update_sequence_observation();
    if (!snapshot_.was_confirmed && snapshot_.hazard_state == HazardState::Verifying &&
        confirmation_rule_met(evidence.monotonic_ns)) {
        confirm_visual(evidence.monotonic_ns);
    }

    if (!is_relevant && last_relevant_ns_ != 0 &&
        evidence.monotonic_ns - last_relevant_ns_ >= thresholds_.clear_grace_period_ns) {
        if (snapshot_.was_confirmed) {
            snapshot_.hazard_state = HazardState::VisualSignatureLost;
        } else {
            snapshot_.hazard_state = HazardState::Clear;
            snapshot_.response_state = ResponseState::Idle;
        }
    } else if (is_relevant && snapshot_.was_confirmed &&
               snapshot_.hazard_state == HazardState::VisualSignatureLost) {
        snapshot_.hazard_state = HazardState::Confirmed;
    }
    return snapshot_;
}

bool IncidentEngine::confirmation_rule_met(std::uint64_t now) {
    const bool high_fire_duration = sustained_high_fire_start_ns_ != 0 &&
        now - sustained_high_fire_start_ns_ >= thresholds_.confirmed_fire_duration_ns;
    const bool visible_duration = snapshot_.first_detection_ns != 0 &&
        now - snapshot_.first_detection_ns >= thresholds_.confirmed_visible_duration_ns &&
        persistence_count() >= thresholds_.persistence_required_frames;
    std::size_t cooccurrence = 0;
    std::uint64_t cooccurrence_first = 0;
    for (const FrameEvidence& frame : window_) {
        if (frame.fire_confidence >= thresholds_.suspected_fire_confidence &&
            frame.smoke_confidence >= thresholds_.suspected_smoke_confidence) {
            ++cooccurrence;
            if (cooccurrence_first == 0) cooccurrence_first = frame.monotonic_ns;
        }
    }
    const bool fire_and_smoke = cooccurrence >= thresholds_.persistence_required_frames &&
        cooccurrence_first != 0 && now - cooccurrence_first >= 1'000'000'000ULL;
    return high_fire_duration || visible_duration || fire_and_smoke || snapshot_.growth_stable;
}

void IncidentEngine::update_growth(std::uint64_t now) {
    double baseline = 0;
    double recent = 0;
    std::size_t count = 0;
    double previous = 0;
    std::size_t positive_steps = 0;
    for (const FrameEvidence& frame : window_) {
        if (!frame.fire_box.valid() || frame.fire_box.area() < thresholds_.growth_minimum_area) continue;
        if (now - frame.monotonic_ns > thresholds_.growth_window_ns) continue;
        const double area = frame.fire_box.area();
        if (baseline == 0) baseline = area;
        recent = count == 0 ? area : 0.35 * area + 0.65 * recent;
        if (previous > 0 && area > previous) ++positive_steps;
        previous = area;
        ++count;
    }
    snapshot_.growth_stable = false;
    snapshot_.fire_region_growth_percent = 0;
    if (count >= 4 && baseline >= thresholds_.growth_minimum_area) {
        const double growth = (recent - baseline) / baseline * 100.0;
        if (growth >= thresholds_.growth_minimum_percent && positive_steps >= 2) {
            snapshot_.growth_stable = true;
            snapshot_.fire_region_growth_percent = growth;
        }
    }
}

void IncidentEngine::update_sequence_observation() {
    snapshot_.smoke_first_known = false;
    if (first_smoke_ns_ == 0 || first_fire_ns_ == 0) return;
    const double difference = static_cast<double>(
        first_smoke_ns_ > first_fire_ns_ ? first_smoke_ns_ - first_fire_ns_
                                        : first_fire_ns_ - first_smoke_ns_) /
        1'000'000'000.0;
    if (difference <= thresholds_.timing_uncertainty_seconds) return;
    snapshot_.smoke_first_known = true;
    snapshot_.smoke_first = first_smoke_ns_ < first_fire_ns_;
    snapshot_.smoke_to_fire_delay_seconds = difference;
}

void IncidentEngine::confirm_visual(std::uint64_t now) {
    snapshot_.hazard_state = HazardState::Confirmed;
    snapshot_.response_state = ResponseState::AwaitingResponse;
    snapshot_.was_confirmed = true;
    snapshot_.updated_ns = now;
}

bool IncidentEngine::cancel(const std::string&) {
    if (!snapshot_.was_confirmed || snapshot_.response_state == ResponseState::CallConnected ||
        snapshot_.response_state == ResponseState::CallCompleted)
        return false;
    snapshot_.response_state = ResponseState::Cancelled;
    return true;
}

bool IncidentEngine::confirm_occupant() {
    if (!snapshot_.was_confirmed || snapshot_.response_state == ResponseState::Cancelled) return false;
    snapshot_.response_state = ResponseState::Escalating;
    return true;
}

bool IncidentEngine::manual_reset() {
    if (snapshot_.response_state != ResponseState::Cancelled &&
        snapshot_.response_state != ResponseState::CallCompleted &&
        snapshot_.response_state != ResponseState::CallFailed)
        return false;
    snapshot_.hazard_state = HazardState::Resolved;
    window_.clear();
    return true;
}

void IncidentEngine::set_degraded(bool degraded) {
    degraded_ = degraded;
    if (degraded) snapshot_.hazard_state = HazardState::Degraded;
    else if (snapshot_.was_confirmed) snapshot_.hazard_state = HazardState::Confirmed;
    else snapshot_.hazard_state = HazardState::Clear;
}

}  // namespace ignis

