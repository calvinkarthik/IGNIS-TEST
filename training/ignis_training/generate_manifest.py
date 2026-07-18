from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def generate_manifest(model_path: Path, width: int = 320, height: int = 320) -> dict[str, Any]:
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    return {
        "schema_version": 1,
        "model_name": "ignis_fire_smoke_detector",
        "model_sha256": digest,
        "input": {
            "index": 0,
            "width": width,
            "height": height,
            "channels": 3,
            "layout": "NHWC",
            "dtype": "uint8",
            "color_order": "RGB",
            "normalization": {"type": "zero_to_one"},
        },
        "outputs": {
            "decoder": "yolo_v8",
            "predictions_index": 0,
            "box_order": "center_x_center_y_width_height",
            "coordinates_are_input_pixels": True,
            "classes_are_zero_based": True,
        },
        "labels": {"0": "fire", "1": "smoke"},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(generate_manifest(args.model), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
