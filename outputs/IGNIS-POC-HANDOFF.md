# IGNIS camera + fire ML POC handoff

The full build is paused. The active proof of concept is:

```text
QNX Pi camera -> local TFLite fire/smoke model -> multi-frame verification -> laptop dashboard
```

## What is ready

- `poc/pi/`: camera, local TFLite inference, YOLOv8/SSD decoding, temporal verification, local logging, authenticated laptop streaming, and automatic reconnect.
- `poc/laptop/`: one-command backend/dashboard start and stop.
- `poc/pi/doctor.sh`: real target gate for camera, runtime, model, inference, and laptop reachability.
- `poc/model/prepare-yolov8.py`: converts licensed two-class YOLOv8 weights to TFLite and writes the matching manifest.
- `POC_STATUS.md`: exact implemented/unverified state.
- `FULL_BUILD_LOG.md`: preserved work and test results.
- `TODO_AFTER_POC.md`: frozen backlog.
- `docs/POC_HANDOFF.md`: complete setup and acceptance procedure.

## Laptop

```powershell
powershell -ExecutionPolicy Bypass -File poc\laptop\run-poc-laptop.ps1
```

Change `IGNIS_DEVICE_TOKEN` in `backend/.env`, then open `http://localhost:5173`.

## QNX Pi after the repository is published

```sh
cd /path/to/ignis
git pull --ff-only
cp poc/pi/ignis-poc.env.example poc/pi/ignis-poc.env
# Edit the laptop IP, matching token, camera source, and model paths.
sh poc/pi/doctor.sh
sh poc/pi/run-poc.sh
```

The model is intentionally not included: no licensed, trained two-class fire/smoke artifact was supplied. Place it at `qnx/models/fire_smoke_detector.tflite` and create the matching `qnx/models/model_manifest.json` before preflight.

## Verified here

- Backend: 19 tests passed.
- POC: 10 tests passed.
- Simulator: 1 test passed.
- Training utilities: 4 tests passed.
- Frontend: 8 tests, lint, TypeScript, and production build passed.
- Portable C++: all 4 test programs passed.
- Laptop smoke test: API healthy, dashboard HTTP 200, clean stop.

## Not verified here

No QNX Pi, Camera Module 3, QNX camera sample/runtime, or real fire/smoke TFLite model was present. Hardware success must not be claimed until `doctor.sh` and the acceptance procedure pass on the real Pi.

## Publication blocker

The current Codex workspace contains an empty `.git` directory and no Git remote. The work is complete locally but cannot be pulled by the Pi until it is placed in the intended GitHub repository and pushed.
