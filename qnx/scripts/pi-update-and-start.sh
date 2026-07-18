#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$REPO_ROOT"
git pull --ff-only

if [ -n "${QNX_HOST:-}" ] && [ -n "${QNX_TARGET:-}" ] && command -v q++ >/dev/null 2>&1; then
  "$REPO_ROOT/qnx/scripts/build-qnx.sh" release
  mkdir -p /data/home/qnxuser/ignis/bin
  cp "$REPO_ROOT/qnx/build/qnx-aarch64-release/bin/"* /data/home/qnxuser/ignis/bin/
fi

/data/home/qnxuser/ignis/scripts/stop-ignis.sh || true
/data/home/qnxuser/ignis/scripts/start-ignis.sh

