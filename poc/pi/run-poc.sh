#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${IGNIS_POC_ENV:-"$REPO_ROOT/poc/pi/ignis-poc.env"}
if [ ! -f "$ENV_FILE" ]; then
    printf 'Missing %s\nCopy ignis-poc.env.example to ignis-poc.env and edit it first.\n' "$ENV_FILE" >&2
    exit 1
fi
# shellcheck disable=SC1090
. "$ENV_FILE"

: "${IGNIS_DEVICE_TOKEN:?IGNIS_DEVICE_TOKEN must be set in ignis-poc.env}"
if [ "$IGNIS_DEVICE_TOKEN" = "replace-this-poc-token" ]; then
    printf 'Replace the example device token on both the laptop and Pi before running.\n' >&2
    exit 1
fi

cd "$REPO_ROOT"
PYTHONPATH="$REPO_ROOT/poc/pi${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH

exec python3 -m ignis_poc.edge \
    --device-id "${IGNIS_DEVICE_ID:-ignis-qnxpi-01}" \
    --backend "${IGNIS_BACKEND_HOST:-192.168.137.1}" \
    --port "${IGNIS_BACKEND_PORT:-9001}" \
    --camera "${IGNIS_CAMERA_SOURCE:-0}" \
    --model "${IGNIS_MODEL_PATH:-qnx/models/fire_smoke_detector.tflite}" \
    --manifest "${IGNIS_MODEL_MANIFEST:-qnx/models/model_manifest.json}" \
    --log "${IGNIS_POC_LOG:-poc/pi/data/ignis-poc.jsonl}"
