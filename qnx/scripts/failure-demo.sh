#!/bin/sh
set -eu
echo "Terminating inference_service only. Watch the dashboard for degraded and restart states."
slay inference_service
echo "Inference termination requested. The watchdog restart budget remains in force."

