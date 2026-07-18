#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SOURCE="$REPO_ROOT/poc/pi/qnx_lcd_display.c"
OUTPUT="$REPO_ROOT/poc/pi/qnx_lcd_display"

if ! command -v clang >/dev/null 2>&1; then
    printf 'clang is required to build the QNX Screen LCD adapter.\n' >&2
    exit 1
fi
if [ ! -f /usr/include/screen/screen.h ]; then
    printf 'QNX Screen development headers are required.\n' >&2
    exit 1
fi

clang -std=c11 -O2 -Wall -Wextra "$SOURCE" -lscreen -o "$OUTPUT"
printf 'Built %s\n' "$OUTPUT"
