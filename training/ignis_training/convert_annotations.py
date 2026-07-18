from __future__ import annotations

from typing import Any


def coco_box_to_yolo(box: list[float], image_width: int, image_height: int) -> list[float]:
    x, y, width, height = box
    if image_width <= 0 or image_height <= 0 or width <= 0 or height <= 0:
        raise ValueError("invalid image dimensions or box")
    return [
        (x + width / 2) / image_width,
        (y + height / 2) / image_height,
        width / image_width,
        height / image_height,
    ]


def convert_coco_annotation(annotation: dict[str, Any], width: int, height: int) -> str:
    class_id = int(annotation["category_id"])
    values = coco_box_to_yolo([float(value) for value in annotation["bbox"]], width, height)
    return f"{class_id} " + " ".join(f"{value:.8f}" for value in values)

