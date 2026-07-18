#!/bin/sh
set -u
echo "IGNIS QNX target verification"
uname -a
echo "Camera/Sensor Framework candidates"
find /usr /lib /opt -iname '*sensor*' -o -iname '*camera*' 2>/dev/null | head -80
echo "TensorFlow Lite/OpenCV/turbojpeg candidates"
find /usr /lib /opt -iname '*tensorflow*' -o -iname '*opencv*' -o -iname '*turbojpeg*' 2>/dev/null | head -80
echo "Logging/GPIO candidates"
which slog2info 2>/dev/null || true
find /usr/include -iname '*gpio*' 2>/dev/null | head -40
echo "Save this output in docs/environment-audit.md before enabling hardware mode."

