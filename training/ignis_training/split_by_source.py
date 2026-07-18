from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def assign_source(source_id: str, seed: str, train: float, validation: float) -> str:
    digest = hashlib.sha256(f"{seed}:{source_id}".encode()).digest()
    value = int.from_bytes(digest[:8], "big") / (2**64 - 1)
    if value < train:
        return "train"
    if value < train + validation:
        return "validation"
    return "test"


def split_records(
    records: list[dict[str, Any]],
    seed: str = "ignis-v1",
    train: float = 0.7,
    validation: float = 0.15,
) -> dict[str, list[dict[str, Any]]]:
    if not 0 < train < 1 or not 0 <= validation < 1 or train + validation >= 1:
        raise ValueError("split ratios must leave a non-empty test fraction")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        source_id = str(record.get("source_id", "")).strip()
        if not source_id:
            raise ValueError("every record requires a source_id")
        grouped[source_id].append(record)
    result: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    for source_id, source_records in sorted(grouped.items()):
        result[assign_source(source_id, seed, train, validation)].extend(source_records)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", default="ignis-v1")
    args = parser.parse_args()
    records = json.loads(args.records.read_text(encoding="utf-8"))
    split = split_records(records, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(split, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

