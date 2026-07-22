#!/usr/bin/env python3
"""Verify committed runtime artifacts using only the Python standard library."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "web/public/data"
SOURCE = ROOT / "data/combined/data_04.csv"
EXPECTED_SOURCE_SHA256 = "4093e523e84c9908aed438a637fda1aaebecdc439fca8bbd5540688dfa4eda13"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Artifact verification failed: {message}")


def main() -> None:
    require(sha256(SOURCE) == EXPECTED_SOURCE_SHA256, "frozen data_04.csv checksum changed")
    pointer = json.loads((DATA_ROOT / "current.json").read_text(encoding="utf-8"))
    dataset_id = pointer.get("dataset_id", "")
    require(len(dataset_id) == 12, "current.json has an invalid dataset ID")
    dataset = DATA_ROOT / dataset_id
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["dataset_id"] == dataset_id, "pointer and manifest dataset IDs differ")
    artifacts = manifest["artifacts"]
    expected_paths = {entry["path"] for entry in artifacts}
    actual_paths = {str(path.relative_to(dataset)) for path in dataset.rglob("*") if path.is_file() and path.name != "manifest.json"}
    require(actual_paths == expected_paths, "artifact file set differs from the manifest")
    for entry in artifacts:
        path = dataset / entry["path"]
        require(path.stat().st_size == entry["bytes"], f"size mismatch for {entry['path']}")
        require(sha256(path) == entry["sha256"], f"hash mismatch for {entry['path']}")
    artifact_set_sha = hashlib.sha256(canonical_json(artifacts)).hexdigest()
    require(artifact_set_sha == manifest["artifact_set_sha256"], "artifact-set hash mismatch")
    require(artifact_set_sha[:12] == dataset_id, "dataset ID is not derived from the artifact-set hash")
    by_path = {entry["path"]: entry["bytes"] for entry in artifacts}
    county_sizes = [size for path, size in by_path.items() if path.startswith("counties/")]
    require(by_path["states.geojson"] <= 800_000, "states.geojson exceeds 800 KB")
    require(sum(county_sizes) <= 3_100_000, "county partitions exceed 3.1 MB")
    require(max(county_sizes) <= 400_000, "largest county partition exceeds 400 KB")
    require(by_path["metrics.json"] <= 150_000, "metrics.json exceeds 150 KB")
    metrics_text = (dataset / "metrics.json").read_text(encoding="utf-8")
    require("dollars" not in metrics_text.lower(), "browser metrics contain dollar-valued fields")
    print(f"Verified dataset {dataset_id}: {manifest['coverage']['published_counties']} counties, {sum(by_path.values()):,} bytes")


if __name__ == "__main__":
    main()
