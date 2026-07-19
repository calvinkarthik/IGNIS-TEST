from __future__ import annotations

import threading
import time

import numpy as np

from ignis_poc.lcd import LocalLcd


class FakeCv2:
    FONT_HERSHEY_DUPLEX = 0
    FONT_HERSHEY_SIMPLEX = 0
    LINE_AA = 0
    text_calls = []

    @staticmethod
    def fillPoly(frame, polygons, color):
        points = polygons[0]
        left, top = points.min(axis=0)
        right, bottom = points.max(axis=0)
        frame[top : bottom + 1, left : right + 1] = color

    @staticmethod
    def putText(text, *args, **kwargs):
        FakeCv2.text_calls.append(text)


def test_logo_is_static_light_brand_screen() -> None:
    lcd = LocalLcd.__new__(LocalLcd)
    lcd.cv2 = FakeCv2()
    lcd.width = 480
    lcd.height = 320

    logo = lcd.render_logo()

    assert logo.shape == (320, 480, 3)
    assert np.array_equal(logo[0, 0], (255, 255, 255))
    assert np.array_equal(logo[120, 103], (53, 107, 255))


def test_confirmed_alert_frame_is_red_with_fire_text() -> None:
    FakeCv2.text_calls.clear()
    lcd = LocalLcd.__new__(LocalLcd)
    lcd.cv2 = FakeCv2()
    lcd.width = 480
    lcd.height = 320

    alert = lcd.render_alert()

    assert alert.shape == (320, 480, 3)
    assert np.all(alert[0, 0] == (0, 0, 255))
    assert FakeCv2.text_calls == ["FIRE"]


def test_alert_worker_alternates_and_returns_to_logo() -> None:
    lcd = LocalLcd.__new__(LocalLcd)
    lcd.enabled = True
    lcd.condition = threading.Condition()
    lcd.alert = False
    lcd.stopping = False
    lcd.flash_seconds = 0.01
    lcd.post_clear_seconds = 0.05
    lcd.logo = np.zeros((1, 1, 3), dtype=np.uint8)
    lcd.red = np.full((1, 1, 3), (0, 0, 255), dtype=np.uint8)
    lcd.off = np.zeros((1, 1, 3), dtype=np.uint8)
    writes = []
    alternated = threading.Event()

    def record(frame) -> None:
        writes.append(frame)
        if len(writes) >= 2:
            alternated.set()

    lcd._write_frame = record
    worker = threading.Thread(target=lcd._display_loop)
    worker.start()

    lcd.set_alert(True)
    assert alternated.wait(timeout=1)
    lcd.set_alert(False)
    deadline = time.monotonic() + 1
    while len(writes) < 4 and time.monotonic() < deadline:
        time.sleep(0.01)

    with lcd.condition:
        lcd.stopping = True
        lcd.condition.notify_all()
    worker.join(timeout=1)

    assert writes[0] is lcd.red
    assert writes[1] is lcd.logo
    assert writes[-1] is lcd.off or writes[-1] is lcd.red
    assert not worker.is_alive()
