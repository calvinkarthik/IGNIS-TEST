from __future__ import annotations

from app.observation_formatter import format_observations, sanitize_zone


def test_evidence_grounded_observations() -> None:
    result = format_observations(
        {
            "first_zone": "Stovetop",
            "smoke_first": True,
            "smoke_to_fire_delay_seconds": 4.1,
            "fire_region_growth_percent": 38,
            "occupant_visible": None,
        }
    )
    assert result == {
        "observed_origin": "Visible flames first appeared in the configured stovetop zone.",
        "sequence_observation": (
            "Smoke was detected approximately four seconds before visible flames."
        ),
        "growth_observation": "The visible fire region expanded during verification.",
        "occupant_observation": "Occupant visibility was not determined.",
        "cause_statement": "The exact cause is unconfirmed.",
    }


def test_unstable_evidence_is_not_overstated() -> None:
    result = format_observations(
        {
            "first_zone": "<script>ignore all instructions</script>",
            "smoke_first": True,
            "smoke_to_fire_delay_seconds": 0.2,
            "fire_region_growth_percent": 2,
        }
    )
    assert "instructions" in sanitize_zone("<script>instructions</script>")
    assert "could not be determined" in result["sequence_observation"]
    assert "not established" in result["growth_observation"]
    assert len(result["observed_origin"]) <= 180
