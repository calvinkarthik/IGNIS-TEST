# Camera service

`camera_service` supports `synthetic` and raw-RGB `replay` modes now. Hardware mode intentionally returns a clear configuration error until the known-working QNX 8 Camera Module 3 sample is copied behind `QnxSensorFrameSource`.

Do not substitute guessed Sensor Framework functions. The target bridge must copy a vendor-owned frame into the bounded shared ring before returning the vendor buffer and must record actual width, height, stride, format, timestamp, and ownership details in `docs/camera-setup.md`.

