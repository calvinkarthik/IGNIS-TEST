from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from .protocol import PacketType, encode_packet


@dataclass(slots=True)
class DeviceConnection:
    device_id: str
    boot_id: str
    writer: asyncio.StreamWriter
    connected_monotonic: float = field(default_factory=time.monotonic)
    outbound_sequence: int = 1

    async def send(self, packet_type: PacketType, payload: dict[str, Any]) -> bool:
        if self.writer.is_closing():
            return False
        self.writer.write(
            encode_packet(
                packet_type,
                payload,
                self.outbound_sequence,
                time.monotonic_ns(),
            )
        )
        self.outbound_sequence += 1
        try:
            await asyncio.wait_for(self.writer.drain(), timeout=1)
            return True
        except (TimeoutError, ConnectionError):
            return False


class DeviceRegistry:
    def __init__(self) -> None:
        self.connections: dict[str, DeviceConnection] = {}
        self.latest_frame: dict[str, Any] | None = None
        self.latest_detections: dict[str, Any] | None = None
        self.latest_health: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def register(self, connection: DeviceConnection) -> None:
        async with self._lock:
            old = self.connections.get(connection.device_id)
            self.connections[connection.device_id] = connection
            if old and old.writer is not connection.writer and not old.writer.is_closing():
                old.writer.close()

    async def unregister(self, device_id: str, writer: asyncio.StreamWriter) -> bool:
        async with self._lock:
            current = self.connections.get(device_id)
            if current is not None and current.writer is writer:
                del self.connections[device_id]
                return True
        return False

    async def send_control(
        self, device_id: str, packet_type: PacketType, payload: dict[str, Any]
    ) -> str:
        connection = self.connections.get(device_id)
        if connection is None:
            return "device_offline"
        delivered = await connection.send(packet_type, payload)
        return "queued_to_device" if delivered else "delivery_failed"

