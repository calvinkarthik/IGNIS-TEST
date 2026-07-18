from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    args = parser.parse_args()
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install pinned training/requirements-ml.txt to export TFLite.") from exc
    YOLO(args.model).export(format="tflite", imgsz=320, int8=True)


if __name__ == "__main__":
    main()

