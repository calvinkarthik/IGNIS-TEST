from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate_split(split: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    required = {"train", "validation", "test"}
    if set(split) != required:
        raise ValueError("split must contain train, validation, and test")
    sources: dict[str, str] = {}
    paths: set[str] = set()
    for partition, records in split.items():
        for record in records:
            source = str(record.get("source_id", ""))
            path = str(record.get("path", ""))
            if not source or not path:
                raise ValueError("every record requires source_id and path")
            previous = sources.setdefault(source, partition)
            if previous != partition:
                raise ValueError(f"source leakage: {source} appears in {previous} and {partition}")
            if path in paths:
                raise ValueError(f"duplicate sample path: {path}")
            paths.add(path)
    return {partition: len(records) for partition, records in split.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("split", type=Path)
    args = parser.parse_args()
    value = json.loads(args.split.read_text(encoding="utf-8"))
    print(json.dumps(validate_split(value), indent=2))


if __name__ == "__main__":
    main()

