from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from .core import Detection, FireVerifier
from .lcd import LocalLcd
from .model import TFLiteDetector
from .protocol import PacketType, encode_packet, frame_payload, receive_ack


class Camera:
    def __init__(self, source: str, width: int, height: int):
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("OpenCV is not installed for this target image.") from exc
        self.cv2 = cv2
        self.width = width
        self.height = height
        self.qnx_process: subprocess.Popen[bytes] | None = None
        if source.startswith("qnx:"):
            unit = source.partition(":")[2] or "1"
            helper = Path(__file__).resolve().parents[1] / "qnx_camera_capture"
            if not helper.is_file():
                raise RuntimeError(
                    f"QNX camera helper is missing: {helper}. "
                    "Run sh poc/pi/build-qnx-camera.sh on the Pi."
                )
            self.capture = None
            self.qnx_process = subprocess.Popen(
                [str(helper), unit], stdout=subprocess.PIPE, bufsize=0
            )
            return
        parsed_source: str | int = int(source) if source.isdigit() else source
        self.capture = cv2.VideoCapture(parsed_source)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self.capture.isOpened():
            raise RuntimeError(
                "Camera could not be opened. Bind the verified QNX Camera Module 3 source "
                "to OpenCV or pass its working capture pipeline with --camera."
            )

    def read(self):
        if self.qnx_process is not None:
            assert self.qnx_process.stdout is not None
            header = self.qnx_process.stdout.readline()
            if not header:
                code = self.qnx_process.poll()
                raise RuntimeError(f"QNX camera helper stopped unexpectedly (exit={code})")
            fields = header.decode("ascii", errors="replace").strip().split()
            if len(fields) != 3 or fields[0] != "IGNISNV12":
                raise RuntimeError(f"invalid QNX camera frame header: {header!r}")
            width, height = int(fields[1]), int(fields[2])
            expected = width * height * 3 // 2
            raw = bytearray()
            while len(raw) < expected:
                chunk = self.qnx_process.stdout.read(expected - len(raw))
                if not chunk:
                    raise RuntimeError("QNX camera frame ended before all NV12 data arrived")
                raw.extend(chunk)
            import numpy as np

            nv12 = np.frombuffer(raw, dtype=np.uint8).reshape((height * 3 // 2, width))
            frame = self.cv2.cvtColor(nv12, self.cv2.COLOR_YUV2BGR_NV12)
            if (width, height) != (self.width, self.height):
                frame = self.cv2.resize(frame, (self.width, self.height))
            return frame
        ok, frame = self.capture.read()
        if not ok or frame is None:
            raise RuntimeError("camera frame capture failed")
        return frame

    def jpeg(self, frame: Any, quality: int = 75) -> bytes:
        ok, encoded = self.cv2.imencode(".jpg", frame, [self.cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise RuntimeError("JPEG encoding failed")
        return encoded.tobytes()

    def close(self) -> None:
        if self.qnx_process is not None:
            self.qnx_process.terminate()
            try:
                self.qnx_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.qnx_process.kill()
                self.qnx_process.wait()
        elif self.capture is not None:
            self.capture.release()


class BackendStream:
    def __init__(self, host: str, port: int, device_id: str, token: str, boot_id: str):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.token = token
        self.boot_id = boot_id
        self.connection: socket.socket | None = None
        self.sequence = 1
        self.next_reconnect = 0.0
        self.last_error = ""

    def connect(self) -> bool:
        if time.monotonic() < self.next_reconnect:
            return False
        try:
            connection = socket.create_connection((self.host, self.port), timeout=5)
            connection.settimeout(5)
            hello = {
                "device_id": self.device_id,
                "boot_id": self.boot_id,
                "protocol_version": 1,
                "software_version": "poc-0.1.0",
                "device_token": self.token,
                "capabilities": ["poc_camera", "tflite_fire_detection", "jpeg_stream"],
            }
            connection.sendall(self.packet(PacketType.HELLO, hello, time.monotonic_ns()))
            receive_ack(connection)
            connection.settimeout(None)
            self.connection = connection
            self.last_error = ""
            print(f"Laptop stream connected to {self.host}:{self.port}")
            return True
        except (OSError, ConnectionError) as exc:
            self.close()
            self.next_reconnect = time.monotonic() + 2.0
            message = str(exc)
            if message != self.last_error:
                print(f"Laptop stream unavailable ({message}); local inference continues")
                self.last_error = message
            return False

    def packet(self, packet_type: PacketType, payload: bytes | dict, monotonic_ns: int) -> bytes:
        encoded = encode_packet(packet_type, payload, self.sequence, monotonic_ns)
        self.sequence += 1
        return encoded

    def send(self, packet_type: PacketType, payload: bytes | dict, monotonic_ns: int) -> bool:
        if self.connection is None and not self.connect():
            return False
        try:
            assert self.connection is not None
            self.connection.sendall(self.packet(packet_type, payload, monotonic_ns))
            return True
        except OSError as exc:
            self.close()
            self.next_reconnect = time.monotonic() + 2.0
            self.last_error = str(exc)
            print(f"Laptop stream disconnected ({exc}); local inference continues")
            return False

    def close(self) -> None:
        if self.connection:
            self.connection.close()
        self.connection = None


def run(args: argparse.Namespace) -> None:
    token = args.token or os.getenv("IGNIS_DEVICE_TOKEN", "")
    if not token:
        raise SystemExit("Set IGNIS_DEVICE_TOKEN to the same value used by the laptop backend.")
    boot_id = uuid.uuid4().hex[:8]
    camera = Camera(args.camera, args.width, args.height)
    detector = TFLiteDetector(args.model, args.manifest, args.threshold)
    lcd = LocalLcd(camera.cv2, args.lcd_width, args.lcd_height) if args.lcd else None
    verifier = FireVerifier(args.device_id, boot_id)
    stream = BackendStream(args.backend, args.port, args.device_id, token, boot_id)
    frame_sequence = 0
    last_health = 0.0
    last_local_log = 0.0
    last_state = "CLEAR"
    frame_period = 1 / args.fps
    try:
        stream.connect()
        print(f"IGNIS POC running; camera={args.camera}, model={args.model}")
        args.log.parent.mkdir(parents=True, exist_ok=True)
        while True:
            loop_started = time.monotonic()
            monotonic_ns = time.monotonic_ns()
            frame = camera.read()
            detections, inference_ms = detector.detect(frame)
            state = verifier.update(monotonic_ns, detections)
            frame_sequence += 1
            jpeg = camera.jpeg(frame, args.jpeg_quality)
            height, width = frame.shape[:2]
            metadata = {
                "device_id": args.device_id,
                "frame_sequence": frame_sequence,
                "width": int(width),
                "height": int(height),
                "jpeg_quality": args.jpeg_quality,
                "detections_reference": frame_sequence,
                "source_mode": "QNX_POC",
            }
            stream.send(
                PacketType.FRAME,
                frame_payload(metadata, jpeg),
                monotonic_ns,
            )
            stream.send(
                PacketType.DETECTIONS,
                {
                    "frame_sequence": frame_sequence,
                    "monotonic_ns": monotonic_ns,
                    "inference_duration_ms": round(inference_ms, 2),
                    "detections": [item.as_json() for item in detections],
                },
                monotonic_ns,
            )
            if lcd is not None:
                lcd.show(frame, detections)
            if state.incident_id:
                response = "AWAITING_RESPONSE" if state.confirmed else "IDLE"
                stream.send(
                    PacketType.INCIDENT_UPDATE,
                    {
                        "incident_id": state.incident_id,
                        "device_id": args.device_id,
                        "boot_id": boot_id,
                        "hazard_state": state.hazard_state,
                        "response_state": response,
                        "first_detection_monotonic_ns": state.first_detection_ns,
                        "updated_monotonic_ns": monotonic_ns,
                        "fire_confidence": state.fire_confidence,
                        "smoke_confidence": state.smoke_confidence,
                        "seconds_persistent": state.seconds_persistent,
                        "first_zone": "Camera view",
                        "current_zone": "Camera view",
                        "primary_fire_bbox": _primary_box(detections, "fire"),
                        "primary_smoke_bbox": _primary_box(detections, "smoke"),
                        "fire_region_growth_percent": None,
                        "smoke_first": None,
                        "smoke_to_fire_delay_seconds": None,
                        "occupant_visible": None,
                        "camera_health": "HEALTHY",
                        "inference_health": "HEALTHY",
                    },
                    monotonic_ns,
                )
                if state.hazard_state != last_state:
                    event = {
                        "time_unix": time.time(),
                        "monotonic_ns": monotonic_ns,
                        "incident_id": state.incident_id,
                        "hazard_state": state.hazard_state,
                        "fire_confidence": state.fire_confidence,
                        "smoke_confidence": state.smoke_confidence,
                    }
                    _append_local_log(args.log, event)
                    print(
                        f"LOCAL STATE {state.hazard_state}: "
                        f"fire={state.fire_confidence:.3f} smoke={state.smoke_confidence:.3f}"
                    )
                    stream.send(
                        PacketType.INCIDENT_TIMELINE_EVENT,
                        {
                            "incident_id": state.incident_id,
                            "event_type": f"POC_{state.hazard_state}",
                            "hazard_state": state.hazard_state,
                        },
                        monotonic_ns,
                    )
                    last_state = state.hazard_state
            if time.monotonic() - last_health >= 1:
                last_health = time.monotonic()
                stream.send(
                    PacketType.HEALTH_UPDATE,
                    {
                        "status": "HEALTHY",
                        "camera": "HEALTHY",
                        "inference": "HEALTHY",
                        "incident_engine": "POC",
                        "stream": "HEALTHY",
                        "inference_latency_ms": round(inference_ms, 2),
                        "watchdog_restart_count": 0,
                        "source_mode": "QNX_POC",
                    },
                    monotonic_ns,
                )
            if time.monotonic() - last_local_log >= 10:
                last_local_log = time.monotonic()
                _append_local_log(
                    args.log,
                    {
                        "time_unix": time.time(),
                        "monotonic_ns": monotonic_ns,
                        "event": "POC_HEALTH",
                        "camera": "HEALTHY",
                        "inference": "HEALTHY",
                        "inference_latency_ms": round(inference_ms, 2),
                        "laptop_connected": stream.connection is not None,
                    },
                )
            elapsed = time.monotonic() - loop_started
            if elapsed < frame_period:
                time.sleep(frame_period - elapsed)
    except KeyboardInterrupt:
        print("IGNIS POC stopped")
    finally:
        if lcd is not None:
            lcd.close()
        camera.close()
        stream.close()


def _primary_box(detections: list[Detection], class_name: str) -> list[float] | None:
    candidates = [item for item in detections if item.class_name == class_name]
    if not candidates:
        return None
    return list(max(candidates, key=lambda item: item.confidence).bbox)


def _append_local_log(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, separators=(",", ":")) + "\n")
        handle.flush()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="IGNIS QNX Pi camera/inference/stream POC")
    result.add_argument("--backend", default=os.getenv("IGNIS_BACKEND_HOST", "192.168.137.1"))
    result.add_argument("--port", type=int, default=int(os.getenv("IGNIS_BACKEND_PORT", "9001")))
    result.add_argument("--token", default="")
    result.add_argument("--device-id", default="ignis-qnxpi-01")
    result.add_argument("--camera", default=os.getenv("IGNIS_CAMERA_SOURCE", "0"))
    result.add_argument(
        "--model",
        type=Path,
        default=Path(os.getenv("IGNIS_MODEL_PATH", "qnx/models/fire_smoke_detector.tflite")),
    )
    result.add_argument(
        "--manifest",
        type=Path,
        default=Path(os.getenv("IGNIS_MODEL_MANIFEST", "qnx/models/model_manifest.json")),
    )
    result.add_argument(
        "--log",
        type=Path,
        default=Path(os.getenv("IGNIS_POC_LOG", "poc/pi/data/ignis-poc.jsonl")),
    )
    result.add_argument("--width", type=int, default=640)
    result.add_argument("--height", type=int, default=480)
    result.add_argument("--fps", type=float, default=5.0)
    result.add_argument("--threshold", type=float, default=0.45)
    result.add_argument("--jpeg-quality", type=int, default=75)
    result.add_argument(
        "--lcd",
        action="store_true",
        default=os.getenv("IGNIS_LCD_ENABLED", "0").lower() in {"1", "true", "yes", "on"},
        help="show an annotated preview through the Pi's native QNX Screen service",
    )
    result.add_argument("--lcd-width", type=int, default=int(os.getenv("IGNIS_LCD_WIDTH", "320")))
    result.add_argument("--lcd-height", type=int, default=int(os.getenv("IGNIS_LCD_HEIGHT", "480")))
    return result


def main() -> None:
    args = parser().parse_args()
    for path in (args.model, args.manifest):
        if not path.is_file():
            raise SystemExit(f"Required model artifact is missing: {path}")
    run(args)


if __name__ == "__main__":
    main()
