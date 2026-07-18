#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SOURCE="$REPO_ROOT/poc/pi/qnx_camera_capture.c"
OUTPUT="$REPO_ROOT/poc/pi/qnx_camera_capture"

if ! command -v clang >/dev/null 2>&1; then
    printf 'clang is required to build the QNX camera adapter.\n' >&2
    exit 1
fi
if [ ! -f /usr/include/camera/camera_api.h ]; then
    printf 'Install qnx-sensor-framework-dev before building.\n' >&2
    exit 1
fi

clang -std=c11 -O2 -Wall -Wextra "$SOURCE" -lcamapi -o "$OUTPUT"
printf 'Built %s\n' "$OUTPUT"
