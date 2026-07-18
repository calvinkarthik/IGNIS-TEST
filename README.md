# IGNIS

IGNIS is a prototype visual fire and smoke detection system. The full product build is currently paused while one temporary proof of concept is proven: **the QNX Pi captures the camera, runs the fire/smoke model locally, and streams the results to the laptop.**

> **DEMO SYSTEM — NOT A CERTIFIED FIRE ALARM OR LIFE-SAFETY DEVICE.** IGNIS does not replace certified smoke alarms, emergency procedures, or professional emergency services. It never calls a public emergency number. Outbound demo calls are disabled by default and are restricted to a server-side allowlist.

## Current scope: camera + model + laptop POC

Start with [the POC handoff](docs/POC_HANDOFF.md). It contains the laptop command, Pi `git pull` workflow, model contract, preflight, run command, and acceptance test.

The repository includes the Pi POC runner, deterministic multi-frame fire verification, authenticated reconnecting stream, laptop backend/dashboard, and target preflight. The laptop vertical slice has been exercised with the simulator. Real camera capture and inference have not yet been run on the QNX Pi because the target, model, and QNX-compatible runtime were unavailable here.

Read [POC_STATUS.md](POC_STATUS.md) for the exact truth state, [FULL_BUILD_LOG.md](FULL_BUILD_LOG.md) for preserved work, and [TODO_AFTER_POC.md](TODO_AFTER_POC.md) for the frozen backlog.

## Start the laptop POC

```powershell
powershell -ExecutionPolicy Bypass -File poc\laptop\run-poc-laptop.ps1
```

Then open `http://localhost:5173`. On the Pi, after configuration and a successful preflight:

```sh
sh poc/pi/doctor.sh
sh poc/pi/run-poc.sh
```

The Pi and laptop must use the same private device token. Never commit the configured token.

## Components

- `qnx/`: portable incident authority, protocol, frame source/ring contracts, process entry points, target scripts, and guarded QNX/TFLite integration seams.
- `backend/`: FastAPI, TCP protocol server, SQLite, WebSockets, voice signing, deterministic timeout, and call safety policy.
- `frontend/`: React/Vite dashboard, live overlays, health, timeline, incident controls, and opt-in ElevenLabs voice.
- `simulator/`: authenticated device simulator with deterministic scenarios and TCP fault modes.
- `training/`: dataset split/validation, calibration, export/manifest tools, and tests.
- `docs/`: architecture, setup, protocol, safety, testing, and demonstration guides.

The broader voice/call/alarm/watchdog work remains in the tree but is outside the current POC.

## Safety defaults

- `DEMO_CALLS_ENABLED=false`
- no destination can be typed into the dashboard
- only exact E.164 numbers in `DEMO_ALLOWED_NUMBERS` are eligible
- emergency-number patterns are always denied
- one call per incident and a global cooldown are enforced transactionally
- API acceptance is reported as `CALL REQUEST ACCEPTED`; connection is never inferred
- zone names are sanitized and never treated as causes
- all language is evidence-grounded and explicitly uncertain
