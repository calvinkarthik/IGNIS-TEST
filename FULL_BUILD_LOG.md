# Full build work log — frozen

The full IGNIS build was paused on 2026-07-18 so the camera/model/stream POC could be proven first. All completed work remains in the repository.

## Completed before the pause

- Defined the strict authority split: QNX owns vision and hazard state; FastAPI coordinates; React visualizes.
- Implemented and tested the shared authenticated binary TCP protocol with sequence numbers, monotonic timestamps, bounded payloads, and CRC-32.
- Implemented portable C++ geometry, protocol, model-decoding, and deterministic incident logic.
- Implemented FastAPI, SQLite persistence, device authentication, TCP ingest, WebSocket snapshots/updates, incident APIs, response timeout handling, and safety-gated communication adapters.
- Implemented a React/Vite dashboard with live JPEG frames, normalized detection overlays, incident state, timeline, device health, zones, and disabled-by-default communication controls.
- Implemented a deterministic laptop simulator with real JPEG packets, fire/smoke scenarios, fragmentation, coalescing, bad-token, disconnect, timestamp, and payload fault modes.
- Implemented the training-tool surface for source-safe dataset splitting, threshold calibration, TFLite export/manifest generation, and validation. No dataset or trained weights were supplied.
- Prepared QNX service boundaries, portable process entry points, build/deploy/start/stop scripts, configuration, and guarded vendor integration seams.
- Exercised a live laptop vertical slice: simulator authentication, streaming, incident persistence, confirmation, growth/smoke evidence, and no-response escalation.
- Fixed a replay/reconnect regression so repeated QNX `AWAITING_RESPONSE` updates cannot downgrade a backend incident already in `ESCALATING`.

## Verification completed before the pause

- Backend tests: passed before the last regression test was added; the current suite is rerun as part of the POC handoff.
- Frontend: 8 tests passed, lint passed, TypeScript passed, and the production build passed.
- Portable C++: geometry, incident engine, protocol, and model-decoder executables passed.
- Simulator golden protocol test passed.
- Live simulator-to-backend-to-dashboard data path was exercised.

## Verification after the POC conversion

- Backend: `19 passed`.
- POC temporal gate, production-protocol compatibility, offline streaming behavior, input quantization/normalization, and YOLOv8 decoding/NMS: `10 passed`.
- Simulator golden protocol: `1 passed`.
- Training utilities: `4 passed`.
- Frontend: `6` test files and `8` tests passed; ESLint, TypeScript, and the Vite production build passed.
- Portable C++: geometry, incident engine, protocol, and model decoder all passed.
- Python static analysis across backend, simulator, training, and POC: passed.
- Laptop launcher smoke test: backend reported `HEALTHY`, dashboard returned HTTP `200`, and the stop script closed ports 8000, 5173, and 9001.
- POC Python, PowerShell, and POSIX shell syntax checks: passed.

These results do not include a real QNX camera or real TFLite model invocation; those remain the target acceptance gate.

## Explicitly unfinished or unverified

- Real QNX Sensor Framework Camera Module 3 adapter.
- Target TensorFlow Lite runtime integration and real model performance.
- Shared-memory camera/inference services on QNX hardware.
- Local evidence package, alarm GPIO, and watchdog recovery on the Pi.
- Browser voice and real outbound demo call credentials/execution.
- Complete production deployment and all final documentation/CI polish.

See `TODO_AFTER_POC.md` before resuming the full build.
