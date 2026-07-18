# IGNIS model pipeline

The training tools keep source groups intact, calibrate thresholds, export a TFLite artifact, and generate the manifest consumed by the edge service. No dataset or trained model is included; dataset sources and licenses must be recorded before training.

The lightweight split, calibration, annotation, and manifest tools run without a GPU. `train.py`, `export_tflite.py`, and `validate_tflite.py` load optional ML runtimes only when invoked and fail with a precise installation message when absent.

