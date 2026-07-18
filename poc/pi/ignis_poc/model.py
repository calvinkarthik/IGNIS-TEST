from __future__ import annotations

import json
import hashlib
from pathlib import Path
from time import perf_counter
from typing import Any

from .core import Detection


def _interpreter_class():
    try:
        from tflite_runtime.interpreter import Interpreter

        return Interpreter
    except ImportError:
        try:
            import tensorflow as tf

            return tf.lite.Interpreter
        except ImportError as exc:
            try:
                from ai_edge_litert.interpreter import Interpreter

                return Interpreter
            except ImportError:
                raise RuntimeError(
                    "No TensorFlow Lite interpreter is installed for this QNX/ARM image."
                ) from exc


class TFLiteDetector:
    def __init__(self, model_path: Path, manifest_path: Path, threshold: float = 0.45):
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("The POC needs target-compatible OpenCV and NumPy packages.") from exc
        self.cv2 = cv2
        self.np = np
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_hash = str(self.manifest.get("model_sha256", "")).lower()
        if expected_hash and expected_hash != "replace-at-export":
            actual_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                raise RuntimeError(
                    "model SHA-256 does not match the manifest; refusing to run mismatched weights"
                )
        self.threshold = threshold
        interpreter_type = _interpreter_class()
        self.interpreter = interpreter_type(model_path=str(model_path), num_threads=2)
        self.interpreter.allocate_tensors()
        self.input_detail = self.interpreter.get_input_details()[0]
        self.outputs = self.interpreter.get_output_details()
        self._validate_contract()

    def _validate_contract(self) -> None:
        expected = self.manifest["input"]
        labels = {str(value).lower() for value in self.manifest["labels"].values()}
        ignored_labels = {
            str(value).lower() for value in self.manifest.get("ignored_labels", [])
        }
        if not {"fire", "smoke"}.issubset(labels):
            raise RuntimeError("model manifest labels must contain fire and smoke")
        if labels - {"fire", "smoke"} != ignored_labels:
            raise RuntimeError(
                "every non-hazard model label must be declared in ignored_labels"
            )
        shape = [int(value) for value in self.input_detail["shape"]]
        wanted = [1, int(expected["height"]), int(expected["width"]), int(expected["channels"])]
        if shape != wanted:
            raise RuntimeError(f"model input shape {shape} does not match manifest {wanted}")
        actual_dtype = self.np.dtype(self.input_detail["dtype"]).name
        if actual_dtype != str(expected["dtype"]):
            raise RuntimeError(
                f"model input dtype {actual_dtype} does not match manifest {expected['dtype']}"
            )
        output_manifest = self.manifest["outputs"]
        decoder = output_manifest.get("decoder", "ssd")
        keys = (
            ("predictions_index",)
            if decoder == "yolo_v8"
            else ("boxes_index", "classes_index", "scores_index", "count_index")
        )
        if decoder not in {"ssd", "yolo_v8"}:
            raise RuntimeError(f"unsupported model decoder: {decoder}")
        for key in keys:
            index = int(output_manifest[key])
            if index < 0 or index >= len(self.outputs):
                raise RuntimeError(f"manifest {key}={index} is outside the model outputs")

    def detect(self, bgr_frame: Any) -> tuple[list[Detection], float]:
        np = self.np
        cv2 = self.cv2
        started = perf_counter()
        expected = self.manifest["input"]
        resized = cv2.resize(bgr_frame, (int(expected["width"]), int(expected["height"])))
        image = (
            cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            if expected["color_order"] == "RGB"
            else resized
        )
        tensor = self._prepare_input_tensor(image, expected)
        self.interpreter.set_tensor(self.input_detail["index"], np.expand_dims(tensor, axis=0))
        self.interpreter.invoke()
        contract = self.manifest["outputs"]

        def output(position: str):
            detail = self.outputs[int(contract[position])]
            value = self.interpreter.get_tensor(detail["index"])
            scale, zero = detail.get("quantization", (0.0, 0))
            if scale:
                value = (value.astype(np.float32) - zero) * scale
            return np.squeeze(value)

        labels = {int(key): value for key, value in self.manifest["labels"].items()}
        if contract.get("decoder", "ssd") == "yolo_v8":
            detections = self._decode_yolo_v8(
                output("predictions_index"), labels, int(expected["width"]), int(expected["height"])
            )
            return detections, (perf_counter() - started) * 1000

        boxes = np.atleast_2d(output("boxes_index"))
        classes = np.atleast_1d(output("classes_index"))
        scores = np.atleast_1d(output("scores_index"))
        count = int(np.atleast_1d(output("count_index"))[0])
        zero_based = bool(contract.get("classes_are_zero_based", True))
        detections: list[Detection] = []
        for index in range(min(count, len(scores), len(classes), len(boxes))):
            confidence = float(scores[index])
            raw_class_id = int(round(float(classes[index])))
            class_id = raw_class_id if zero_based else raw_class_id - 1
            class_name = labels.get(class_id, f"class_{class_id}")
            if confidence < self.threshold or class_name not in {"fire", "smoke"}:
                continue
            y_min, x_min, y_max, x_max = [float(value) for value in boxes[index]]
            coordinates = tuple(max(0.0, min(1.0, value)) for value in (x_min, y_min, x_max, y_max))
            if coordinates[0] >= coordinates[2] or coordinates[1] >= coordinates[3]:
                continue
            detections.append(Detection(class_name, class_id, confidence, coordinates))
        return detections, (perf_counter() - started) * 1000

    def _prepare_input_tensor(self, image: Any, expected: dict[str, Any]):
        np = self.np
        normalization = expected.get("normalization", {})
        normalization_type = normalization.get("type")
        pixels = image.astype(np.float32)
        if normalization_type == "zero_to_one":
            real_values = pixels / 255.0
        elif normalization_type == "minus_one_to_one":
            real_values = (pixels - 127.5) / 127.5
        elif normalization_type == "none":
            real_values = pixels
        else:
            raise RuntimeError(
                "manifest normalization.type must be zero_to_one, minus_one_to_one, or none"
            )

        dtype = self.input_detail["dtype"]
        if np.issubdtype(dtype, np.floating):
            return real_values.astype(dtype)
        if not np.issubdtype(dtype, np.integer):
            raise RuntimeError(f"unsupported input tensor dtype: {dtype}")
        scale, zero = self.input_detail.get("quantization", (0.0, 0))
        if not scale:
            raise RuntimeError("quantized input tensor has no quantization scale")
        limits = np.iinfo(dtype)
        return np.clip(np.rint(real_values / scale + zero), limits.min, limits.max).astype(dtype)

    def _decode_yolo_v8(
        self,
        raw: Any,
        labels: dict[int, str],
        input_width: int,
        input_height: int,
    ) -> list[Detection]:
        """Decode Ultralytics YOLOv8 TFLite output and apply class-aware NMS."""
        np = self.np
        predictions = np.squeeze(raw)
        if predictions.ndim != 2:
            raise RuntimeError(f"YOLO output must be rank 2 after squeeze, got {predictions.shape}")
        columns = 4 + len(labels)
        if predictions.shape[0] == columns:
            predictions = predictions.T
        elif predictions.shape[1] != columns:
            raise RuntimeError(
                f"YOLO output {predictions.shape} does not match 4 box values + {len(labels)} labels"
            )
        class_scores = predictions[:, 4:]
        class_ids = np.argmax(class_scores, axis=1)
        scores = class_scores[np.arange(len(predictions)), class_ids]
        candidates: list[Detection] = []
        coordinates_are_pixels = bool(
            self.manifest["outputs"].get("coordinates_are_input_pixels", True)
        )
        for row, class_id, score in zip(predictions, class_ids, scores, strict=True):
            confidence = float(score)
            class_index = int(class_id)
            class_name = labels.get(class_index, f"class_{class_index}")
            if confidence < self.threshold or class_name not in {"fire", "smoke"}:
                continue
            center_x, center_y, box_width, box_height = [float(value) for value in row[:4]]
            if coordinates_are_pixels:
                center_x /= input_width
                box_width /= input_width
                center_y /= input_height
                box_height /= input_height
            coordinates = (
                max(0.0, center_x - box_width / 2),
                max(0.0, center_y - box_height / 2),
                min(1.0, center_x + box_width / 2),
                min(1.0, center_y + box_height / 2),
            )
            if coordinates[0] >= coordinates[2] or coordinates[1] >= coordinates[3]:
                continue
            candidates.append(
                Detection(class_name, class_index, confidence, coordinates)
            )
        return self._class_aware_nms(candidates, iou_threshold=0.45)

    @staticmethod
    def _iou(left: Detection, right: Detection) -> float:
        lx1, ly1, lx2, ly2 = left.bbox
        rx1, ry1, rx2, ry2 = right.bbox
        width = max(0.0, min(lx2, rx2) - max(lx1, rx1))
        height = max(0.0, min(ly2, ry2) - max(ly1, ry1))
        intersection = width * height
        left_area = (lx2 - lx1) * (ly2 - ly1)
        right_area = (rx2 - rx1) * (ry2 - ry1)
        union = left_area + right_area - intersection
        return intersection / union if union > 0 else 0.0

    def _class_aware_nms(
        self, candidates: list[Detection], iou_threshold: float
    ) -> list[Detection]:
        selected: list[Detection] = []
        for candidate in sorted(candidates, key=lambda item: item.confidence, reverse=True):
            if all(
                candidate.class_id != kept.class_id
                or self._iou(candidate, kept) <= iou_threshold
                for kept in selected
            ):
                selected.append(candidate)
        return selected
