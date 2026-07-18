# IGNIS build status

Updated: 2026-07-18 (America/Toronto)

> **Scope pause:** the full build is frozen. The active objective is only the QNX Pi camera + local TFLite fire/smoke inference + laptop stream POC. See `POC_STATUS.md`.

| Area | Status | Verification |
|---|---|---|
| Shared protocol/config contracts | Implemented | Python and portable C++ tests |
| Deterministic temporal incident engine | Implemented | Portable C++ tests and simulator scenarios |
| FastAPI + SQLite + WebSocket | Implemented | Backend tests and live simulator exercise |
| Raw authenticated TCP receiver | Implemented | Parser/unit tests plus simulator fragmentation/coalescing |
| React dashboard | Implemented | Type check, unit tests, production build |
| Laptop simulator | Implemented | Deterministic scenarios and protocol faults |
| Observation formatter | Implemented | Unit tests |
| Call policy/allowlist/dedup/cooldown | Implemented | Mock-provider backend tests; disabled by default |
| ElevenLabs signed URL/outbound adapters | Implemented | Contract tests only; no credentials used |
| QNX portable services/contracts | Implemented | Desktop compilation where supported |
| QNX Sensor Framework adapter | Integration seam prepared | Blocked: licensed SDK, target headers/sample, and Pi absent |
| TensorFlow Lite QNX execution | Integration seam prepared | Blocked: model and target TFLite libraries absent |
| Camera Module 3 | Not hardware-tested | No camera or QNX target available |
| Temporary Pi POC runner | Implemented; target run pending | Local tests only; `poc/pi/doctor.sh` is the hardware gate |
| Alarm GPIO | Null/simulated adapter | No target GPIO library or hardware available |
| QNX watchdog restart | Portable supervisor implemented | Not executed on QNX hardware |
| ElevenLabs browser voice | Implemented | SDK/build verification only; no agent credentials used |
| Twilio demo phone call | Implemented and safety-gated | Not exercised; no credentials/approved number supplied |

## Environment blockers

- No QNX SDP 8.0 installation, `qcc`, Sensor Framework headers, `slog2`, camera sample, QNX AI Camera App source, or target libraries were found.
- No Raspberry Pi QNX target or Camera Module 3 was attached.
- No TensorFlow Lite model, manifest hash, or licensed target runtime was supplied.
- No ElevenLabs/Twilio credentials or approved demonstration E.164 destination were supplied.
- The host has no system Python/Node/CMake/Docker; repository bootstrap uses the Codex-bundled runtimes for verification in this workspace.

These blockers do not affect the laptop simulator vertical slice.
