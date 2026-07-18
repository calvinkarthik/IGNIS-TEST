from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

import httpx

from .config import Settings
from .database import CallPolicyError, Database
from .observation_formatter import format_observations, sanitize_zone


class CommunicationError(RuntimeError):
    def __init__(self, code: str, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


E164 = re.compile(r"^\+[1-9]\d{7,14}$")
EMERGENCY_NUMBERS = {"000", "110", "112", "118", "119", "911", "999"}


def validate_destination(destination: str, allowed: tuple[str, ...]) -> None:
    if not E164.fullmatch(destination):
        raise CommunicationError("destination_not_valid_e164")
    digits = destination.lstrip("+")
    if digits in EMERGENCY_NUMBERS or digits[-3:] in EMERGENCY_NUMBERS:
        raise CommunicationError("emergency_numbers_are_forbidden", 403)
    if destination not in allowed:
        raise CommunicationError("destination_not_allowlisted", 403)


def destination_hash(destination: str) -> str:
    return hashlib.sha256(destination.encode("utf-8")).hexdigest()


def mask_destination(destination: str) -> str:
    return f"{destination[:2]}••••••{destination[-2:]}" if len(destination) >= 6 else "[masked]"


def safe_incident_context(incident: dict[str, Any]) -> dict[str, Any]:
    observations = format_observations(
        {
            **incident,
            "fire_region_growth_percent": incident.get("fire_region_growth_percent")
            if "fire_region_growth_percent" in incident
            else incident.get("max_growth_percent"),
        }
    )
    return {
        "incident_id": incident["incident_id"],
        "hazard_state": incident["hazard_state"],
        "response_state": incident["response_state"],
        "zone": sanitize_zone(incident.get("first_zone")),
        "fire_confidence_percent": round(100 * float(incident.get("peak_fire_confidence") or 0)),
        "smoke_confidence_percent": round(
            100 * float(incident.get("peak_smoke_confidence") or 0)
        ),
        "duration_seconds": round(float(incident.get("seconds_persistent") or 0), 1),
        "smoke_first": incident.get("smoke_first"),
        "smoke_to_fire_delay_seconds": incident.get("smoke_to_fire_delay_seconds"),
        "fire_region_growth_percent": incident.get("max_growth_percent"),
        "occupant_visible": (
            "unknown"
            if incident.get("occupant_visible") is None
            else str(bool(incident["occupant_visible"])).lower()
        ),
        **observations,
        "prototype_notice": "This is an IGNIS demonstration system.",
    }


class ElevenLabsService:
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5, read=12, write=8, pool=5),
            headers={"User-Agent": "ignis/0.1.0"},
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def signed_url(self) -> str:
        if not self.settings.elevenlabs_api_key or not self.settings.occupant_agent_id:
            raise CommunicationError("voice_not_configured", 503)
        response = await self.client.get(
            "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url",
            params={"agent_id": self.settings.occupant_agent_id},
            headers={"xi-api-key": self.settings.elevenlabs_api_key},
        )
        if response.status_code >= 400:
            raise CommunicationError("signed_url_provider_error", 502)
        signed_url = response.json().get("signed_url")
        if not isinstance(signed_url, str) or not signed_url.startswith("wss://"):
            raise CommunicationError("signed_url_provider_response_invalid", 502)
        return signed_url

    async def request_demo_call(self, incident_id: str) -> dict[str, Any]:
        settings = self.settings
        if not settings.demo_calls_enabled:
            raise CommunicationError("demo_calls_disabled", 403)
        destination = settings.demo_dispatch_number
        validate_destination(destination, settings.demo_allowed_numbers)
        incident = self.database.get_incident(incident_id)
        if incident is None:
            raise CommunicationError("incident_not_found", 404)
        if incident.get("confirmed_at") is None:
            raise CommunicationError("incident_not_visually_confirmed", 409)
        if incident.get("response_state") == "CANCELLED":
            raise CommunicationError("incident_cancelled", 409)
        if settings.call_provider == "elevenlabs" and not all(
            [settings.elevenlabs_api_key, settings.dispatch_agent_id, settings.phone_number_id]
        ):
            raise CommunicationError("dispatch_provider_not_configured", 503)

        try:
            attempt_id = self.database.reserve_call_attempt(
                incident_id,
                destination_hash(destination),
                settings.global_call_cooldown_seconds,
                settings.max_calls_per_incident,
            )
        except CallPolicyError as exc:
            raise CommunicationError(str(exc), 409) from exc

        context = safe_incident_context(incident)
        dynamic_variables = {
            "incident_id": context["incident_id"],
            "location": context["zone"],
            "duration_seconds": str(context["duration_seconds"]),
            "fire_confidence": f"{context['fire_confidence_percent']}%",
            "smoke_confidence": f"{context['smoke_confidence_percent']}%",
            "observed_origin": context["observed_origin"],
            "smoke_timing": context["sequence_observation"],
            "growth_observation": context["growth_observation"],
            "occupant_response": (
                "The occupant confirmed the emergency."
                if incident.get("occupant_response") == "confirmed"
                else "No occupant response was received."
            ),
            "occupant_visibility": context["occupant_observation"],
            "cause_statement": context["cause_statement"],
            "demo_notice": "This is an automated IGNIS demonstration alert.",
        }

        if settings.call_provider == "mock":
            conversation_id = f"mock-{attempt_id}"
            self.database.update_call_attempt(
                attempt_id, "INITIATED", conversation_id=conversation_id
            )
            return {
                "status": "CALL_REQUEST_ACCEPTED",
                "connection_status": "UNKNOWN",
                "provider": "mock",
                "conversation_id": conversation_id,
                "destination": mask_destination(destination),
            }

        payload = {
            "agent_id": settings.dispatch_agent_id,
            "agent_phone_number_id": settings.phone_number_id,
            "to_number": destination,
            "conversation_initiation_client_data": {
                "dynamic_variables": dynamic_variables,
                "environment": settings.elevenlabs_environment,
            },
        }
        try:
            response = await self.client.post(
                "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
                json=payload,
                headers={"xi-api-key": settings.elevenlabs_api_key},
            )
        except httpx.TimeoutException as exc:
            self.database.update_call_attempt(
                attempt_id,
                "UNKNOWN",
                error_code="provider_timeout",
                error_message_safe="Provider outcome is unknown; automatic retry was suppressed.",
            )
            raise CommunicationError("call_provider_outcome_unknown", 502) from exc
        except httpx.HTTPError as exc:
            self.database.update_call_attempt(
                attempt_id,
                "FAILED",
                error_code="provider_connection_error",
                error_message_safe="Could not reach the configured call provider.",
            )
            raise CommunicationError("call_provider_connection_error", 502) from exc

        if response.status_code >= 400:
            self.database.update_call_attempt(
                attempt_id,
                "FAILED",
                error_code=f"provider_http_{response.status_code}",
                error_message_safe="The call provider rejected the request.",
            )
            raise CommunicationError("call_provider_rejected_request", 502)
        body = response.json()
        conversation_id = body.get("conversation_id")
        call_sid = body.get("callSid")
        self.database.update_call_attempt(
            attempt_id,
            "INITIATED",
            conversation_id=str(conversation_id) if conversation_id else None,
            call_sid=str(call_sid) if call_sid else None,
        )
        return {
            "status": "CALL_REQUEST_ACCEPTED",
            "connection_status": "UNKNOWN",
            "provider": "elevenlabs_twilio",
            "conversation_id": conversation_id,
            "destination": mask_destination(destination),
        }

    def authenticate_provider_webhook(self, supplied: str | None) -> bool:
        secret = self.settings.provider_webhook_secret
        return bool(secret and supplied and hmac.compare_digest(secret, supplied))
