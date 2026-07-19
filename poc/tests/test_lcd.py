from __future__ import annotations

import threading
import time

import numpy as np

from ignis_poc.lcd import LocalLcd


class FakeCv2:
    FONT_HERSHEY_DUPLEX = 0
    FONT_HERSHEY_SIMPLEX = 0
    LINE_AA = 0

    @staticmethod
    def fillPoly(frame, polygons, color):
        points = polygons[0]
        left, top = points.min(axis=0)
        right, bottom = points.max(axis=0)
        frame[top : bottom + 1, left : right + 1] = color

    @staticmethod
    def putText(*args, **kwargs):
        del args, kwargs


def test_logo_is_static_light_brand_screen() -> None:
    lcd = LocalLcd.__new__(LocalLcd)
    lcd.cv2 = FakeCv2()
    lcd.width = 480
    lcd.height = 320

    logo = lcd.render_logo()

    assert logo.shape == (320, 480, 3)
    assert np.array_equal(logo[0, 0], (255, 255, 255))
    assert np.array_equal(logo[120, 103], (53, 107, 255))


def test_confirmed_alert_frame_is_solid_red() -> None:
    lcd = LocalLcd.__new__(LocalLcd)
    lcd.width = 480
    lcd.height = 320

    alert = lcd.render_alert()

    assert alert.shape == (320, 480, 3)
    assert np.all(alert == (0, 0, 255))


def test_off_frame_is_solid_black() -> None:
    lcd = LocalLcd.__new__(LocalLcd)
    lcd.width = 480
    lcd.height = 320

    off = lcd.render_off()

    assert off.shape == (320, 480, 3)
    assert np.all(off == (0, 0, 0))


def test_alert_worker_flashes_off_and_red_then_returns_to_logo() -> None:
    lcd = LocalLcd.__new__(LocalLcd)
    lcd.enabled = True
    lcd.condition = threading.Condition()
    lcd.alert = False
    lcd.stopping = False
    lcd.flash_seconds = 0.01
    lcd.logo = np.zeros((1, 1, 3), dtype=np.uint8)
    lcd.red = np.full((1, 1, 3), (0, 0, 255), dtype=np.uint8)
    lcd.off = np.full((1, 1, 3), (1, 1, 1), dtype=np.uint8)
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
    while writes[-1] is not lcd.logo and time.monotonic() < deadline:
        time.sleep(0.01)

    with lcd.condition:
        lcd.stopping = True
        lcd.condition.notify_all()
    worker.join(timeout=1)

    assert writes[0] is lcd.off
    assert writes[1] is lcd.red
    assert writes[-1] is lcd.logo
    assert not worker.is_alive()
