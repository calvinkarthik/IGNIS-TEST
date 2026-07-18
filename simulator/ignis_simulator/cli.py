from __future__ import annotations

import argparse
import os
import socket
import time
import uuid
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass

from .protocol import HEADER, PacketType, frame_payload, packet
from .render import render_frame
from .scenarios import SCENARIOS, Scenario, Stage, current_stage


@dataclass(slots=True)
class Runtime:
    sequence: int = 1
    frame_sequence: int = 0
    incident_counter: int = 1


class Simulator:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.runtime = Runtime()
        self.boot_id = uuid.uuid4().hex[:8]
        self.incident_id = f"{args.device_id}-{self.boot_id}-1"
        self.connection: socket.socket | None = None
        self.started_ns = time.monotonic_ns()

    def connect(self, invalid_token: bool = False) -> None:
        connection = socket.create_connection((self.args.host, self.args.port), timeout=5)
        connection.settimeout(2)
        self.connection = connection
        hello = {
            "device_id": self.args.device_id,
            "boot_id": self.boot_id,
            "protocol_version": 1,
            "software_version": "simulator-0.1.0",
            "device_token": "invalid-token" if invalid_token else self.args.token,
            "capabilities": [
                "simulated_camera",
                "deterministic_replay",
                "incident_engine",
                "evidence_buffer",
            ],
        }
        self._send(packet(PacketType.HELLO, hello, self._next_sequence(), time.monotonic_ns()))
        if invalid_token:
            with suppress(OSError):
                connection.recv(1024)
            return
        ack = connection.recv(4096)
        if len(ack) < HEADER.size or ack[:4] != b"IGNS" or ack[5] != PacketType.HELLO_ACK:
            raise RuntimeError("backend did not return a valid HELLO_ACK")

    def close(self) -> None:
        if self.connection:
            with suppress(OSError):
                self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            self.connection = None

    def _next_sequence(self) -> int:
        value = self.runtime.sequence
        self.runtime.sequence += 1
        return value

    def _send(self, payload: bytes, fragment: bool | None = None) -> None:
        if self.connection is None:
            raise RuntimeError("simulator is not connected")
        use_fragments = self.args.fault == "fragmented" if fragment is None else fragment
        if not use_fragments:
            self.connection.sendall(payload)
            return
        cursor = 0
        pattern = (1, 3, 7, 13, 31, 127, 521)
        while cursor < len(payload):
            size = pattern[cursor % len(pattern)]
            self.connection.sendall(payload[cursor : cursor + size])
            cursor += size

    def run(self, scenario: Scenario) -> None:
        if self.args.fault == "invalid_token":
            self.connect(invalid_token=True)
            print("Invalid token scenario sent; the backend should reject the connection.")
            return
        self.connect()
        print(
            f"Connected simulator {self.args.device_id} to {self.args.host}:{self.args.port}; "
            f"scenario={scenario.name}, incident={self.incident_id}"
        )
        if self.args.fault == "invalid_length":
            header = HEADER.pack(b"IGNS", 1, PacketType.FRAME, 0, 3_000_000, 2, 1, 0)
            self._send(header, fragment=False)
            print("Oversized payload header sent; the backend should close the connection.")
            return

        start = time.monotonic()
        last_stage: Stage | None = None
        last_health_second = -1
        disconnected = False
        while self.args.loop or time.monotonic() - start < scenario.duration:
            elapsed = (time.monotonic() - start) % scenario.duration
            stage = current_stage(scenario, elapsed)
            self.runtime.frame_sequence += 1
            monotonic_ns = self.started_ns + int(elapsed * 1_000_000_000)

            if self.args.fault == "disconnect_reconnect" and 5 < elapsed < 7 and not disconnected:
                print("Simulating network disconnect; local scenario time continues.")
                self.close()
                disconnected = True
                time.sleep(2)
                self.connect()
                print("Simulator reconnected and is reconciling current state.")
            if elapsed >= 7:
                disconnected = False

            stage_changed = stage is not last_stage
            if stage_changed:
                last_stage = stage

            packets = list(self._frame_packets(scenario, stage, monotonic_ns))
            if self.args.fault == "coalesced":
                self._send(b"".join(packets), fragment=False)
            else:
                for encoded in packets:
                    self._send(encoded)

            second = int(elapsed)
            if second != last_health_second:
                last_health_second = second
                self._send_health(stage, monotonic_ns)

            if stage.hazard != "CLEAR":
                self._send_incident(stage, elapsed, monotonic_ns)
                if stage_changed and stage.event:
                    self._send_timeline(stage, monotonic_ns)

            if self.args.fault == "out_of_order" and self.runtime.frame_sequence == 12:
                old_sequence = max(1, self.runtime.sequence - 5)
                self._send(
                    packet(
                        PacketType.HEALTH_UPDATE,
                        {"status": "out_of_order_test"},
                        old_sequence,
                        monotonic_ns - 2_000_000_000,
                    )
                )

            time.sleep(max(0.01, 1 / self.args.fps))
        print("Scenario complete.")

    def _frame_packets(
        self, scenario: Scenario, stage: Stage, monotonic_ns: int
    ) -> Iterable[bytes]:
        jpeg = render_frame(stage, self.runtime.frame_sequence, scenario.name)
        frame_meta = {
            "device_id": self.args.device_id,
            "frame_sequence": self.runtime.frame_sequence,
            "width": 640,
            "height": 480,
            "jpeg_quality": 78,
            "detections_reference": self.runtime.frame_sequence,
            "source_mode": "LAPTOP_SIMULATOR",
        }
        yield packet(
            PacketType.FRAME,
            frame_payload(frame_meta, jpeg),
            self._next_sequence(),
            monotonic_ns,
        )
        detections = []
        if stage.fire > 0:
            size = stage.area_scale
            detections.append(
                {
                    "class_name": "fire",
                    "class_id": 0,
                    "confidence": stage.fire,
                    "bbox": {
                        "x_min": max(0.08, 0.37 - 0.06 * size),
                        "y_min": max(0.08, 0.68 - 0.22 * size),
                        "x_max": min(0.92, 0.37 + 0.08 * size),
                        "y_max": 0.76,
                    },
                }
            )
        if stage.smoke > 0:
            detections.append(
                {
                    "class_name": "smoke",
                    "class_id": 1,
                    "confidence": stage.smoke,
                    "bbox": {"x_min": 0.27, "y_min": 0.16, "x_max": 0.70, "y_max": 0.58},
                }
            )
        yield packet(
            PacketType.DETECTIONS,
            {
                "frame_sequence": self.runtime.frame_sequence,
                "monotonic_ns": monotonic_ns,
                "inference_duration_ms": 41.5,
                "detections": detections,
            },
            self._next_sequence(),
            monotonic_ns,
        )

    def _send_incident(self, stage: Stage, elapsed: float, monotonic_ns: int) -> None:
        fire_bbox = [0.31, 0.68 - 0.22 * stage.area_scale, 0.45, 0.76]
        payload = {
            "incident_id": self.incident_id,
            "device_id": self.args.device_id,
            "boot_id": self.boot_id,
            "hazard_state": stage.hazard,
            "response_state": stage.response,
            "first_detection_monotonic_ns": self.started_ns + 1_000_000_000,
            "updated_monotonic_ns": monotonic_ns,
            "fire_confidence": stage.fire,
            "smoke_confidence": stage.smoke,
            "seconds_persistent": max(0, elapsed - 1),
            "first_zone": "Stovetop",
            "current_zone": "Stovetop",
            "primary_fire_bbox": fire_bbox if stage.fire else None,
            "primary_smoke_bbox": [0.27, 0.16, 0.70, 0.58] if stage.smoke else None,
            "fire_region_growth_percent": 38.0 if stage.area_scale >= 1.3 else None,
            "smoke_first": True if stage.fire else None,
            "smoke_to_fire_delay_seconds": 1.5 if stage.fire else None,
            "occupant_visible": None,
            "camera_health": stage.camera,
            "inference_health": stage.inference,
        }
        self._send(
            packet(
                PacketType.INCIDENT_UPDATE,
                payload,
                self._next_sequence(),
                monotonic_ns,
            )
        )

    def _send_timeline(self, stage: Stage, monotonic_ns: int) -> None:
        self._send(
            packet(
                PacketType.INCIDENT_TIMELINE_EVENT,
                {
                    "incident_id": self.incident_id,
                    "event_type": stage.event,
                    "hazard_state": stage.hazard,
                    "response_state": stage.response,
                },
                self._next_sequence(),
                monotonic_ns,
            )
        )

    def _send_health(self, stage: Stage, monotonic_ns: int) -> None:
        restarted = stage.inference in {"RESTARTING", "HEALTHY"} and (
            monotonic_ns > self.started_ns + 5_000_000_000
        )
        restart_count = 1 if restarted else 0
        self._send(
            packet(
                PacketType.HEALTH_UPDATE,
                {
                    "status": "HEALTHY"
                    if stage.camera == stage.inference == "HEALTHY"
                    else "DEGRADED",
                    "camera": stage.camera,
                    "inference": stage.inference,
                    "incident_engine": "HEALTHY",
                    "stream": "HEALTHY",
                    "last_frame_age_ms": 12,
                    "last_inference_age_ms": 48 if stage.inference == "HEALTHY" else 1850,
                    "inference_latency_ms": 41.5,
                    "watchdog_restart_count": restart_count,
                    "source_mode": "LAPTOP_SIMULATOR",
                },
                self._next_sequence(),
                monotonic_ns,
            )
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Send deterministic IGNIS packets to FastAPI")
    result.add_argument("--host", default=os.getenv("IGNIS_BACKEND_HOST", "127.0.0.1"))
    result.add_argument("--port", type=int, default=int(os.getenv("QNX_TCP_PORT", "9001")))
    result.add_argument("--token", default=os.getenv("IGNIS_DEVICE_TOKEN", "replace-me"))
    result.add_argument("--device-id", default="ignis-qnxpi-01")
    result.add_argument("--scenario", choices=sorted(SCENARIOS), default="confirmed_fire")
    result.add_argument("--fps", type=float, default=7.0)
    result.add_argument("--loop", action="store_true")
    result.add_argument(
        "--fault",
        choices=(
            "none",
            "fragmented",
            "coalesced",
            "disconnect_reconnect",
            "out_of_order",
            "invalid_length",
            "invalid_token",
        ),
        default="none",
    )
    return result


def main() -> None:
    args = parser().parse_args()
    simulator = Simulator(args)
    try:
        simulator.run(SCENARIOS[args.scenario])
    except KeyboardInterrupt:
        print("Simulator stopped.")
    finally:
        simulator.close()


if __name__ == "__main__":
    main()
