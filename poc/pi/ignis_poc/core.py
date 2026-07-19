from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Detection:
    class_name: str
    class_id: int
    confidence: float
    bbox: tuple[float, float, float, float]

    def as_json(self) -> dict:
        x_min, y_min, x_max, y_max = self.bbox
        return {
            "class_name": self.class_name,
            "class_id": self.class_id,
            "confidence": round(self.confidence, 5),
            "bbox": {
                "x_min": x_min,
                "y_min": y_min,
                "x_max": x_max,
                "y_max": y_max,
            },
        }


@dataclass(slots=True)
class FireState:
    hazard_state: str = "CLEAR"
    incident_id: str | None = None
    first_detection_ns: int = 0
    last_relevant_ns: int = 0
    confirmed: bool = False
    fire_confidence: float = 0.0
    smoke_confidence: float = 0.0
    seconds_persistent: float = 0.0


class FireVerifier:
    """Small deterministic POC gate; one ML output cannot produce CONFIRMED."""

    def __init__(
        self,
        device_id: str,
        boot_id: str,
        window: int = 10,
        required: int = 6,
        fire_threshold: float = 0.55,
        smoke_threshold: float = 0.65,
        confirm_seconds: float = 1.5,
        clear_seconds: float = 5.0,
        reset_seconds: float = 10.0,
    ) -> None:
        self.device_id = device_id
        self.boot_id = boot_id
        self.window = deque(maxlen=window)
        self.required = required
        self.fire_threshold = fire_threshold
        self.smoke_threshold = smoke_threshold
        self.confirm_ns = int(confirm_seconds * 1e9)
        self.clear_ns = int(clear_seconds * 1e9)
        self.reset_ns = int(reset_seconds * 1e9)
        self.counter = 0
        self.state = FireState()

    def update(self, monotonic_ns: int, detections: list[Detection]) -> FireState:
        fire = max((item.confidence for item in detections if item.class_name == "fire"), default=0.0)
        smoke = max((item.confidence for item in detections if item.class_name == "smoke"), default=0.0)
        relevant = fire >= self.fire_threshold or smoke >= self.smoke_threshold
        self.window.append(relevant)
        state = self.state
        state.fire_confidence = fire
        state.smoke_confidence = smoke
        if relevant:
            state.last_relevant_ns = monotonic_ns
            if state.incident_id is None:
                self.counter += 1
                state.incident_id = f"{self.device_id}-{self.boot_id}-{self.counter}"
                state.first_detection_ns = monotonic_ns
                state.hazard_state = "SUSPECTED"
            state.seconds_persistent = (monotonic_ns - state.first_detection_ns) / 1e9
            hits = sum(self.window)
            if hits >= max(3, self.required // 2) and not state.confirmed:
                state.hazard_state = "VERIFYING"
            if hits >= self.required and monotonic_ns - state.first_detection_ns >= self.confirm_ns:
                state.hazard_state = "CONFIRMED"
                state.confirmed = True
        elif state.incident_id:
            missing_ns = monotonic_ns - state.last_relevant_ns
            if state.confirmed and missing_ns >= self.reset_ns:
                self.window.clear()
                self.state = FireState()
                state = self.state
            elif state.confirmed and missing_ns >= self.clear_ns:
                state.hazard_state = "VISUAL_SIGNATURE_LOST"
            elif not state.confirmed and missing_ns >= self.clear_ns:
                self.window.clear()
                self.state = FireState()
                state = self.state
        return state
