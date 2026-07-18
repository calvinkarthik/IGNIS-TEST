#!/bin/sh
set -u

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${IGNIS_POC_ENV:-"$REPO_ROOT/poc/pi/ignis-poc.env"}
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    . "$ENV_FILE"
fi

MODEL_PATH=${IGNIS_MODEL_PATH:-"$REPO_ROOT/qnx/models/fire_smoke_detector.tflite"}
MANIFEST_PATH=${IGNIS_MODEL_MANIFEST:-"$REPO_ROOT/qnx/models/model_manifest.json"}
CAMERA_SOURCE=${IGNIS_CAMERA_SOURCE:-0}
BACKEND_HOST=${IGNIS_BACKEND_HOST:-192.168.137.1}
BACKEND_PORT=${IGNIS_BACKEND_PORT:-9001}
FAILURES=0

case "$MODEL_PATH" in /*) ;; *) MODEL_PATH="$REPO_ROOT/$MODEL_PATH" ;; esac
case "$MANIFEST_PATH" in /*) ;; *) MANIFEST_PATH="$REPO_ROOT/$MANIFEST_PATH" ;; esac

ok() { printf 'OK      %s\n' "$1"; }
missing() { printf 'MISSING %s\n' "$1"; FAILURES=$((FAILURES + 1)); }
info() { printf 'INFO    %s\n' "$1"; }

printf 'IGNIS POC preflight\n'
uname -a 2>/dev/null || true

if command -v python3 >/dev/null 2>&1; then
    ok "python3: $(python3 --version 2>&1)"
else
    missing "python3 is not available on this QNX image"
fi

if command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import cv2, numpy; print(cv2.__version__)' >/tmp/ignis-cv-version.txt 2>/dev/null; then
        ok "OpenCV + NumPy: $(cat /tmp/ignis-cv-version.txt)"
    else
        missing "target-compatible OpenCV Python bindings and NumPy"
    fi
    if python3 -c 'from tflite_runtime.interpreter import Interpreter' >/dev/null 2>&1; then
        ok "tflite_runtime interpreter"
    elif python3 -c 'from tensorflow.lite import Interpreter' >/dev/null 2>&1; then
        ok "TensorFlow Lite interpreter from TensorFlow"
    else
        missing "QNX/ARM-compatible TensorFlow Lite Python interpreter"
    fi
fi

if [ -f "$MODEL_PATH" ]; then
    ok "model: $MODEL_PATH"
else
    missing "model: $MODEL_PATH"
fi
if [ -f "$MANIFEST_PATH" ]; then
    ok "model manifest: $MANIFEST_PATH"
else
    missing "model manifest: $MANIFEST_PATH"
fi

if command -v python3 >/dev/null 2>&1 \
    && [ -f "$MODEL_PATH" ] \
    && [ -f "$MANIFEST_PATH" ] \
    && python3 -c 'import cv2, numpy' >/dev/null 2>&1; then
    if PYTHONPATH="$REPO_ROOT/poc/pi${PYTHONPATH:+:$PYTHONPATH}" \
        IGNIS_MODEL_PATH="$MODEL_PATH" IGNIS_MODEL_MANIFEST="$MANIFEST_PATH" \
        python3 - <<'PY'
import os
from pathlib import Path

import numpy as np

from ignis_poc.model import TFLiteDetector

detector = TFLiteDetector(
    Path(os.environ["IGNIS_MODEL_PATH"]), Path(os.environ["IGNIS_MODEL_MANIFEST"])
)
height = int(detector.manifest["input"]["height"])
width = int(detector.manifest["input"]["width"])
detections, latency_ms = detector.detect(np.zeros((height, width, 3), dtype=np.uint8))
print(f"inference completed in {latency_ms:.1f} ms ({len(detections)} black-frame detections)")
PY
    then
        ok "model contract, hash, allocation, and one inference"
    else
        missing "model could not be allocated/invoked with its manifest"
    fi
fi

if command -v qcc >/dev/null 2>&1 || command -v q++ >/dev/null 2>&1; then
    ok "QNX compiler is present (not required for the Python POC)"
else
    info "No target compiler found; this is normal for a runtime-only Pi image"
fi

if ls /dev/video* >/dev/null 2>&1; then
    info "Video devices: $(ls /dev/video* 2>/dev/null | tr '\n' ' ')"
else
    info "No /dev/video* nodes; QNX Sensor Framework may expose the camera differently"
fi

if command -v python3 >/dev/null 2>&1 && python3 -c 'import cv2' >/dev/null 2>&1; then
    if IGNIS_CAMERA_SOURCE="$CAMERA_SOURCE" python3 - <<'PY'
import os
import cv2

source = os.environ["IGNIS_CAMERA_SOURCE"]
source = int(source) if source.isdigit() else source
camera = cv2.VideoCapture(source)
opened = camera.isOpened()
ok, frame = camera.read() if opened else (False, None)
camera.release()
raise SystemExit(0 if ok and frame is not None else 1)
PY
    then
        ok "one real camera frame captured from: $CAMERA_SOURCE"
    else
        missing "camera source '$CAMERA_SOURCE' did not produce a frame through OpenCV"
    fi
fi

if command -v python3 >/dev/null 2>&1; then
    if IGNIS_BACKEND_HOST="$BACKEND_HOST" IGNIS_BACKEND_PORT="$BACKEND_PORT" python3 - <<'PY'
import os
import socket

with socket.create_connection(
    (os.environ["IGNIS_BACKEND_HOST"], int(os.environ["IGNIS_BACKEND_PORT"])), timeout=3
):
    pass
PY
    then
        ok "laptop TCP port reachable at $BACKEND_HOST:$BACKEND_PORT"
    else
        missing "laptop TCP port is not reachable at $BACKEND_HOST:$BACKEND_PORT"
    fi
fi

if [ "$FAILURES" -eq 0 ]; then
    printf '\nREADY: all POC prerequisites passed.\n'
    exit 0
fi
printf '\nNOT READY: %s required check(s) failed. See docs/POC_HANDOFF.md.\n' "$FAILURES"
exit 1
