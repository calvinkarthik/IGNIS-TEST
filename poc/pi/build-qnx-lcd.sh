#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SOURCE="$REPO_ROOT/poc/pi/qnx_lcd_display.c"
OUTPUT="$REPO_ROOT/poc/pi/qnx_lcd_display"

if ! command -v clang >/dev/null 2>&1; then
    printf 'clang is required to build the QNX SPI LCD adapter.\n' >&2
    exit 1
fi
if [ ! -f /usr/include/hw/io-spi.h ]; then
    printf 'QNX io-spi development headers are required.\n' >&2
    exit 1
fi

QNX_SAMPLES_ROOT=${IGNIS_QNX_SAMPLES_ROOT:-/home/qnxuser/hardware-component-samples}
GPIO_INCLUDE="$QNX_SAMPLES_ROOT/common/system/gpio"
if [ ! -f "$GPIO_INCLUDE/sys/rpi_gpio.h" ]; then
    printf 'QNX Raspberry Pi GPIO message header is required under %s.\n' "$GPIO_INCLUDE" >&2
    exit 1
fi

clang -std=c11 -O2 -Wall -Wextra -I"$GPIO_INCLUDE" "$SOURCE" -o "$OUTPUT"
printf 'Built %s\n' "$OUTPUT"
