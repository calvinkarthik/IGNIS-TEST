# IGNIS session command log

Commands run this session, in order, grouped by phase. Paths below use the
scratchpad clone (`SRC`) that was the working copy for most of the session;
`AI_2026\IGNIS-TEST` (this folder) is now synced to match it.

## 1. Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Then edited `.env`:
```
IGNIS_DEVICE_TOKEN=ignis-poc-2026-private
```

Start the backend:
```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 2. Frontend setup

```powershell
cd frontend
npm install
npm run dev -- --host
```

Edited `frontend\src\App.tsx` to temporarily disable VoicePanel (it crashes
without a `ConversationProvider` wrapper that the ElevenLabs integration
hasn't added yet):
```tsx
{/* VoicePanel temporarily disabled for local viewing */}
{false && <VoicePanel incident={incident} />}
```

## 3. Simulator (fake Pi, for testing the pipeline without hardware)

```powershell
$env:IGNIS_DEVICE_TOKEN = "ignis-poc-2026-private"
cd backend
.\.venv\Scripts\python.exe -m pip install Pillow
.\.venv\Scripts\python.exe -m simulator.ignis_simulator.cli --scenario confirmed_fire --loop
```

## 4. Pulling Calvin's new commits

```powershell
git fetch origin
git log --oneline -5 origin/main
git merge origin/main --no-edit
```
This brought in two commits: the real TFLite model (`f842f08`) and the QNX
Sensor Framework camera adapter (`6caeba5`).

## 5. Connecting to the QNX Pi

The Pi's actual address on its own network is `192.168.137.106` (not `.214`
— that was a stale DHCP lease remembered in `known_hosts`). This laptop has
to be joined to that same network (its Wi-Fi shows `192.168.137.41` when
connected).

```powershell
ssh -m hmac-sha2-256 qnxuser@192.168.137.106
# password: qnxuser (default — should be changed)
```

Once connected, the real repo is already cloned there at:
```
~/IGNISv1/IGNIS-TEST
```

## 6. Preflight + running the real POC on the Pi

```sh
cd ~/IGNISv1/IGNIS-TEST
cat poc/pi/ignis-poc.env        # confirm IGNIS_BACKEND_HOST points at 192.168.137.41
sh poc/pi/doctor.sh             # should print: READY: all POC prerequisites passed.
sh poc/pi/run-poc.sh            # starts real camera + real model streaming to this laptop
```

If `doctor.sh` fails on the camera step with `camera_open(unit=1) failed: 16`
(EBUSY), a leftover `qnx_camera_capture` process is holding the device open.
Find and kill it:
```sh
pidin | grep qnx_camera_capture
kill -9 <pid>
```

## 7. Verifying it's working

```powershell
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/devices
```
Look for `"device_id":"ignis-qnxpi-01"`, `"connected":true`, and
`"software_version":"poc-0.1.0"` with `"source_mode":"QNX_POC"` — that's the
real Pi, not the simulator (simulator reports `LAPTOP_SIMULATOR`/
`simulator-0.1.0` instead).

Dashboard: `http://localhost:5173`
