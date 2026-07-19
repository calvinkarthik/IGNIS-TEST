from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .communications import (
    CommunicationError,
    ElevenLabsService,
    safe_incident_context,
)
from .config import Settings
from .database import Database, DatabaseError
from .device_registry import DeviceRegistry
from .escalation import ResponseTimeoutManager
from .logging_config import configure_logging
from .models import (
    Cancellation,
    ManualConfirmation,
    ProviderStatus,
    ResetRequest,
    ZoneConfiguration,
)
from .protocol import PacketType
from .rate_limit import RateLimiter
from .tcp_server import DeviceTcpServer
from .websockets import WebSocketHub

ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def create_app(settings: Settings | None = None) -> FastAPI:
    selected_settings = settings or Settings.from_env()
    configure_logging(
        selected_settings.log_level, selected_settings.app_env == "production"
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(selected_settings.database_path)
        database.initialize()
        hub = WebSocketHub()
        registry = DeviceRegistry()
        communications = ElevenLabsService(selected_settings, database)
        timeout_manager = ResponseTimeoutManager(
            selected_settings, database, hub, communications
        )
        tcp_server = DeviceTcpServer(selected_settings, database, hub, registry)
        limiter = RateLimiter(selected_settings.action_rate_limit_per_minute)
        tcp_server.incident_observer = timeout_manager.observe
        app.state.armed = False
        tcp_server.arming_state = lambda: bool(app.state.armed)

        if database.get_configuration("zones") is None:
            zones = _load_json(ROOT / "config" / "zones.example.json")
            database.put_configuration("zones", int(zones["configuration_version"]), zones)
        if database.get_configuration("thresholds") is None:
            thresholds = _load_json(ROOT / "config" / "thresholds.example.json")
            database.put_configuration(
                "thresholds", int(thresholds["configuration_version"]), thresholds
            )

        async def snapshot() -> dict[str, Any]:
            return {
                "demo_system": True,
                "demo_calls_enabled": selected_settings.demo_calls_enabled,
                "armed": bool(app.state.armed),
                "devices": database.list_devices(),
                "incidents": database.list_incidents(25),
                "latest_frame": registry.latest_frame,
                "latest_detections": registry.latest_detections,
                "health": registry.latest_health,
                "zones": database.get_configuration("zones"),
            }

        hub.snapshot_factory = snapshot
        app.state.settings = selected_settings
        app.state.database = database
        app.state.hub = hub
        app.state.registry = registry
        app.state.communications = communications
        app.state.timeout_manager = timeout_manager
        app.state.tcp_server = tcp_server
        app.state.rate_limiter = limiter
        await tcp_server.start()
        try:
            yield
        finally:
            await timeout_manager.close()
            await tcp_server.close()
            await communications.close()
            database.close()

    app = FastAPI(
        title="IGNIS API",
        version="0.1.0",
        description="Coordination API for the IGNIS demonstration system.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[selected_settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "X-Ignis-Webhook-Secret"],
    )

    def db(request: Request) -> Database:
        return request.app.state.database

    def require_rate_limit(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        if not request.app.state.rate_limiter.allow(client):
            raise HTTPException(status_code=429, detail="action_rate_limit_exceeded")

    def get_incident_or_404(request: Request, incident_id: str) -> dict[str, Any]:
        incident = db(request).get_incident(incident_id)
        if incident is None:
            raise HTTPException(status_code=404, detail="incident_not_found")
        return incident

    async def announce_action(
        request: Request,
        incident: dict[str, Any],
        event: dict[str, Any],
        packet_type: PacketType,
        packet_payload: dict[str, Any],
    ) -> str:
        delivery = await request.app.state.registry.send_control(
            incident["device_id"], packet_type, packet_payload
        )
        await request.app.state.hub.broadcast("timeline_event", event)
        await request.app.state.hub.broadcast("incident_update", incident)
        return delivery

    @app.exception_handler(CommunicationError)
    async def communication_exception(_: Request, exc: CommunicationError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.code})

    @app.get("/api/health")
    async def health(request: Request) -> dict[str, Any]:
        devices = db(request).list_devices()
        device = devices[0] if devices else None
        device_health = (device or {}).get("health") or {}
        qnx_connected = bool(device and device.get("connected"))
        inference = device_health.get("inference", "UNKNOWN")
        overall = "HEALTHY" if qnx_connected and inference == "HEALTHY" else "DEGRADED"
        return {
            "status": overall,
            "backend": "HEALTHY",
            "qnx_connected": qnx_connected,
            "camera": device_health.get("camera", "UNKNOWN"),
            "inference": inference,
            "incident_engine": device_health.get("incident_engine", "UNKNOWN"),
            "stream": "HEALTHY",
            "last_frame_age_ms": device_health.get("last_frame_age_ms"),
            "last_inference_age_ms": device_health.get("last_inference_age_ms"),
            "watchdog_restart_count": device_health.get("watchdog_restart_count", 0),
            "demo_system": True,
            "demo_calls_enabled": request.app.state.settings.demo_calls_enabled,
            "armed": bool(request.app.state.armed),
            "websocket_clients": request.app.state.hub.client_count,
        }

    @app.get("/api/arming")
    async def get_arming(request: Request) -> dict[str, Any]:
        return {"armed": bool(request.app.state.armed)}

    @app.put("/api/arming")
    async def put_arming(request: Request, body: dict[str, Any]) -> dict[str, Any]:
        require_rate_limit(request)
        armed = bool(body.get("armed"))
        request.app.state.armed = armed
        payload = {"armed": armed}
        await request.app.state.hub.broadcast("arming_update", payload)
        return payload

    @app.get("/api/devices")
    async def devices(request: Request) -> list[dict[str, Any]]:
        return db(request).list_devices()

    @app.get("/api/devices/{device_id}")
    async def device(request: Request, device_id: str) -> dict[str, Any]:
        result = db(request).get_device(device_id)
        if not result:
            raise HTTPException(status_code=404, detail="device_not_found")
        return result

    @app.get("/api/incidents")
    async def incidents(request: Request, limit: int = 100) -> list[dict[str, Any]]:
        return db(request).list_incidents(max(1, min(limit, 250)))

    @app.get("/api/incidents/{incident_id}")
    async def incident(request: Request, incident_id: str) -> dict[str, Any]:
        return get_incident_or_404(request, incident_id)

    @app.get("/api/incidents/{incident_id}/context")
    async def incident_context(request: Request, incident_id: str) -> dict[str, Any]:
        return safe_incident_context(get_incident_or_404(request, incident_id))

    @app.get("/api/incidents/{incident_id}/events")
    async def incident_events(request: Request, incident_id: str) -> list[dict[str, Any]]:
        get_incident_or_404(request, incident_id)
        return db(request).list_events(incident_id)

    @app.get("/api/incidents/{incident_id}/evidence")
    async def evidence(request: Request, incident_id: str) -> dict[str, Any]:
        stored = get_incident_or_404(request, incident_id)
        evidence_path = stored.get("evidence_path")
        if not evidence_path:
            return {"incident_id": incident_id, "available": False, "files": []}
        root = request.app.state.settings.incident_storage_root.resolve()
        candidate = (root / evidence_path).resolve()
        if not candidate.is_relative_to(root):
            raise HTTPException(status_code=400, detail="invalid_evidence_path")
        if not candidate.exists() or not candidate.is_dir():
            return {"incident_id": incident_id, "available": False, "files": []}
        files = [
            {"name": item.name, "size": item.stat().st_size}
            for item in candidate.iterdir()
            if item.is_file() and item.suffix.lower() in {".json", ".jpg", ".jpeg"}
        ]
        return {"incident_id": incident_id, "available": True, "files": files}

    @app.post("/api/incidents/{incident_id}/confirm")
    async def confirm(
        request: Request, incident_id: str, body: ManualConfirmation
    ) -> dict[str, Any]:
        require_rate_limit(request)
        stored = get_incident_or_404(request, incident_id)
        if stored["hazard_state"] not in {"CONFIRMED", "VISUAL_SIGNATURE_LOST"}:
            raise HTTPException(status_code=409, detail="incident_not_visually_confirmed")
        if stored["response_state"] == "CANCELLED":
            raise HTTPException(status_code=409, detail="incident_cancelled")
        request.app.state.timeout_manager.cancel(incident_id)
        updated = db(request).update_incident_response(incident_id, "ESCALATING", "confirmed")
        event = db(request).add_event(
            incident_id,
            "OCCUPANT_CONFIRMED",
            body.source,
            {"note": body.note},
        )
        delivery = await announce_action(
            request,
            updated,
            event,
            PacketType.OCCUPANT_CONFIRM,
            {"incident_id": incident_id, "source": body.source},
        )
        return {"incident": updated, "device_delivery": delivery, "applied_by_backend": True}

    @app.post("/api/incidents/{incident_id}/cancel")
    async def cancel(request: Request, incident_id: str, body: Cancellation) -> dict[str, Any]:
        require_rate_limit(request)
        stored = get_incident_or_404(request, incident_id)
        if stored["response_state"] in {"CALL_CONNECTED", "CALL_COMPLETED"}:
            raise HTTPException(status_code=409, detail="communication_already_connected")
        request.app.state.timeout_manager.cancel(incident_id)
        updated = db(request).update_incident_response(incident_id, "CANCELLED", body.reason)
        event = db(request).add_event(
            incident_id,
            "ESCALATION_CANCELLED",
            body.source,
            {"reason": body.reason, "note": body.note},
        )
        delivery = await announce_action(
            request,
            updated,
            event,
            PacketType.OCCUPANT_CANCEL,
            {"incident_id": incident_id, "reason": body.reason, "source": body.source},
        )
        return {"incident": updated, "device_delivery": delivery, "applied_by_backend": True}

    @app.post("/api/incidents/{incident_id}/reset")
    async def reset(request: Request, incident_id: str, body: ResetRequest) -> dict[str, Any]:
        require_rate_limit(request)
        stored = get_incident_or_404(request, incident_id)
        if stored["response_state"] not in {"CANCELLED", "CALL_COMPLETED", "CALL_FAILED"}:
            raise HTTPException(status_code=409, detail="incident_not_ready_for_reset")
        updated = db(request).update_incident_response(
            incident_id, stored["response_state"], stored.get("occupant_response"), "RESOLVED"
        )
        event = db(request).add_event(
            incident_id, "MANUAL_RESET", body.source, {"note": body.note}
        )
        delivery = await announce_action(
            request,
            updated,
            event,
            PacketType.MANUAL_RESET,
            {"incident_id": incident_id, "source": body.source},
        )
        return {"incident": updated, "device_delivery": delivery, "applied_by_backend": True}

    @app.post("/api/incidents/{incident_id}/call-demo-dispatch")
    async def call_demo_dispatch(request: Request, incident_id: str) -> dict[str, Any]:
        require_rate_limit(request)
        if not request.app.state.armed:
            raise HTTPException(status_code=409, detail="system_unarmed")
        get_incident_or_404(request, incident_id)
        result = await request.app.state.communications.request_demo_call(incident_id)
        event = db(request).add_event(
            incident_id, "DEMO_DISPATCH_REQUESTED", "backend", result
        )
        await request.app.state.hub.broadcast("timeline_event", event)
        await request.app.state.hub.broadcast("call_update", result)
        return result

    @app.get("/api/config/zones")
    async def get_zones(request: Request) -> dict[str, Any]:
        return db(request).get_configuration("zones") or {}

    @app.put("/api/config/zones")
    async def put_zones(request: Request, body: ZoneConfiguration) -> dict[str, Any]:
        require_rate_limit(request)
        value = body.model_dump(mode="json")
        value["zones"] = [
            {**zone, "points": [[point["x"], point["y"]] for point in zone["points"]]}
            for zone in value["zones"]
        ]
        try:
            db(request).put_configuration("zones", body.configuration_version, value)
        except DatabaseError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        deliveries = {}
        for device_id in tuple(request.app.state.registry.connections):
            deliveries[device_id] = await request.app.state.registry.send_control(
                device_id, PacketType.CONFIG_UPDATE, {"kind": "zones", "value": value}
            )
        result = {"configuration": value, "device_delivery": deliveries, "acknowledged": False}
        await request.app.state.hub.broadcast("configuration_update", result)
        return result

    @app.get("/api/config/thresholds")
    async def get_thresholds(request: Request) -> dict[str, Any]:
        return db(request).get_configuration("thresholds") or {}

    @app.get("/api/voice/signed-url")
    async def voice_signed_url(request: Request, incident_id: str) -> dict[str, Any]:
        if not request.app.state.armed:
            raise HTTPException(status_code=409, detail="system_unarmed")
        context = safe_incident_context(get_incident_or_404(request, incident_id))
        signed_url = await request.app.state.communications.signed_url()
        return {"signed_url": signed_url, "context": context}

    @app.post("/api/provider/call-status")
    async def provider_call_status(
        request: Request,
        body: ProviderStatus,
        x_ignis_webhook_secret: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if not request.app.state.communications.authenticate_provider_webhook(
            x_ignis_webhook_secret
        ):
            raise HTTPException(status_code=401, detail="invalid_webhook_secret")
        attempt = db(request).find_attempt_for_incident(body.incident_id)
        if not attempt:
            raise HTTPException(status_code=404, detail="call_attempt_not_found")
        status = {"connected": "CONNECTED", "completed": "COMPLETED", "failed": "FAILED"}[
            body.status
        ]
        updated = db(request).update_call_attempt(
            attempt["id"],
            status,
            body.conversation_id,
            body.call_sid,
            body.error_code,
            "Provider reported call failure." if body.status == "failed" else None,
        )
        await request.app.state.hub.broadcast("call_update", updated)
        return {"accepted": True, "status": status}

    @app.get("/api/simulator/status")
    async def simulator_status(request: Request) -> dict[str, Any]:
        if not request.app.state.settings.enable_simulator_endpoints:
            raise HTTPException(status_code=404, detail="not_found")
        return {
            "enabled": True,
            "tcp_port": request.app.state.tcp_server.bound_port,
            "connected_devices": list(request.app.state.registry.connections),
        }

    @app.websocket("/ws/live")
    async def live(websocket: WebSocket) -> None:
        await app.state.hub.connect(websocket)
        try:
            while True:
                message = await websocket.receive_text()
                if message == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            await app.state.hub.disconnect(websocket)
        except Exception:
            await app.state.hub.disconnect(websocket)

    return app


app = create_app()
