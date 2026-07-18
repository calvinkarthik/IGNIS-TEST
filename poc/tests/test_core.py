from __future__ import annotations

from ignis_poc.core import Detection, FireVerifier


FIRE = Detection("fire", 0, 0.9, (0.1, 0.2, 0.5, 0.7))


def test_one_frame_never_confirms() -> None:
    verifier = FireVerifier("device", "boot")
    assert verifier.update(0, [FIRE]).hazard_state == "SUSPECTED"
    for index in range(1, 7):
        state = verifier.update(index * 400_000_000, [])
    assert state.hazard_state == "CLEAR"
    assert state.incident_id is None


def test_six_of_ten_over_time_confirms() -> None:
    verifier = FireVerifier("device", "boot")
    pattern = [True, True, False, True, False, True, True, True]
    states = []
    for index, positive in enumerate(pattern):
        states.append(verifier.update(index * 300_000_000, [FIRE] if positive else []))
    assert states[-1].hazard_state == "CONFIRMED"
    assert states[-1].confirmed is True


def test_short_false_event_does_not_seed_later_incident() -> None:
    verifier = FireVerifier("device", "boot", required=6)
    verifier.update(0, [FIRE])
    verifier.update(2_100_000_000, [])
    for index in range(5):
        state = verifier.update(5_000_000_000 + index * 500_000_000, [FIRE])
    assert state.hazard_state == "VERIFYING"
    assert state.confirmed is False


def test_confirmed_signature_loss_is_not_called_safe() -> None:
    verifier = FireVerifier("device", "boot")
    for index in range(6):
        state = verifier.update(index * 300_000_000, [FIRE])
    assert state.confirmed is True
    state = verifier.update(4_000_000_000, [])
    assert state.hazard_state == "VISUAL_SIGNATURE_LOST"
    assert state.confirmed is True
