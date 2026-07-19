from __future__ import annotations

import asyncio
import base64
import hmac
import logging
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from pydantic import ValidationError

from .config import Settings
from .database import Database
from .device_registry import DeviceConnection, DeviceRegistry
from .models import IncidentUpdate
from .protocol import (
    Packet,
    PacketParser,
    PacketType,
    ProtocolError,
    decode_frame_payload,
)
from .websockets import WebSocketHub

logger = logging.getLogger(__name__)


class DeviceTcpServer:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        hub: WebSocketHub,
        registry: DeviceRegistry,
    ):
        self.settings = settings
        self.database = database
        self.hub = hub
        self.registry = registry
        self.server: asyncio.AbstractServer | None = None
        self.bound_port: int | None = None
        self.incident_observer: Callable[[str], None] | None = None
        self.arming_state: Callable[[], bool] | None = None

    async def start(self) -> None:
        self.server = await asyncio.start_server(
            self._handle_connection,
            host=self.settings.qnx_tcp_host,
            port=self.settings.qnx_tcp_port,
            limit=self.settings.max_payload_bytes + 4096,
        )
        sockets = self.server.sockets or []
        self.bound_port = sockets[0].getsockname()[1] if sockets else None
        logger.info("device TCP receiver listening on port %s", self.bound_port)

    async def close(self) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        parser = PacketParser(self.settings.max_payload_bytes)
        hello: dict[str, Any] | None = None
        last_sequence = -1
        peer = writer.get_extra_info("peername")
        try:
            while True:
                chunk = await reader.read(65_536)
                if not chunk:
                    break
                for packet in parser.feed(chunk):
                    if packet.sequence <= last_sequence:
                        await self.hub.broadcast(
                            "error",
                            {
                                "code": "OUT_OF_ORDER_SEQUENCE",
                                "sequence": packet.sequence,
                                "last_sequence": last_sequence,
                            },
                        )
                        continue
                    last_sequence = packet.sequence
                    if hello is None:
                        if packet.packet_type != PacketType.HELLO:
                            raise ProtocolError("HELLO must be the first packet")
                        hello = await self._authenticate(packet, writer)
                        continue
                    await self._dispatch(hello, packet)
        except (ProtocolError, ValidationError, KeyError, ValueError) as exc:
            logger.warning("device protocol connection rejected: %s", exc)
            await self.hub.broadcast(
                "error", {"code": "DEVICE_PROTOCOL_ERROR", "message": str(exc)[:160]}
            )
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        except Exception:
            logger.exception("unexpected device connection error from %s", peer)
        finally:
            if hello is not None:
                was_current = await self.registry.unregister(hello["device_id"], writer)
                if was_current:
                    self.database.mark_device_disconnected(hello["device_id"], hello["boot_id"])
                    await self.hub.broadcast(
                        "health_update",
                        {"device_id": hello["device_id"], "qnx_connected": False},
                    )
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()

    async def _authenticate(
        self, packet: Packet, writer: asyncio.StreamWriter
    ) -> dict[str, Any]:
        hello = packet.json()
        required = {"device_id", "boot_id", "protocol_version", "software_version", "device_token"}
        if not required.issubset(hello):
            raise ProtocolError("HELLO missing required fields")
        if hello["protocol_version"] != 1:
            raise ProtocolError("HELLO protocol version mismatch")
        if hello["device_id"] != self.settings.expected_device_id:
            raise ProtocolError("unknown device")
        supplied = str(hello["device_token"])
        if not hmac.compare_digest(supplied, self.settings.device_token):
            raise ProtocolError("authentication failed")
        hello.pop("device_token", None)
        connection = DeviceConnection(hello["device_id"], hello["boot_id"], writer)
        await self.registry.register(connection)
        self.database.upsert_device(hello)
        await connection.send(
            PacketType.HELLO_ACK,
            {
                "accepted": True,
                "protocol_version": 1,
                "zone_configuration_version": 1,
                "threshold_configuration_version": 1,
            },
        )
        await self.hub.broadcast(
            "health_update", {"device_id": hello["device_id"], "qnx_connected": True}
        )
        return hello

    async def _dispatch(self, hello: dict[str, Any], packet: Packet) -> None:
        device_id = hello["device_id"]
        if packet.packet_type == PacketType.FRAME:
            metadata, jpeg = decode_frame_payload(packet.payload)
            frame = {
                **metadata,
                "monotonic_ns": packet.monotonic_ns,
                "sequence": packet.sequence,
                "jpeg_base64": base64.b64encode(jpeg).decode("ascii"),
            }
            self.registry.latest_frame = frame
            await self.hub.broadcast("frame", frame)
            return
        data = packet.json()
        if packet.packet_type == PacketType.DETECTIONS:
            self.registry.latest_detections = data
            await self.hub.broadcast("detections", data)
        elif packet.packet_type == PacketType.INCIDENT_UPDATE:
            if self.arming_state is not None and not self.arming_state():
                return
            incident = IncidentUpdate.model_validate(data).model_dump(mode="json")
            self.database.upsert_incident(incident, device_id, hello["boot_id"])
            stored = self.database.get_incident(incident["incident_id"])
            await self.hub.broadcast("incident_update", stored)
            if self.incident_observer is not None:
                self.incident_observer(incident["incident_id"])
        elif packet.packet_type == PacketType.INCIDENT_TIMELINE_EVENT:
            incident_id = str(data["incident_id"])
            if self.database.get_incident(incident_id) is None:
                raise ProtocolError("timeline event references unknown incident")
            event = self.database.add_event(
                incident_id,
                str(data.get("event_type", "DEVICE_EVENT")),
                "qnx",
                data,
                packet.monotonic_ns,
                data.get("wall_time_utc"),
            )
            await self.hub.broadcast("timeline_event", event)
        elif packet.packet_type == PacketType.HEALTH_UPDATE:
            health = {**data, "device_id": device_id, "qnx_connected": True}
            self.registry.latest_health = health
            self.database.update_health(device_id, health)
            await self.hub.broadcast("health_update", health)
        elif packet.packet_type == PacketType.CONFIG_ACK:
            await self.hub.broadcast("configuration_update", data)
        elif packet.packet_type == PacketType.PING:
            connection = self.registry.connections.get(device_id)
            if connection:
                await connection.send(PacketType.PONG, {"ping_sequence": packet.sequence})
        elif packet.packet_type in {PacketType.EVIDENCE_MANIFEST, PacketType.LOG_EVENT}:
            await self.hub.broadcast(
                "timeline_event",
                {"source": "qnx", "packet_type": packet.packet_type.name, "payload": data},
            )
        else:
            raise ProtocolError(f"unexpected device packet type {packet.packet_type.name}")
