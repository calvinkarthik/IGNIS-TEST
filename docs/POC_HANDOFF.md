# Camera + fire ML POC handoff

This is the only active IGNIS workflow. It keeps all fire/smoke decisions on the QNX Pi and uses the laptop only for storage and visualization.

> Prototype only. Do not use IGNIS as a fire alarm and do not test with a live fire. Point the camera at prepared fire footage on a display.

## 1. Start the laptop

From the repository root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File poc\laptop\run-poc-laptop.ps1
```

Open `http://localhost:5173`. The dashboard may initially say the Pi is disconnected. That is expected.

Edit `backend/.env` and replace `IGNIS_DEVICE_TOKEN` with a private random value. Restart the laptop POC after changing it. Allow private-network inbound access to TCP ports `9001` (Pi stream), `8000` (API), and `5173` (dashboard) if Windows Firewall prompts.

To stop the laptop services:

```powershell
powershell -ExecutionPolicy Bypass -File poc\laptop\stop-poc-laptop.ps1
```

## 2. Put the model in the repository checkout

The detector requires a real two-class TFLite object detector whose labels are exactly `fire` and `smoke`. The POC supports:

- Ultralytics YOLOv8 TFLite output: one `[1, 4 + classes, predictions]` output.
- SSD-style TFLite output: boxes, class IDs, scores, and count.

Place the model at:

```text
qnx/models/fire_smoke_detector.tflite
```

For licensed YOLOv8 `.pt` weights, the laptop conversion helper exports the TFLite file and inspects it to generate the matching manifest:

```powershell
python -m venv work\model-venv
work\model-venv\Scripts\python -m pip install -r training\requirements-ml.txt
work\model-venv\Scripts\python poc\model\prepare-yolov8.py C:\path\to\licensed-best.pt
```

For a pre-existing TFLite file, copy `qnx/models/model_manifest.example.json` to `qnx/models/model_manifest.json`, update the input dtype/shape, normalization, class order, and decoder to match the actual artifact, and replace `model_sha256` with the file's SHA-256. A mismatched hash, dtype, shape, label set, or output contract causes a clear startup failure.

No model weights are committed because no trained/licensed artifact or dataset provenance was supplied. A generic COCO detector is not sufficient because COCO has no `fire` or `smoke` class.

## 3. Pull and configure on the QNX Pi

```sh
cd /path/to/ignis
git pull --ff-only
cp poc/pi/ignis-poc.env.example poc/pi/ignis-poc.env
```

Edit `poc/pi/ignis-poc.env`:

- Set `IGNIS_BACKEND_HOST` to the laptop's private IPv4 address.
- Set `IGNIS_DEVICE_TOKEN` to the exact laptop value.
- Set `IGNIS_CAMERA_SOURCE` to `0` only when that opens the real camera through OpenCV. Otherwise use the exact capture source/pipeline from the camera sample already proven on this QNX image.
- Adjust model paths if the untracked model is provisioned outside the checkout.

Do not commit `ignis-poc.env` or the model.

## 4. Run the target preflight

Start the laptop first, then on the Pi:

```sh
sh poc/pi/doctor.sh
```

This performs a real one-frame capture and checks the target runtime and laptop port. `READY` means the temporary Python path can run. `MISSING` identifies the exact dependency.

If the Pi image does not include Python, OpenCV bindings, NumPy, or a QNX/ARM TensorFlow Lite interpreter, do not install Linux ARM wheels: they are ABI-incompatible with QNX. Supply the target libraries from the licensed QNX environment/AI Camera App, or promote the adapter to C++ using the actual working Sensor Framework sample.

## 5. Run the POC

For the optional 480x320 local LCD, set these values in
`poc/pi/ignis-poc.env` before starting:

```sh
export IGNIS_LCD_ENABLED='1'
export IGNIS_LCD_WIDTH='480'
export IGNIS_LCD_HEIGHT='320'
export IGNIS_LCD_FLASH_SECONDS='0.75'
```

Build its native QNX SPI/ILI9486 adapter once on the Pi:

```sh
sh poc/pi/build-qnx-lcd.sh
```

The LCD shows one large IGNIS logo with a white background and black lettering.
After the local verifier reaches `CONFIRMED`, it alternates between the logo and
a solid red frame. It returns to the logo when the verifier resets five seconds
after the last relevant detection. It never receives camera frames or detection
boxes. One persistent native helper owns the LCD, blanks it during each complete
frame replacement, writes the target frame twice, then reveals it. A volatile
`/dev/shmem` writer lock prevents competing LCD helpers, and `run-poc.sh` uses a
single-instance lock so duplicate edge/camera processes cannot start. Camera and
inference output remain on the laptop dashboard. The adapter uses
`/dev/io-spi/spi0/dev0`, the native `/dev/gpio/msg` interface, GPIO24 for
command/data, and GPIO25 for reset. Linux framebuffer overlays and
Waveshare Linux install scripts are not compatible with QNX. If SPI/GPIO access
is absent, the LCD logo disables itself while inference and laptop streaming
continue.

```sh
sh poc/pi/run-poc.sh
```

Expected Pi output includes:

```text
IGNIS POC running
Laptop stream connected
LOCAL STATE SUSPECTED
LOCAL STATE VERIFYING
LOCAL STATE CONFIRMED
```

Local state transitions and health are appended to `poc/pi/data/ignis-poc.jsonl`. If the laptop disappears, the Pi prints that local inference continues and reconnects automatically.

## 6. Acceptance test

1. Show a normal room for at least ten seconds: state stays `CLEAR`.
2. Show a brief one-frame/very short fire image: it must not reach `CONFIRMED`.
3. Show prepared fire footage for several seconds: aligned fire boxes appear and the state progresses `SUSPECTED` → `VERIFYING` → `CONFIRMED`.
4. Stop the laptop or disconnect Wi-Fi: the Pi keeps logging inference locally.
5. Restore the laptop/network: the live stream reconnects without restarting the Pi process.
6. Save the terminal output, local JSONL log, model hash, and a dashboard screenshot as the POC record.

Model accuracy is separate from software integration. Treat false positives/negatives as a model/dataset calibration result, not proof that the camera/stream plumbing failed.

## If preflight fails

Send back the complete output of:

```sh
sh poc/pi/doctor.sh
```

Also provide the path or source for the camera sample that currently works on that Pi. That is the minimum evidence needed to implement the real Sensor Framework adapter without inventing QNX APIs.
