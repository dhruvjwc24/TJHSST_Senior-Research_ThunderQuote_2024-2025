#!/usr/bin/env python3
"""Package the frozen synthetic research dataset into browser-safe artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = ROOT / "data/combined/data_04.csv"
STATE_SHP = ROOT / "data/gui/states/cb_2018_us_state_500k.shp"
COUNTY_SHP = ROOT / "data/gui/counties/cb_2018_us_county_500k.shp"
CROSSWALK_CSV = ROOT / "data/mappings/county_crosswalk.csv"
EXPECTED_SOURCE_SHA256 = "4093e523e84c9908aed438a637fda1aaebecdc439fca8bbd5540688dfa4eda13"
SCHEMA_VERSION = "1.0.0"
FORMULA_VERSION = "scenario-index-v1"
YEARS = 44
TOLERANCE = 0.01
REQUIRED_COLUMNS = {
    "Year",
    "State",
    "County",
    "Claims Paid",
    "Dollars Paid",
    "Total Storms",
}


class BuildError(RuntimeError):
    """Raised when a source or generated artifact violates the release contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def source_commit_metadata() -> dict[str, str]:
    def git_value(fmt: str) -> str:
        result = subprocess.run(
            ["git", "log", "-1", f"--format={fmt}", "--", str(SOURCE_CSV.relative_to(ROOT))],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    try:
        return {"commit": git_value("%H"), "committed_at": git_value("%cI")}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": "unknown", "committed_at": "unknown"}


def load_crosswalk() -> dict[tuple[str, str], dict[str, str]]:
    with CROSSWALK_CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"source_state", "source_county", "canonical_geoid", "resolution", "note"}
    if not rows or not required.issubset(rows[0]):
        raise BuildError("county_crosswalk.csv is empty or missing required columns")
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["source_state"].strip(), row["source_county"].strip())
        if key in result:
            raise BuildError(f"duplicate crosswalk source key: {key}")
        if row["resolution"] not in {"alias", "withhold"}:
            raise BuildError(f"unsupported crosswalk resolution for {key}: {row['resolution']}")
        if row["resolution"] == "alias" and len(row["canonical_geoid"]) != 5:
            raise BuildError(f"alias must contain a five-digit GEOID: {key}")
        result[key] = row
    return result


def validate_source(frame: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise BuildError(f"data_04.csv is missing columns: {', '.join(sorted(missing))}")
    if sha256_file(SOURCE_CSV) != EXPECTED_SOURCE_SHA256:
        raise BuildError("data_04.csv checksum changed; review and version the frozen source before building")
    if frame[["Year", "State", "County"]].duplicated().any():
        raise BuildError("data_04.csv contains duplicate year/state/county rows")
    if frame["Year"].min() != 1980 or frame["Year"].max() != 2023:
        raise BuildError("data_04.csv must cover 1980 through 2023")
    for column in ("Claims Paid", "Dollars Paid", "Total Storms"):
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.isna().any() or (~numeric.map(math.isfinite)).any() or (numeric < 0).any():
            raise BuildError(f"{column} must contain only finite nonnegative values")


def clean_geography(frame: gpd.GeoDataFrame, fields: list[str]) -> gpd.GeoDataFrame:
    if frame.crs is None:
        raise BuildError("source geography has no coordinate reference system")
    frame = frame.to_crs(4326).copy()
    frame["geometry"] = frame.geometry.simplify(TOLERANCE, preserve_topology=True)
    if frame.geometry.is_empty.any() or frame.geometry.isna().any() or (~frame.geometry.is_valid).any():
        raise BuildError("simplified geography contains empty or invalid geometry")
    return frame[fields + ["geometry"]].sort_values(fields[0]).reset_index(drop=True)


def dataframe_geojson(frame: gpd.GeoDataFrame, property_map: dict[str, str]) -> dict[str, Any]:
    features = []
    for row in frame.itertuples(index=False):
        properties = {public: str(getattr(row, source)) for source, public in property_map.items()}
        geometry = json.loads(gpd.GeoSeries([row.geometry], crs=4326).to_json())["features"][0]["geometry"]
        features.append({"type": "Feature", "id": properties.get("geoid", properties.get("state_fips")), "properties": properties, "geometry": geometry})
    return {"type": "FeatureCollection", "features": features}


def build(output_root: Path) -> dict[str, Any]:
    if output_root.exists() and not (output_root / "current.json").is_file():
        raise BuildError(
            f"refusing to replace non-artifact directory: {output_root}"
        )
    source = pd.read_csv(SOURCE_CSV)
    validate_source(source)
    crosswalk = load_crosswalk()
    states_raw = gpd.read_file(STATE_SHP)
    counties_raw = gpd.read_file(COUNTY_SHP)
    for field in ("STATEFP", "GEOID", "NAME", "LSAD"):
        if field not in counties_raw:
            raise BuildError(f"county shapefile is missing {field}")
    for field in ("STATEFP", "NAME", "STUSPS"):
        if field not in states_raw:
            raise BuildError(f"state shapefile is missing {field}")

    source_states = sorted(source["State"].unique())
    state_rows = states_raw[states_raw["NAME"].isin(source_states)].copy()
    if len(state_rows) != 50:
        raise BuildError(f"expected geography for 50 source states, found {len(state_rows)}")
    state_name_to_fips = dict(zip(state_rows["NAME"], state_rows["STATEFP"], strict=True))
    counties = counties_raw[counties_raw["STATEFP"].isin(state_name_to_fips.values())].copy()
    county_by_geoid = counties.set_index("GEOID", drop=False)
    county_candidates: dict[tuple[str, str], list[str]] = {}
    for row in counties.itertuples(index=False):
        state_name = next(name for name, fips in state_name_to_fips.items() if fips == row.STATEFP)
        county_candidates.setdefault((state_name, row.NAME), []).append(row.GEOID)

    aggregates = source.groupby(["State", "County"], sort=True, as_index=False)[["Claims Paid", "Total Storms"]].sum()
    resolved: list[dict[str, Any]] = []
    join_rows: list[dict[str, str]] = []
    used_geoids: set[str] = set()
    reviewed_keys: set[tuple[str, str]] = set()
    for _, row in aggregates.iterrows():
        key = (str(row["State"]), str(row["County"]))
        disposition = crosswalk.get(key)
        if disposition:
            reviewed_keys.add(key)
            if disposition["resolution"] == "withhold":
                join_rows.append({"source_state": key[0], "source_county": key[1], "status": "withheld", "geoid": "", "note": disposition["note"]})
                continue
            candidates = [disposition["canonical_geoid"]]
            status = "alias"
        else:
            candidates = county_candidates.get(key, [])
            status = "direct"
        if len(candidates) != 1:
            raise BuildError(f"unreviewed county join has {len(candidates)} matches: {key}")
        geoid = candidates[0]
        if geoid not in county_by_geoid.index:
            raise BuildError(f"crosswalk target is absent from geography: {key} -> {geoid}")
        if geoid in used_geoids:
            raise BuildError(f"multiple source keys resolve to GEOID {geoid}")
        used_geoids.add(geoid)
        geo = county_by_geoid.loc[geoid]
        resolved.append({
            "geoid": geoid,
            "state_fips": str(geo["STATEFP"]),
            "state": str(row["State"]),
            "county": str(geo["NAME"]),
            "claims": float(row["Claims Paid"]),
            "storms": float(row["Total Storms"]),
        })
        join_rows.append({"source_state": key[0], "source_county": key[1], "status": status, "geoid": geoid, "note": disposition["note"] if disposition else ""})
    unused_crosswalk = set(crosswalk) - reviewed_keys
    if unused_crosswalk:
        raise BuildError(f"crosswalk entries do not exist in source data: {sorted(unused_crosswalk)}")

    median_claims_rate = statistics.median(item["claims"] / YEARS for item in resolved)
    median_storms_rate = statistics.median(item["storms"] / YEARS for item in resolved)
    if median_claims_rate <= 0 or median_storms_rate <= 0:
        raise BuildError("reference medians must be positive")
    for item in resolved:
        claims_rate = item.pop("claims") / YEARS
        storms_rate = item.pop("storms") / YEARS
        item["claims_per_year"] = round(claims_rate, 6)
        item["storms_per_year"] = round(storms_rate, 6)
        item["base_index"] = round(100 * (0.6 * claims_rate / median_claims_rate + 0.4 * storms_rate / median_storms_rate), 6)
    resolved.sort(key=lambda item: item["geoid"])

    state_index: dict[str, float] = {}
    for state_fips in sorted(state_name_to_fips.values()):
        values = [item["base_index"] for item in resolved if item["state_fips"] == state_fips]
        state_index[state_fips] = round(statistics.median(values), 6) if values else 0.0

    state_geo = clean_geography(state_rows, ["STATEFP", "NAME", "STUSPS"])
    county_geo = clean_geography(counties, ["GEOID", "STATEFP", "NAME", "LSAD"])
    stage_parent = output_root.parent
    stage_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="runtime-data-", dir=stage_parent) as temp_name:
        temp = Path(temp_name)
        data_dir = temp / "dataset"
        write_json(data_dir / "states.geojson", dataframe_geojson(state_geo, {"STATEFP": "state_fips", "NAME": "name", "STUSPS": "abbreviation"}))
        for state_fips, group in county_geo.groupby("STATEFP", sort=True):
            write_json(data_dir / "counties" / f"{state_fips}.geojson", dataframe_geojson(group, {"GEOID": "geoid", "STATEFP": "state_fips", "NAME": "name", "LSAD": "lsad"}))
        formula = {
            "version": FORMULA_VERSION,
            "description": "Dimensionless synthetic scenario index; not a probability, prediction, price, or quote.",
            "base": {"claims_weight": 0.6, "storms_weight": 0.4, "median_claims_per_year": median_claims_rate, "median_storms_per_year": median_storms_rate, "years": YEARS},
            "defaults": {"year_built": 1982, "stories": "2", "square_feet": 2200, "primary_residence": "yes", "roof_age": 6},
            "bounds": {"year_built": [1900, 2026], "square_feet": [200, 20000], "roof_age": [0, 100]},
            "factors": {
                "year_built_per_year_from_1982": -0.005,
                "stories": {"1": 0.9, "2": 1.0, "3+": 1.1},
                "square_feet_per_foot_from_2200": 0.0001,
                "primary_residence": {"yes": 1.0, "no": 0.95},
                "roof_age_per_year_from_6": 0.01,
                "protective_device_each": 0.975,
            },
            "rounding": "half-away-from-zero to one decimal place",
        }
        write_json(data_dir / "formula.json", formula)
        compact_metrics = [
            [item["geoid"], item["base_index"], item["claims_per_year"], item["storms_per_year"]]
            for item in resolved
        ]
        write_json(
            data_dir / "metrics.json",
            {
                "schema_version": SCHEMA_VERSION,
                "county_columns": ["geoid", "base_index", "generated_claims_per_year", "generated_storms_per_year"],
                "states": state_index,
                "counties": compact_metrics,
            },
        )
        write_json(data_dir / "join-report.json", {"source_keys": len(aggregates), "published_keys": len(resolved), "aliases": sum(row["status"] == "alias" for row in join_rows), "withheld": sum(row["status"] == "withheld" for row in join_rows), "rows": join_rows})

        artifact_paths = sorted(path for path in data_dir.rglob("*") if path.is_file())
        artifacts = [{"path": str(path.relative_to(data_dir)), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in artifact_paths]
        artifact_set_sha = hashlib.sha256(canonical_json(artifacts)).hexdigest()
        dataset_id = artifact_set_sha[:12]
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "dataset_id": dataset_id,
            "artifact_set_sha256": artifact_set_sha,
            "source_set_sha256": EXPECTED_SOURCE_SHA256,
            "source_commit": source_commit_metadata(),
            "data_period": {"start": 1980, "end": 2023},
            "formula_version": FORMULA_VERSION,
            "coverage": {"states": 50, "published_counties": len(resolved), "withheld_source_keys": sum(row["status"] == "withheld" for row in join_rows)},
            "artifacts": artifacts,
        }
        write_json(data_dir / "manifest.json", manifest)
        final_parent = temp / "final"
        shutil.copytree(data_dir, final_parent / dataset_id)
        write_json(final_parent / "current.json", {"dataset_id": dataset_id, "manifest": f"/data/{dataset_id}/manifest.json"})
        backup = output_root.with_name(f".{output_root.name}.previous")
        if backup.exists():
            raise BuildError(f"stale artifact backup must be removed manually: {backup}")
        if output_root.exists():
            os.replace(output_root, backup)
        try:
            os.replace(final_parent, output_root)
        except BaseException:
            if backup.exists() and not output_root.exists():
                os.replace(backup, output_root)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "web/public/data")
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    print(f"Built dataset {manifest['dataset_id']} with {manifest['coverage']['published_counties']} county records")


if __name__ == "__main__":
    main()
