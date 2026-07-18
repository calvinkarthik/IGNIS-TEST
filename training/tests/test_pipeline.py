from __future__ import annotations

from pathlib import Path

import pytest

from ignis_training.calibrate_thresholds import best_f1_threshold
from ignis_training.generate_manifest import generate_manifest
from ignis_training.split_by_source import split_records
from ignis_training.validate_split import validate_split


def test_source_groups_never_leak() -> None:
    records = [
        {"path": f"{source}-{index}.jpg", "source_id": source, "label": "fire"}
        for source in ("clip-a", "clip-b", "clip-c", "clip-d", "clip-e")
        for index in range(3)
    ]
    split = split_records(records)
    counts = validate_split(split)
    assert sum(counts.values()) == len(records)


def test_split_validator_rejects_leakage() -> None:
    with pytest.raises(ValueError, match="source leakage"):
        validate_split(
            {
                "train": [{"path": "a.jpg", "source_id": "clip"}],
                "validation": [{"path": "b.jpg", "source_id": "clip"}],
                "test": [],
            }
        )


def test_manifest_contains_real_hash(tmp_path: Path) -> None:
    model = tmp_path / "model.tflite"
    model.write_bytes(b"synthetic-test-model")
    manifest = generate_manifest(model)
    assert len(manifest["model_sha256"]) == 64
    assert manifest["labels"] == {"0": "fire", "1": "smoke"}


def test_threshold_calibration() -> None:
    result = best_f1_threshold([0, 0, 1, 1], [0.1, 0.3, 0.7, 0.9])
    assert result["f1"] == 1.0
    assert 0.31 <= result["threshold"] <= 0.7

