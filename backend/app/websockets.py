from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket


def envelope(message_type: str, data: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "type": message_type,
        "sent_at": datetime.now(UTC).isoformat(),
        "data": data,
    }


class WebSocketHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self.snapshot_factory: Callable[[], Awaitable[dict[str, Any]]] | None = None

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        snapshot = await self.snapshot_factory() if self.snapshot_factory else {}
        await websocket.send_json(envelope("system_snapshot", snapshot))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, message_type: str, data: Any) -> None:
        serialized = json.dumps(envelope(message_type, data), separators=(",", ":"))
        clients = tuple(self._clients)
        if not clients:
            return

        async def send(client: WebSocket) -> None:
            try:
                await asyncio.wait_for(client.send_text(serialized), timeout=0.35)
            except Exception:
                await self.disconnect(client)

        await asyncio.gather(*(send(client) for client in clients))

