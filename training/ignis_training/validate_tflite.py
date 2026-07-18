from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit("Install pinned training/requirements-ml.txt to validate TFLite.") from exc
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    interpreter = tf.lite.Interpreter(model_path=str(args.model))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    expected = [1, manifest["input"]["height"], manifest["input"]["width"], 3]
    if list(input_detail["shape"]) != expected:
        raise SystemExit(f"input shape mismatch: {list(input_detail['shape'])} != {expected}")
    print("TFLite tensor contract validated")


if __name__ == "__main__":
    main()

