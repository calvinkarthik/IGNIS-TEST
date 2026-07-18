#!/bin/sh
set -eu

BUILD_KIND="${1:-release}"
case "$BUILD_KIND" in
  release) OPT_FLAGS="-O2 -DNDEBUG" ;;
  debug) OPT_FLAGS="-O0 -g" ;;
  *) echo "usage: $0 [release|debug]" >&2; exit 64 ;;
esac

: "${QNX_HOST:?Source the verified QNX SDP 8.0 environment first}"
: "${QNX_TARGET:?Source the verified QNX SDP 8.0 environment first}"

command -v q++ >/dev/null 2>&1 || { echo "q++ was not found in PATH" >&2; exit 69; }

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
QNX_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
BUILD_ROOT="$QNX_ROOT/build/qnx-aarch64-$BUILD_KIND"
BIN_DIR="$BUILD_ROOT/bin"
mkdir -p "$BIN_DIR"

VARIANT="${IGNIS_QNX_COMPILER_VARIANT:-gcc_ntoaarch64le}"
CXXFLAGS="-V$VARIANT -std=c++17 $OPT_FLAGS -Wall -Wextra -Wpedantic -I$QNX_ROOT/common/include"
COMMON="$QNX_ROOT/common/src/geometry.cpp $QNX_ROOT/common/src/incident.cpp $QNX_ROOT/common/src/protocol.cpp"

q++ $CXXFLAGS -I"$QNX_ROOT/camera_service/include" $COMMON \
  "$QNX_ROOT/camera_service/src/frame_sources.cpp" "$QNX_ROOT/camera_service/src/main.cpp" \
  -o "$BIN_DIR/camera_service"
q++ $CXXFLAGS -I"$QNX_ROOT/inference_service/include" $COMMON \
  "$QNX_ROOT/inference_service/src/inference_engine.cpp" "$QNX_ROOT/inference_service/src/main.cpp" \
  -o "$BIN_DIR/inference_service"
q++ $CXXFLAGS $COMMON "$QNX_ROOT/incident_engine/src/main.cpp" -o "$BIN_DIR/incident_engine"
q++ $CXXFLAGS $COMMON "$QNX_ROOT/stream_service/src/main.cpp" -lsocket -o "$BIN_DIR/stream_service"
q++ $CXXFLAGS $COMMON "$QNX_ROOT/watchdog_service/src/main.cpp" -o "$BIN_DIR/watchdog_service"
q++ $CXXFLAGS $COMMON "$QNX_ROOT/alarm_service/src/main.cpp" -o "$BIN_DIR/alarm_service"

echo "QNX binaries: $BIN_DIR"
ls -l "$BIN_DIR"

