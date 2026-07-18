from __future__ import annotations

import asyncio
import logging

from .communications import CommunicationError, ElevenLabsService
from .config import Settings
from .database import Database
from .websockets import WebSocketHub

logger = logging.getLogger(__name__)


class ResponseTimeoutManager:
    """Deterministic timeout enforcement independent of voice-agent behavior."""

    def __init__(
        self,
        settings: Settings,
        database: Database,
        hub: WebSocketHub,
        communications: ElevenLabsService,
    ) -> None:
        self.settings = settings
        self.database = database
        self.hub = hub
        self.communications = communications
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._closed = False

    def observe(self, incident_id: str) -> None:
        incident = self.database.get_incident(incident_id)
        if not incident or incident["response_state"] != "AWAITING_RESPONSE":
            return
        existing = self._tasks.get(incident_id)
        if existing is None or existing.done():
            self._tasks[incident_id] = asyncio.create_task(self._wait(incident_id))

    def cancel(self, incident_id: str) -> None:
        task = self._tasks.pop(incident_id, None)
        if task:
            task.cancel()

    async def _wait(self, incident_id: str) -> None:
        try:
            await asyncio.sleep(self.settings.response_timeout_seconds)
            incident = self.database.get_incident(incident_id)
            if not incident:
                return
            if incident["response_state"] != "AWAITING_RESPONSE":
                return
            if incident["hazard_state"] not in {"CONFIRMED", "VISUAL_SIGNATURE_LOST"}:
                return
            incident = self.database.update_incident_response(
                incident_id, "ESCALATING", "no_response"
            )
            event = self.database.add_event(
                incident_id,
                "NO_OCCUPANT_RESPONSE",
                "backend_timeout",
                {"timeout_seconds": self.settings.response_timeout_seconds},
            )
            await self.hub.broadcast("timeline_event", event)
            await self.hub.broadcast("incident_update", incident)
            if self.settings.demo_calls_enabled:
                try:
                    result = await self.communications.request_demo_call(incident_id)
                    await self.hub.broadcast("call_update", result)
                except CommunicationError as exc:
                    await self.hub.broadcast(
                        "call_update", {"status": "BLOCKED", "reason": exc.code}
                    )
            else:
                await self.hub.broadcast(
                    "call_update",
                    {"status": "BLOCKED", "reason": "demo_calls_disabled"},
                )
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("response timeout failed for incident %s", incident_id)
        finally:
            self._tasks.pop(incident_id, None)

    async def close(self) -> None:
        self._closed = True
        tasks = tuple(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

