from __future__ import annotations

import numpy as np
from queue import Queue

from ignis_poc.core import Detection
from ignis_poc.lcd import LocalLcd


class FakeCv2:
    FONT_HERSHEY_SIMPLEX = 0
    LINE_AA = 0

    @staticmethod
    def resize(frame, size):
        width, height = size
        return np.full((height, width, 3), frame[0, 0], dtype=np.uint8)

    @staticmethod
    def rectangle(frame, top_left, bottom_right, color, thickness):
        del thickness
        left, top = top_left
        right, bottom = bottom_right
        frame[top, left : right + 1] = color
        frame[bottom, left : right + 1] = color
        frame[top : bottom + 1, left] = color
        frame[top : bottom + 1, right] = color

    @staticmethod
    def putText(*args, **kwargs):
        del args, kwargs


def test_render_letterboxes_landscape_frame_and_draws_detection() -> None:
    lcd = LocalLcd.__new__(LocalLcd)
    lcd.cv2 = FakeCv2()
    lcd.width = 320
    lcd.height = 480
    frame = np.full((480, 640, 3), 40, dtype=np.uint8)
    detection = Detection("fire", 0, 0.9, (0.25, 0.25, 0.75, 0.75))

    rendered = lcd.render(frame, [detection])

    assert rendered.shape == (480, 320, 3)
    assert np.all(rendered[:119] == 0)
    assert np.any(rendered[120:360] != 40)
    assert np.all(rendered[361:] == 0)


def test_slow_lcd_keeps_only_latest_frame_without_blocking() -> None:
    lcd = LocalLcd.__new__(LocalLcd)
    lcd.enabled = True
    lcd.frames = Queue(maxsize=1)
    first = np.zeros((2, 2, 3), dtype=np.uint8)
    latest = np.ones((2, 2, 3), dtype=np.uint8)

    lcd.show(first, [])
    lcd.show(latest, [])

    queued, detections = lcd.frames.get_nowait()
    assert np.array_equal(queued, latest)
    assert detections == []
