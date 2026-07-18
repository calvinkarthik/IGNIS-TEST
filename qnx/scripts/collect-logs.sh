#!/bin/sh
set -eu
ROOT="${IGNIS_ROOT:-/data/home/qnxuser/ignis}"
OUTPUT="${1:-$ROOT/ignis-diagnostics-$(date +%Y%m%d-%H%M%S).tar.gz}"
tar -czf "$OUTPUT" -C "$ROOT" logs config data/incidents
echo "$OUTPUT"

