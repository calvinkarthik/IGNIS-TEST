from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Any


class LocalLcd:
    """Own the local LCD and flash red for locally confirmed incidents."""

    def __init__(
        self,
        cv2: Any,
        width: int = 480,
        height: int = 320,
        flash_seconds: float = 0.75,
    ):
        self.cv2 = cv2
        self.width = width
        self.height = height
        self.flash_seconds = max(0.25, flash_seconds)
        self.enabled = False
        self.process: subprocess.Popen[bytes] | None = None
        self.worker: threading.Thread | None = None
        self.condition = threading.Condition()
        self.alert = False
        self.stopping = False
        self.logo = self.render_logo()
        self.red = self.render_alert()
        try:
            helper = Path(__file__).resolve().parents[1] / "qnx_lcd_display"
            if not helper.is_file():
                raise RuntimeError(
                    f"QNX LCD helper is missing: {helper}; "
                    "run sh poc/pi/build-qnx-lcd.sh on the Pi"
                )
            self.process = subprocess.Popen(
                [str(helper), str(width), str(height)], stdin=subprocess.PIPE, bufsize=0
            )
            self._write_frame(self.logo)
            self.enabled = True
            self.worker = threading.Thread(
                target=self._display_loop,
                name="ignis-lcd-alert",
                daemon=True,
            )
            self.worker.start()
        except Exception as exc:
            self._disable(exc)

    def render_logo(self) -> Any:
        np = __import__("numpy")
        canvas = np.full((self.height, self.width, 3), 255, dtype=np.uint8)
        orange = (53, 107, 255)
        ink = (0, 0, 0)
        mark = np.array(
            [[103, 35], [153, 87], [170, 276], [36, 276], [53, 87]],
            dtype=np.int32,
        )
        self.cv2.fillPoly(canvas, [mark], orange)
        self.cv2.putText(
            canvas,
            "I",
            (86, 220),
            self.cv2.FONT_HERSHEY_DUPLEX,
            2.9,
            ink,
            6,
            self.cv2.LINE_AA,
        )
        self.cv2.putText(
            canvas,
            "IGNIS",
            (186, 166),
            self.cv2.FONT_HERSHEY_DUPLEX,
            2.0,
            ink,
            4,
            self.cv2.LINE_AA,
        )
        self.cv2.putText(
            canvas,
            "VISUAL INCIDENT INTELLIGENCE",
            (188, 207),
            self.cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            ink,
            1,
            self.cv2.LINE_AA,
        )
        return canvas

    def render_alert(self) -> Any:
        np = __import__("numpy")
        canvas = np.empty((self.height, self.width, 3), dtype=np.uint8)
        canvas[:] = (0, 0, 255)
        return canvas

    def set_alert(self, confirmed: bool) -> None:
        if not self.enabled:
            return
        with self.condition:
            requested = bool(confirmed)
            if requested == self.alert:
                return
            self.alert = requested
            self.condition.notify_all()

    def _display_loop(self) -> None:
        showing_red = False
        while True:
            with self.condition:
                if self.stopping:
                    return
                alert = self.alert

            try:
                if alert:
                    self._write_frame(self.logo if showing_red else self.red)
                    showing_red = not showing_red
                    with self.condition:
                        self.condition.wait_for(
                            lambda: self.stopping or self.alert != alert,
                            timeout=self.flash_seconds,
                        )
                elif showing_red:
                    self._write_frame(self.logo)
                    showing_red = False
                else:
                    with self.condition:
                        self.condition.wait_for(
                            lambda: self.stopping or self.alert,
                        )
            except Exception as exc:
                self._disable(exc)
                return

    def _write_frame(self, frame: Any) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("QNX LCD helper is not running")
        if self.process.poll() is not None:
            raise RuntimeError(f"QNX LCD helper exited with {self.process.returncode}")
        header = f"IGNISBGR {self.width} {self.height}\n".encode("ascii")
        self.process.stdin.write(header + frame.tobytes())
        self.process.stdin.flush()

    def close(self) -> None:
        with self.condition:
            self.stopping = True
            self.condition.notify_all()
        if self.worker is not None and self.worker is not threading.current_thread():
            self.worker.join(timeout=15)
        self._stop_process()

    def _stop_process(self) -> None:
        if self.process is None:
            return
        try:
            if self.process.stdin is not None:
                self.process.stdin.close()
            self.process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    def _disable(self, exc: Exception) -> None:
        self.enabled = False
        with self.condition:
            self.stopping = True
            self.condition.notify_all()
        self._stop_process()
        print(f"LCD alert disabled ({exc}); inference and laptop streaming continue")
