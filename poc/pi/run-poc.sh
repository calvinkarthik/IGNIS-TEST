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

LOCK_DIR=${IGNIS_POC_LOCK_DIR:-/tmp/ignis-poc.lock}
LOCK_PID="$LOCK_DIR/pid"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    OLD_PID=
    if [ -r "$LOCK_PID" ]; then
        OLD_PID=$(cat "$LOCK_PID" 2>/dev/null || true)
    fi
    case "$OLD_PID" in
        ''|*[!0-9]*) OLD_PID= ;;
    esac
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        printf 'IGNIS POC is already running (pid %s).\n' "$OLD_PID" >&2
        exit 0
    fi
    printf 'Removing stale IGNIS POC lock.\n' >&2
    rm -f "$LOCK_PID"
    if ! rmdir "$LOCK_DIR" 2>/dev/null || ! mkdir "$LOCK_DIR" 2>/dev/null; then
        printf 'Unable to acquire IGNIS POC lock: %s\n' "$LOCK_DIR" >&2
        exit 1
    fi
fi
printf '%s\n' "$$" > "$LOCK_PID"

CHILD_PID=
cleanup() {
    STATUS=$?
    trap - 0 1 2 15
    if [ -n "$CHILD_PID" ] && kill -0 "$CHILD_PID" 2>/dev/null; then
        kill -TERM "$CHILD_PID" 2>/dev/null || true
        wait "$CHILD_PID" 2>/dev/null || true
    fi
    rm -f "$LOCK_PID"
    rmdir "$LOCK_DIR" 2>/dev/null || true
    exit "$STATUS"
}
trap cleanup 0 1 2 15

cd "$REPO_ROOT"
PYTHONPATH="$REPO_ROOT/poc/pi${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH

python3 -m ignis_poc.edge \
    --device-id "${IGNIS_DEVICE_ID:-ignis-qnxpi-01}" \
    --backend "${IGNIS_BACKEND_HOST:-192.168.137.1}" \
    --port "${IGNIS_BACKEND_PORT:-9001}" \
    --camera "${IGNIS_CAMERA_SOURCE:-0}" \
    --fps 10 \
    --threshold "${IGNIS_DETECTION_THRESHOLD:-0.25}" \
    --model "${IGNIS_MODEL_PATH:-qnx/models/fire_smoke_detector.tflite}" \
    --manifest "${IGNIS_MODEL_MANIFEST:-qnx/models/model_manifest.json}" \
    --log "${IGNIS_POC_LOG:-poc/pi/data/ignis-poc.jsonl}" &
CHILD_PID=$!
printf '%s\n' "$CHILD_PID" > "$LOCK_PID"
set +e
wait "$CHILD_PID"
STATUS=$?
set -e
CHILD_PID=
exit "$STATUS"
