# Inference service

Portable detection normalization and manifest validation are implemented. The target TensorFlow Lite loader is deliberately not fabricated: bind the verified QNX runtime and validate model hash, tensor rank/dimensions/types, output indexes, and labels before enabling normal inference. Until then the service exits with a degraded-mode configuration code so the watchdog and dashboard report the truth.

