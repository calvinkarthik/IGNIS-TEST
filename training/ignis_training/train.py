from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_yaml")
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=80)
    args = parser.parse_args()
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install pinned training/requirements-ml.txt to train the detector.") from exc
    YOLO(args.model).train(data=args.dataset_yaml, epochs=args.epochs, imgsz=320)


if __name__ == "__main__":
    main()

