from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


def best_f1_threshold(labels: Iterable[int], scores: Iterable[float]) -> dict[str, float]:
    pairs = list(zip(labels, scores, strict=True))
    if not pairs:
        raise ValueError("calibration data is empty")
    best = {"threshold": 0.5, "precision": 0.0, "recall": 0.0, "f1": -1.0}
    for step in range(1, 100):
        threshold = step / 100
        true_positive = sum(label == 1 and score >= threshold for label, score in pairs)
        false_positive = sum(label == 0 and score >= threshold for label, score in pairs)
        false_negative = sum(label == 1 and score < threshold for label, score in pairs)
        precision = true_positive / max(1, true_positive + false_positive)
        recall = true_positive / max(1, true_positive + false_negative)
        f1 = 2 * precision * recall / max(1e-12, precision + recall)
        if f1 > best["f1"]:
            best = {"threshold": threshold, "precision": precision, "recall": recall, "f1": f1}
    return best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path, help="JSON array with label and score")
    args = parser.parse_args()
    values = json.loads(args.predictions.read_text(encoding="utf-8"))
    result = best_f1_threshold(
        (int(item["label"]) for item in values), (float(item["score"]) for item in values)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

