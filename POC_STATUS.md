# IGNIS POC status

Updated: 2026-07-18 (America/Toronto)

## Active objective

Only this path is active:

```text
QNX Raspberry Pi camera
  -> local TensorFlow Lite fire/smoke inference
  -> deterministic multi-frame verification
  -> authenticated laptop stream
  -> live React picture, boxes, state, and health
```

The broader voice, phone, alarm, watchdog, zone editor, evidence packaging, and production multi-process work is frozen. It has not been deleted.

## Ready in the repository

- A single-process Pi POC runner that opens the configured camera, invokes a local TFLite detector, rejects one-frame triggers, records local JSONL state events, and sends JPEGs/detections/incidents/health to the laptop.
- SSD and Ultralytics YOLOv8 TFLite output decoding, manifest contract checks, model SHA-256 verification, normalized boxes, and class-aware non-maximum suppression.
- Network loss does not stop camera inference. Video is dropped while disconnected and streaming reconnects every two seconds.
- A laptop launcher for the existing FastAPI/React vertical slice.
- A QNX Pi preflight that tests Python, OpenCV, NumPy, TensorFlow Lite, the model, one actual camera frame, and laptop TCP reachability.
- A laptop conversion helper for licensed two-class YOLOv8 `.pt` weights; it exports TFLite and generates a hash/tensor-accurate manifest.
- Portable temporal-verification and protocol tests.

## Not yet proven

No Raspberry Pi, Camera Module 3, QNX Sensor Framework installation, QNX-compatible Python/OpenCV/TFLite runtime, or trained fire/smoke model was accessible in this workspace. Therefore real QNX camera capture and real target inference are **not hardware-verified**.

The repository intentionally contains no unlicensed or unvalidated model weights. A real two-class `fire`/`smoke` TFLite artifact and its matching manifest must be placed in `qnx/models/` before the target run.

## Exit criteria for this POC

The POC is accepted only when all of these are observed on the real equipment:

1. `doctor.sh` reports `READY` and captures one real camera frame.
2. The model loads and runs locally on QNX without a manifest/hash error.
3. The laptop shows live Pi frames and aligned fire/smoke boxes.
4. A single positive frame does not confirm an incident.
5. A sustained prepared fire video changes the local and laptop state to `CONFIRMED`.
6. Unplugging the network leaves local inference running; reconnecting restores the stream.

Never use a live fire for testing. Use prepared fire footage on a display. IGNIS is a prototype and not a certified fire alarm.
