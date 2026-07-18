from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--every", type=int, default=10)
    args = parser.parse_args()
    try:
        import cv2
    except ImportError as exc:
        raise SystemExit("Install OpenCV for video frame extraction.") from exc
    args.output.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(args.video))
    index = 0
    written = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if index % args.every == 0:
            cv2.imwrite(str(args.output / f"frame-{written:06d}.jpg"), frame)
            written += 1
        index += 1
    capture.release()
    print(f"wrote {written} frames")


if __name__ == "__main__":
    main()

