from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class LocalLcd:
    """Write one static IGNIS logo to the local LCD at startup."""

    def __init__(self, cv2: Any, width: int = 480, height: int = 320):
        self.cv2 = cv2
        self.width = width
        self.height = height
        try:
            helper = Path(__file__).resolve().parents[1] / "qnx_lcd_display"
            if not helper.is_file():
                raise RuntimeError(
                    f"QNX LCD helper is missing: {helper}; "
                    "run sh poc/pi/build-qnx-lcd.sh on the Pi"
                )
            canvas = self.render_logo()
            header = f"IGNISBGR {width} {height}\n".encode("ascii")
            subprocess.run(
                [str(helper), str(width), str(height)],
                input=header + canvas.tobytes(),
                check=True,
                timeout=15,
            )
        except Exception as exc:
            print(f"LCD logo disabled ({exc}); inference and laptop streaming continue")

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

    def close(self) -> None:
        pass
