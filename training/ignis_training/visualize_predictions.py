from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def render_predictions(image_path: Path, predictions: list[dict[str, Any]], output: Path) -> None:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for prediction in predictions:
        box = prediction["bbox"]
        coordinates = [box[0] * width, box[1] * height, box[2] * width, box[3] * height]
        draw.rectangle(coordinates, outline="#ff6b35", width=3)
        draw.text((coordinates[0], coordinates[1]), str(prediction["class_name"]), fill="#ff6b35")
    image.save(output)

