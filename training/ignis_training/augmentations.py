from __future__ import annotations


def recommended_augmentations() -> dict[str, float | bool]:
    return {
        "horizontal_flip_probability": 0.5,
        "brightness_delta": 0.20,
        "contrast_delta": 0.20,
        "hue_delta": 0.04,
        "blur_probability": 0.10,
        "compression_probability": 0.15,
        "mosaic": False,
    }

