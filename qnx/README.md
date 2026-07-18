# IGNIS on the QNX Raspberry Pi

The production multi-service path below is frozen. For the current camera/model/stream proof of concept, use [`../docs/POC_HANDOFF.md`](../docs/POC_HANDOFF.md) and run `poc/pi/doctor.sh` followed by `poc/pi/run-poc.sh` from the repository root.

This subtree is the Pi deployment surface. Pulling the repository on the Pi updates source, configuration examples, and operational scripts. Runtime binaries normally come from the licensed QNX SDP cross-build and are deployed into `/data/home/qnxuser/ignis/bin`; if the Pi itself has the verified SDP environment and compiler, `pi-update-and-start.sh` can build after `git pull`.

Create this untracked Pi file before startup:

```sh
# /data/home/qnxuser/ignis/config/device.env
export IGNIS_DEVICE_TOKEN='same-secret-as-the-laptop-backend'
export IGNIS_BACKEND_HOST='192.168.137.1'
export IGNIS_BACKEND_PORT='9001'
export IGNIS_DEVICE_ID='ignis-qnxpi-01'
export IGNIS_CAMERA_MODE='qnx'
```

Then run `/data/home/qnxuser/ignis/scripts/start-ignis.sh`. For a no-camera transport rehearsal use `IGNIS_CAMERA_MODE=synthetic`; that is explicitly simulated and does not validate Camera Module 3 capture or TensorFlow Lite.
