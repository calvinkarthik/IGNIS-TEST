#!/bin/sh
set -eu
ROOT="${IGNIS_ROOT:-/data/home/qnxuser/ignis}"
if [ -f "$ROOT/watchdog.pid" ]; then
  PID=$(cat "$ROOT/watchdog.pid")
  kill -TERM "$PID" 2>/dev/null || true
  rm -f "$ROOT/watchdog.pid"
fi
for service in camera_service inference_service incident_engine stream_service alarm_service; do
  slay "$service" 2>/dev/null || true
done
echo "IGNIS stopped; incident evidence was preserved."

