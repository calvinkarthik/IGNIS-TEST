#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "usage: $0 user@qnx-host [release|debug]" >&2
  exit 64
fi

TARGET="$1"
BUILD_KIND="${2:-release}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
QNX_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
BIN_DIR="$QNX_ROOT/build/qnx-aarch64-$BUILD_KIND/bin"
REMOTE_ROOT="/data/home/qnxuser/ignis"

[ -d "$BIN_DIR" ] || { echo "Build first: qnx/scripts/build-qnx.sh $BUILD_KIND" >&2; exit 66; }
for binary in camera_service inference_service incident_engine stream_service watchdog_service alarm_service; do
  [ -f "$BIN_DIR/$binary" ] || { echo "Missing $BIN_DIR/$binary" >&2; exit 66; }
done

ssh "$TARGET" "mkdir -p '$REMOTE_ROOT/bin' '$REMOTE_ROOT/lib' '$REMOTE_ROOT/models' '$REMOTE_ROOT/config' '$REMOTE_ROOT/data/incidents' '$REMOTE_ROOT/logs' '$REMOTE_ROOT/scripts'"
scp "$BIN_DIR"/* "$TARGET:$REMOTE_ROOT/bin/"
scp "$QNX_ROOT/config"/*.json "$QNX_ROOT/config"/*.yaml "$TARGET:$REMOTE_ROOT/config/"
scp "$QNX_ROOT/scripts/start-ignis.sh" "$QNX_ROOT/scripts/stop-ignis.sh" \
  "$QNX_ROOT/scripts/failure-demo.sh" "$QNX_ROOT/scripts/collect-logs.sh" \
  "$TARGET:$REMOTE_ROOT/scripts/"
scp "$QNX_ROOT/models/labels.txt" "$TARGET:$REMOTE_ROOT/models/"

if [ -f "$QNX_ROOT/models/fire_smoke_detector.tflite" ] && [ -f "$QNX_ROOT/models/model_manifest.json" ]; then
  scp "$QNX_ROOT/models/fire_smoke_detector.tflite" "$QNX_ROOT/models/model_manifest.json" \
    "$TARGET:$REMOTE_ROOT/models/"
else
  echo "Model/manifest absent: hardware inference will report degraded mode."
fi

ssh "$TARGET" "chmod 755 '$REMOTE_ROOT'/bin/* '$REMOTE_ROOT'/scripts/*.sh && sha256 '$REMOTE_ROOT'/bin/*"
echo "Secrets were not copied. Create $REMOTE_ROOT/config/device.env on the Pi, then run:"
echo "ssh $TARGET '$REMOTE_ROOT/scripts/start-ignis.sh'"

