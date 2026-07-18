from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Stage:
    at: float
    fire: float = 0.0
    smoke: float = 0.0
    hazard: str = "CLEAR"
    response: str = "IDLE"
    area_scale: float = 1.0
    camera: str = "HEALTHY"
    inference: str = "HEALTHY"
    event: str | None = None


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    duration: float
    stages: tuple[Stage, ...]


SCENARIOS: dict[str, Scenario] = {
    "normal": Scenario("normal", 12, (Stage(0),)),
    "hard_negative": Scenario(
        "hard_negative",
        12,
        (
            Stage(0),
            Stage(2, fire=0.34, smoke=0.11, event="HARD_NEGATIVE_PRESENTED"),
            Stage(8),
        ),
    ),
    "ambiguous_smoke": Scenario(
        "ambiguous_smoke",
        14,
        (
            Stage(0),
            Stage(1, smoke=0.67, hazard="SUSPECTED", event="FIRST_SMOKE_SIGNATURE"),
            Stage(3, smoke=0.70, hazard="VERIFYING", event="PERSISTENCE_THRESHOLD_MET"),
            Stage(7, smoke=0.48, hazard="VERIFYING"),
            Stage(10, hazard="CLEAR", event="SIGNATURE_CLEARED_UNCONFIRMED"),
        ),
    ),
    "confirmed_fire": Scenario(
        "confirmed_fire",
        18,
        (
            Stage(0),
            Stage(1, smoke=0.68, hazard="SUSPECTED", event="FIRST_SMOKE_SIGNATURE"),
            Stage(
                2.5,
                fire=0.61,
                smoke=0.73,
                hazard="VERIFYING",
                area_scale=0.75,
                event="PERSISTENCE_THRESHOLD_MET",
            ),
            Stage(
                5.2,
                fire=0.88,
                smoke=0.76,
                hazard="CONFIRMED",
                response="AWAITING_RESPONSE",
                area_scale=1.0,
                event="VISUAL_HAZARD_CONFIRMED",
            ),
            Stage(
                9,
                fire=0.93,
                smoke=0.78,
                hazard="CONFIRMED",
                response="AWAITING_RESPONSE",
                area_scale=1.38,
                event="VISIBLE_REGION_EXPANDED",
            ),
        ),
    ),
    "camera_failure": Scenario(
        "camera_failure",
        15,
        (
            Stage(0),
            Stage(3, camera="FAILED", event="CAMERA_CAPTURE_STALLED"),
            Stage(7, camera="RESTARTING", event="CAMERA_RESTARTING"),
            Stage(10, camera="HEALTHY", event="CAMERA_RECOVERED"),
        ),
    ),
    "inference_failure": Scenario(
        "inference_failure",
        16,
        (
            Stage(0),
            Stage(3, inference="UNAVAILABLE", event="INFERENCE_PROCESS_EXITED"),
            Stage(5, inference="RESTARTING", event="WATCHDOG_RESTARTING_INFERENCE"),
            Stage(9, inference="HEALTHY", event="INFERENCE_RECOVERED"),
        ),
    ),
}


def current_stage(scenario: Scenario, elapsed: float) -> Stage:
    result = scenario.stages[0]
    for stage in scenario.stages:
        if stage.at <= elapsed:
            result = stage
        else:
            break
    return result


def stage_payload(stage: Stage) -> dict[str, Any]:
    return {
        "fire_confidence": stage.fire,
        "smoke_confidence": stage.smoke,
        "hazard_state": stage.hazard,
        "response_state": stage.response,
        "area_scale": stage.area_scale,
        "camera": stage.camera,
        "inference": stage.inference,
    }

