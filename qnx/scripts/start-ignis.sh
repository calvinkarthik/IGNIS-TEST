#!/bin/sh
set -eu

ROOT="${IGNIS_ROOT:-/data/home/qnxuser/ignis}"
ENV_FILE="$ROOT/config/device.env"
[ -f "$ENV_FILE" ] || {
  echo "Missing $ENV_FILE. It must export IGNIS_DEVICE_TOKEN and IGNIS_BACKEND_HOST." >&2
  exit 78
}
. "$ENV_FILE"
: "${IGNIS_DEVICE_TOKEN:?IGNIS_DEVICE_TOKEN is required}"
: "${IGNIS_BACKEND_HOST:?IGNIS_BACKEND_HOST is required}"
export IGNIS_DEVICE_TOKEN IGNIS_BACKEND_HOST
export IGNIS_BACKEND_PORT="${IGNIS_BACKEND_PORT:-9001}"
export IGNIS_DEVICE_ID="${IGNIS_DEVICE_ID:-ignis-qnxpi-01}"
export IGNIS_CAMERA_MODE="${IGNIS_CAMERA_MODE:-qnx}"

mkdir -p "$ROOT/logs" "$ROOT/data/incidents"
if [ -f "$ROOT/watchdog.pid" ] && kill -0 "$(cat "$ROOT/watchdog.pid")" 2>/dev/null; then
  echo "IGNIS watchdog is already running"
  exit 0
fi
nohup "$ROOT/bin/watchdog_service" "$ROOT/bin" >>"$ROOT/logs/watchdog.log" 2>&1 &
echo $! >"$ROOT/watchdog.pid"
echo "IGNIS started with watchdog PID $(cat "$ROOT/watchdog.pid")"

