# POC model source

The temporary POC model is the pretrained `best.pt` from:

```text
https://huggingface.co/rabahdev/fire-smoke-yolov8n
```

The checkpoint is a 3.0-million-parameter YOLOv8n detector trained on D-Fire.
It declares exactly two output classes: `0=smoke` and `1=fire`. The model card
reports test mAP50 of 0.754 at 640-pixel input; IGNIS exports it at 320x320 for
the Raspberry Pi POC. The source checkpoint SHA-256 is
`b91633799ceb052c814b4f8b77a37efc9a40f002d528df97d74463585fa4f28f`.

The model is distributed under AGPL-3.0. It is for proof-of-concept evaluation
only and is not a validated or safety-certified fire detector. A displayed
photo or video can trigger it; it does not establish that a physical fire is
present.
