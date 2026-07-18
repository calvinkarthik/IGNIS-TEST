# Work deferred until the POC passes

Resume the full build only after the six exit criteria in `POC_STATUS.md` pass on the real QNX Pi.

## First: promote the proven POC

- Replace the temporary Python/OpenCV camera path with the exact QNX Sensor Framework sample/API proven on the target.
- Move the verified model preprocessing/decoder into the native C++ inference service.
- Compare the same image through the POC and native service and require matching boxes within a documented tolerance.
- Preserve the tested wire contract so the laptop requires no rewrite.

## Then: edge reliability

- Wire camera, inference, incident, streaming, alarm, and watchdog services through QNX IPC/shared memory.
- Add bounded local evidence storage and restart-safe incident journaling.
- Verify laptop disconnect, camera loss, inference crash/restart, storage exhaustion, and reboot behavior on hardware.
- Implement and verify optional GPIO LED/buzzer only with the actual target library/pin configuration.

## Then: product functions

- Finish zone association, growth/smoke sequencing, occupant option, and evidence review in hardware mode.
- Complete browser voice verification with real ElevenLabs credentials.
- Exercise a call only to an explicitly allowlisted teammate demo number; never a public emergency number.
- Finish the demo runbook, deployment packaging, CI, and hardware acceptance record.

## Inputs that will be needed

- Output from `poc/pi/doctor.sh` on the Pi.
- The exact working QNX camera sample and its headers/libraries or capture pipeline.
- A licensed QNX/ARM TensorFlow Lite runtime.
- A licensed, validated two-class fire/smoke model plus dataset/license record.
- QNX SDP build host access for the native promotion step.
