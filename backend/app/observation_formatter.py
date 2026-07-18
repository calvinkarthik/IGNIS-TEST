from __future__ import annotations

import re
from typing import Any


def sanitize_zone(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9 .,'()&-]", "", str(value or "")).strip()[:48]
    return text or "unconfigured area"


def _rounded_duration(seconds: float | int | None) -> str | None:
    if seconds is None or seconds < 0.75:
        return None
    value = round(float(seconds))
    words = {
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
        9: "nine",
        10: "ten",
    }
    return words.get(value, str(value))


def format_observations(data: dict[str, Any]) -> dict[str, str]:
    zone = sanitize_zone(data.get("first_zone"))
    delay = _rounded_duration(data.get("smoke_to_fire_delay_seconds"))
    smoke_first = data.get("smoke_first")
    growth = data.get("fire_region_growth_percent")
    occupant = data.get("occupant_visible")

    if zone.casefold() in {"unconfigured area", "general room", "unknown"}:
        origin = "The source is not visible from the camera."
    else:
        origin = f"Visible flames first appeared in the configured {zone.lower()} zone."

    if smoke_first is True and delay:
        sequence = f"Smoke was detected approximately {delay} seconds before visible flames."
    elif smoke_first is False and delay:
        sequence = f"Visible flames were detected approximately {delay} seconds before smoke."
    else:
        sequence = "The visual sequence could not be determined reliably."

    if isinstance(growth, int | float) and 20 <= growth <= 1000:
        growth_text = "The visible fire region expanded during verification."
    else:
        growth_text = "Stable visual-region growth was not established."

    occupant_text = {
        True: "An occupant was visibly detected.",
        False: "No occupant was visibly detected in the available frame.",
        None: "Occupant visibility was not determined.",
    }[occupant if occupant in {True, False, None} else None]

    return {
        "observed_origin": origin[:180],
        "sequence_observation": sequence[:180],
        "growth_observation": growth_text,
        "occupant_observation": occupant_text,
        "cause_statement": "The exact cause is unconfirmed.",
    }
