from __future__ import annotations

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
