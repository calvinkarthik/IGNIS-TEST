# POC model source

The temporary POC model is derived from `runs/detect/train/weights/best.pt` in:

```text
https://github.com/Abonia1/YOLOv8-Fire-and-Smoke-Detection
```

The source model declares three output classes: `Fire`, `default`, and `smoke`.
IGNIS treats `fire` and `smoke` as hazard detections and explicitly ignores
`default`. This model is for proof-of-concept evaluation only and is not a
validated or safety-certified fire detector.
