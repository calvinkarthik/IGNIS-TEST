from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def _tflite_candidates(exported: Path, int8: bool) -> list[Path]:
    candidates = [exported] if exported.suffix == ".tflite" else list(exported.rglob("*.tflite"))
    marker = "int8" if int8 else "float32"
    preferred = [path for path in candidates if marker in path.name.lower()]
    return preferred or candidates


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert licensed two-class YOLOv8 fire/smoke weights for the IGNIS POC"
    )
    parser.add_argument("weights", type=Path, help="licensed .pt weights")
    parser.add_argument("--size", type=int, default=320)
    parser.add_argument("--int8", action="store_true")
    parser.add_argument("--data", help="YOLO dataset YAML required for representative INT8 data")
    parser.add_argument(
        "--output", type=Path, default=Path("qnx/models/fire_smoke_detector.tflite")
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("qnx/models/model_manifest.json")
    )
    args = parser.parse_args()
    if args.int8 and not args.data:
        raise SystemExit("--data is required for an INT8 export; use float32 for the first POC")

    try:
        import numpy as np
        import tensorflow as tf
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "Install training/requirements-ml.txt in an isolated laptop environment first."
        ) from exc

    model = YOLO(str(args.weights))
    raw_names = model.names
    names = raw_names if isinstance(raw_names, dict) else dict(enumerate(raw_names))
    labels = {int(index): str(name).strip().lower() for index, name in names.items()}
    if set(labels.values()) != {"fire", "smoke"} or len(labels) != 2:
        raise SystemExit(f"weights must contain exactly fire and smoke classes; found {labels}")

    export_options = {
        "format": "tflite",
        "imgsz": args.size,
        "int8": args.int8,
        "nms": False,
    }
    if args.data:
        export_options["data"] = args.data
    exported = Path(str(model.export(**export_options))).resolve()
    candidates = _tflite_candidates(exported, args.int8)
    if len(candidates) != 1:
        raise SystemExit(f"could not select one TFLite output from: {candidates}")
    source = candidates[0]

    interpreter = tf.lite.Interpreter(model_path=str(source))
    interpreter.allocate_tensors()
    inputs = interpreter.get_input_details()
    outputs = interpreter.get_output_details()
    if len(inputs) != 1 or len(outputs) != 1:
        raise SystemExit(
            f"YOLOv8 POC expects one input and one raw prediction output; got {len(inputs)}/{len(outputs)}"
        )
    shape = [int(value) for value in inputs[0]["shape"]]
    if len(shape) != 4 or shape[0] != 1 or shape[3] != 3:
        raise SystemExit(f"unsupported input tensor shape: {shape}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, args.output)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "model_name": args.weights.stem,
        "model_sha256": digest,
        "input": {
            "index": 0,
            "width": shape[2],
            "height": shape[1],
            "channels": shape[3],
            "layout": "NHWC",
            "dtype": np.dtype(inputs[0]["dtype"]).name,
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
        "labels": {str(index): name for index, name in labels.items()},
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"POC model: {args.output}")
    print(f"Manifest:  {args.manifest}")
    print(f"SHA-256:   {digest}")


if __name__ == "__main__":
    main()
