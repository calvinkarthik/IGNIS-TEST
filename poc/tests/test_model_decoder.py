from __future__ import annotations

import pytest

from ignis_poc.model import TFLiteDetector

np = pytest.importorskip("numpy")


def test_yolov8_decoder_normalizes_boxes_and_suppresses_overlap() -> None:
    detector = TFLiteDetector.__new__(TFLiteDetector)
    detector.np = np
    detector.threshold = 0.45
    detector.manifest = {"outputs": {"coordinates_are_input_pixels": True}}
    raw = np.array(
        [
            [160, 162, 60],
            [160, 162, 60],
            [100, 100, 40],
            [100, 100, 40],
            [0.90, 0.80, 0.05],
            [0.05, 0.10, 0.75],
        ],
        dtype=np.float32,
    )
    detections = detector._decode_yolo_v8(raw, {0: "fire", 1: "smoke"}, 320, 320)
    assert [item.class_name for item in detections] == ["fire", "smoke"]
    assert detections[0].bbox == pytest.approx((0.34375, 0.34375, 0.65625, 0.65625))
    assert all(0 <= value <= 1 for item in detections for value in item.bbox)


def test_yolo_float_input_is_scaled_zero_to_one() -> None:
    detector = TFLiteDetector.__new__(TFLiteDetector)
    detector.np = np
    detector.input_detail = {"dtype": np.float32, "quantization": (0.0, 0)}
    tensor = detector._prepare_input_tensor(
        np.array([[[0, 127, 255]]], dtype=np.uint8),
        {"normalization": {"type": "zero_to_one"}},
    )
    assert tensor[0, 0] == pytest.approx([0.0, 127 / 255, 1.0])


def test_quantized_input_uses_interpreter_scale_and_zero_point() -> None:
    detector = TFLiteDetector.__new__(TFLiteDetector)
    detector.np = np
    detector.input_detail = {
        "dtype": np.int8,
        "quantization": (1 / 255, -128),
    }
    tensor = detector._prepare_input_tensor(
        np.array([[[0, 127, 255]]], dtype=np.uint8),
        {"normalization": {"type": "zero_to_one"}},
    )
    assert tensor[0, 0].tolist() == [-128, -1, 127]
