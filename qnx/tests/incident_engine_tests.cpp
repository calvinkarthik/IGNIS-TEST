#include "ignis/incident.hpp"

#include <iostream>

#include "test_support.hpp"

namespace {

ignis::FrameEvidence frame(
    std::uint64_t sequence,
    double seconds,
    double fire,
    double smoke = 0,
    double size = 0.2) {
    ignis::FrameEvidence value;
    value.sequence = sequence;
    value.monotonic_ns = 1'000'000'000ULL + static_cast<std::uint64_t>(seconds * 1e9);
    value.fire_confidence = fire;
    value.smoke_confidence = smoke;
    value.fire_box = {0.2, 0.2, 0.2 + size, 0.2 + size};
    value.smoke_box = {0.1, 0.1, 0.6, 0.6};
    value.zone = "Stovetop";
    return value;
}

}  // namespace

int main() {
    using namespace ignis;

    // One frame must not verify or confirm and clears after the grace period.
    IncidentEngine single("device", "boot");
    REQUIRE(single.process(frame(1, 0, 0.60)).hazard_state == HazardState::Suspected);
    REQUIRE(single.process(frame(2, 2.1, 0)).hazard_state == HazardState::Clear);
    REQUIRE(!single.snapshot().was_confirmed);

    // Exactly six relevant frames in ten verify; five do not.
    IncidentEngine six("device", "six");
    for (std::uint64_t i = 1; i <= 6; ++i) six.process(frame(i, i * 0.1, 0.60));
    REQUIRE(six.snapshot().hazard_state == HazardState::Verifying);
    IncidentEngine five("device", "five");
    for (std::uint64_t i = 1; i <= 5; ++i) five.process(frame(i, i * 0.1, 0.60));
    for (std::uint64_t i = 6; i <= 10; ++i) five.process(frame(i, i * 0.1, 0));
    REQUIRE(five.snapshot().hazard_state == HazardState::Suspected);

    // Sustained high-confidence fire confirms only after two actual seconds.
    IncidentEngine sustained("device", "sustained");
    for (std::uint64_t i = 1; i <= 9; ++i)
        sustained.process(frame(i, (i - 1) * 0.25, 0.80));
    REQUIRE(sustained.snapshot().hazard_state == HazardState::Confirmed);
    REQUIRE(sustained.snapshot().response_state == ResponseState::AwaitingResponse);

    IncidentEngine disappeared("device", "gone");
    for (std::uint64_t i = 1; i <= 6; ++i)
        disappeared.process(frame(i, (i - 1) * 0.2, 0.60));
    disappeared.process(frame(7, 3.2, 0));
    REQUIRE(disappeared.snapshot().hazard_state == HazardState::Clear);

    // Persistent co-occurring fire and smoke is a separate confirmation rule.
    IncidentEngine cooccurrence("device", "co");
    for (std::uint64_t i = 1; i <= 6; ++i)
        cooccurrence.process(frame(i, (i - 1) * 0.25, 0.60, 0.70));
    REQUIRE(cooccurrence.snapshot().hazard_state == HazardState::Confirmed);

    // Stable area growth confirms; tiny boxes are rejected.
    IncidentEngine growth("device", "growth");
    for (std::uint64_t i = 1; i <= 7; ++i)
        growth.process(frame(i, i * 0.2, 0.60, 0, 0.10 + i * 0.025));
    REQUIRE(growth.snapshot().growth_stable);
    REQUIRE(growth.snapshot().hazard_state == HazardState::Confirmed);
    IncidentEngine tiny("device", "tiny");
    for (std::uint64_t i = 1; i <= 7; ++i)
        tiny.process(frame(i, i * 0.2, 0.60, 0, 0.002 + i * 0.001));
    REQUIRE(!tiny.snapshot().growth_stable);

    // Smoke-first evidence needs a difference larger than the uncertainty margin.
    IncidentEngine sequence("device", "sequence");
    sequence.process(frame(1, 0, 0, 0.70));
    sequence.process(frame(2, 1.2, 0.60, 0.70));
    REQUIRE(sequence.snapshot().smoke_first_known);
    REQUIRE(sequence.snapshot().smoke_first);

    // Duplicate/out-of-order frames do not rewrite state.
    const std::uint64_t before = sequence.snapshot().updated_ns;
    sequence.process(frame(2, 9, 0.99, 0.99));
    REQUIRE(sequence.snapshot().updated_ns == before);

    REQUIRE(sustained.confirm_occupant());
    REQUIRE(sustained.snapshot().response_state == ResponseState::Escalating);
    REQUIRE(sustained.cancel("controlled flame"));
    REQUIRE(sustained.snapshot().hazard_state == HazardState::Confirmed);
    REQUIRE(sustained.snapshot().response_state == ResponseState::Cancelled);
    REQUIRE(sustained.manual_reset());
    REQUIRE(sustained.snapshot().hazard_state == HazardState::Resolved);

    sustained.set_degraded(true);
    REQUIRE(sustained.snapshot().hazard_state == HazardState::Degraded);
    sustained.set_degraded(false);
    REQUIRE(sustained.snapshot().hazard_state == HazardState::Confirmed);

    std::cout << "incident_engine_tests: all assertions passed\n";
    return 0;
}

