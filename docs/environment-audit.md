# Environment audit

Audit date: 2026-07-18, Windows (reported kernel `10.0.26200.0`), PowerShell 5.1.

## Detected

| Tool | Result |
|---|---|
| Codex-bundled Python | 3.12.13 |
| Codex-bundled Node.js | 24.14.0 |
| Git | 2.51.0.windows.1 |
| GitHub CLI | 2.79.0 |
| MinGW g++ | 6.3.0 (old; portable fallback only) |
| GNU Make | 3.81 |

## Not detected

- system `python`/usable Windows launcher, system `node`/`npm`
- CMake, Ninja, Clang, Docker
- QNX SDP environment variables or installation in common locations
- `qcc`, QNX target headers, Sensor Framework, `slog2`, QNX message-passing samples
- QNX AI Camera App source or a known-working Camera Module 3 sample
- target TensorFlow Lite, OpenCV, turbojpeg, or GPIO libraries
- connected QNX/Raspberry Pi camera hardware
- model file and training dataset
- ElevenLabs or Twilio credentials and an approved demo number

## Consequences

The portable edge logic, backend, simulator, and frontend can be built and tested on the laptop. QNX-only source is kept behind compile-time adapters and cannot be truthfully marked hardware-tested. Before target integration, run `qnx/scripts/verify-target.sh`, attach the known-working camera sample, and update `docs/camera-setup.md` with the observed pixel format, dimensions, stride, buffer lifetime, and callback contract.

## External API research

Implementation was aligned to the current official ElevenLabs React SDK, signed URL, dynamic variables, and native Twilio outbound-call documentation as of the audit date. Exact links are recorded in `docs/elevenlabs-setup.md` and `docs/twilio-setup.md`.

