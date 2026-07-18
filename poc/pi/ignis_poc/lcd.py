from __future__ import annotations

import subprocess
import threading
from queue import Empty, Full, Queue
from pathlib import Path
from typing import Any

from .core import Detection


class LocalLcd:
    """Best-effort 320x480 annotated preview on the target's default display."""

    def __init__(self, cv2: Any, width: int = 320, height: int = 480):
        self.cv2 = cv2
        self.width = width
        self.height = height
        self.enabled = True
        self.process: subprocess.Popen[bytes] | None = None
        self.frames: Queue[tuple[Any, list[Detection]]] = Queue(maxsize=1)
        self.stopping = threading.Event()
        self.worker: threading.Thread | None = None
        try:
            helper = Path(__file__).resolve().parents[1] / "qnx_lcd_display"
            if not helper.is_file():
                raise RuntimeError(
                    f"QNX Screen helper is missing: {helper}; "
                    "run sh poc/pi/build-qnx-lcd.sh on the Pi"
                )
            self.process = subprocess.Popen(
                [str(helper), str(width), str(height)], stdin=subprocess.PIPE, bufsize=0
            )
            self.worker = threading.Thread(
                target=self._display_loop, name="ignis-lcd", daemon=True
            )
            self.worker.start()
        except Exception as exc:
            self._disable(exc)

    def render(self, frame: Any, detections: list[Detection]) -> Any:
        """Return a portrait canvas with a fitted frame and aligned detection boxes."""
        np = __import__("numpy")
        source_height, source_width = frame.shape[:2]
        scale = min(self.width / source_width, self.height / source_height)
        draw_width = max(1, int(round(source_width * scale)))
        draw_height = max(1, int(round(source_height * scale)))
        offset_x = (self.width - draw_width) // 2
        offset_y = (self.height - draw_height) // 2
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        canvas[offset_y : offset_y + draw_height, offset_x : offset_x + draw_width] = (
            self.cv2.resize(frame, (draw_width, draw_height))
        )

        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            left = offset_x + int(round(x1 * draw_width))
            top = offset_y + int(round(y1 * draw_height))
            right = offset_x + int(round(x2 * draw_width))
            bottom = offset_y + int(round(y2 * draw_height))
            color = (0, 0, 255) if detection.class_name == "fire" else (0, 165, 255)
            self.cv2.rectangle(canvas, (left, top), (right, bottom), color, 2)
            label = f"{detection.class_name.upper()} {detection.confidence:.0%}"
            label_y = max(18, top - 5)
            self.cv2.putText(
                canvas,
                label,
                (left, label_y),
                self.cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                self.cv2.LINE_AA,
            )
        return canvas

    def show(self, frame: Any, detections: list[Detection]) -> None:
        if not self.enabled:
            return
        try:
            self.frames.put_nowait((frame.copy(), list(detections)))
        except Full:
            try:
                self.frames.get_nowait()
            except Empty:
                pass
            try:
                self.frames.put_nowait((frame.copy(), list(detections)))
            except Full:
                pass

    def _display_loop(self) -> None:
        while not self.stopping.is_set():
            try:
                frame, detections = self.frames.get(timeout=0.1)
            except Empty:
                continue
            try:
                assert self.process is not None and self.process.stdin is not None
                canvas = self.render(frame, detections)
                rgba = self.cv2.cvtColor(canvas, self.cv2.COLOR_BGR2RGBA)
                self.process.stdin.write(
                    f"IGNISRGBA {self.width} {self.height}\n".encode("ascii")
                )
                self.process.stdin.write(rgba.tobytes())
                self.process.stdin.flush()
            except Exception as exc:
                self._disable(exc)
                return

    def close(self) -> None:
        if self.process is None:
            return
        self.stopping.set()
        try:
            self.process.terminate()
            self.process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            self.process.kill()
        if self.worker is not None:
            self.worker.join(timeout=2)

    def _disable(self, exc: Exception) -> None:
        self.enabled = False
        print(f"LCD preview disabled ({exc}); inference and laptop streaming continue")
