from __future__ import annotations

import math
import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class HazardState(StrEnum):
    CLEAR = "CLEAR"
    SUSPECTED = "SUSPECTED"
    VERIFYING = "VERIFYING"
    CONFIRMED = "CONFIRMED"
    VISUAL_SIGNATURE_LOST = "VISUAL_SIGNATURE_LOST"
    RESOLVED = "RESOLVED"
    DEGRADED = "DEGRADED"


class ResponseState(StrEnum):
    IDLE = "IDLE"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    CANCELLED = "CANCELLED"
    ESCALATING = "ESCALATING"
    CALL_REQUESTED = "CALL_REQUESTED"
    CALL_INITIATED = "CALL_INITIATED"
    CALL_CONNECTED = "CALL_CONNECTED"
    CALL_COMPLETED = "CALL_COMPLETED"
    CALL_FAILED = "CALL_FAILED"


class ManualConfirmation(BaseModel):
    source: Literal["manual", "voice_agent"] = "manual"
    note: str = Field(default="Occupant confirmed visible fire", max_length=240)


class Cancellation(BaseModel):
    source: Literal["manual", "voice_agent"] = "manual"
    reason: Literal["controlled_flame", "false_alarm", "testing", "other"]
    note: str = Field(default="", max_length=240)


class ResetRequest(BaseModel):
    source: Literal["manual"] = "manual"
    note: str = Field(default="", max_length=240)


class Point(BaseModel):
    x: float
    y: float

    @model_validator(mode="before")
    @classmethod
    def from_pair(cls, value: Any) -> Any:
        if isinstance(value, list | tuple) and len(value) == 2:
            return {"x": value[0], "y": value[1]}
        return value

    @model_validator(mode="after")
    def validate_normalized(self) -> Point:
        if not all(math.isfinite(value) and 0 <= value <= 1 for value in (self.x, self.y)):
            raise ValueError("zone points must be finite normalized coordinates")
        return self


def _polygon_area(points: list[Point]) -> float:
    return abs(
        sum(
            point.x * points[(index + 1) % len(points)].y
            - points[(index + 1) % len(points)].x * point.y
            for index, point in enumerate(points)
        )
        / 2
    )


class Zone(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
    name: str = Field(min_length=1, max_length=48)
    points: list[Point] = Field(min_length=3, max_length=32)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, value: str) -> str:
        clean = re.sub(r"[^A-Za-z0-9 .,'()&-]", "", value).strip()
        if not clean:
            raise ValueError("zone name contains no safe characters")
        return clean

    @model_validator(mode="after")
    def validate_area(self) -> Zone:
        if _polygon_area(self.points) < 0.0001:
            raise ValueError("zone polygon area is too small")
        return self


class ZoneConfiguration(BaseModel):
    schema_version: Literal[1] = 1
    configuration_version: int = Field(ge=1)
    frame_aspect_ratio: float = Field(gt=0, le=10)
    zones: list[Zone] = Field(max_length=32)

    @model_validator(mode="after")
    def unique_fields(self) -> ZoneConfiguration:
        ids = [zone.id for zone in self.zones]
        names = [zone.name.casefold() for zone in self.zones]
        if len(ids) != len(set(ids)) or len(names) != len(set(names)):
            raise ValueError("zone ids and names must be unique")
        return self


class ProviderStatus(BaseModel):
    incident_id: str = Field(min_length=1, max_length=160)
    status: Literal["connected", "completed", "failed"]
    conversation_id: str | None = Field(default=None, max_length=160)
    call_sid: str | None = Field(default=None, max_length=160)
    error_code: str | None = Field(default=None, max_length=80)


class IncidentUpdate(BaseModel):
    incident_id: str = Field(min_length=1, max_length=160)
    device_id: str | None = Field(default=None, max_length=80)
    boot_id: str | None = Field(default=None, max_length=80)
    hazard_state: HazardState
    response_state: ResponseState
    first_detection_monotonic_ns: int = Field(ge=0)
    updated_monotonic_ns: int = Field(ge=0)
    fire_confidence: float = Field(default=0, ge=0, le=1)
    smoke_confidence: float = Field(default=0, ge=0, le=1)
    seconds_persistent: float = Field(default=0, ge=0)
    first_zone: str = Field(default="Unconfigured area", max_length=48)
    current_zone: str = Field(default="Unconfigured area", max_length=48)
    primary_fire_bbox: list[float] | None = None
    primary_smoke_bbox: list[float] | None = None
    fire_region_growth_percent: float | None = None
    smoke_first: bool | None = None
    smoke_to_fire_delay_seconds: float | None = None
    occupant_visible: bool | None = None
    camera_health: str = Field(default="UNKNOWN", max_length=32)
    inference_health: str = Field(default="UNKNOWN", max_length=32)


JsonObject = dict[str, Any]
