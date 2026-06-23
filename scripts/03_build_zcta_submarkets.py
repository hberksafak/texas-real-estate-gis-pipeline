"""
Build analyst-defined ZCTA-based DFW submarket proxy polygons.

This workflow uses the Census-derived DFW ZCTA and CBSA layers from Milestone 3
to create deterministic directional sector submarkets for portfolio
demonstration. These are not official commercial, brokerage, government, or
regulatory submarket boundaries.
"""

from __future__ import annotations

import importlib.util
import math
import re
from pathlib import Path
from types import ModuleType

import geopandas as gpd
import pandas as pd
from shapely.geometry.base import BaseGeometry


CENTRAL_CORE_RADIUS_M = 25_000
DEFINITION_METHOD = "centroid_direction_sector_proxy"
SOURCE_NOTE = (
    "Analyst-defined ZCTA sector proxy for portfolio demonstration; not an "
    "official commercial, brokerage, government, or regulatory submarket boundary."
)

PREFERRED_ZCTA_FIELDS = (
    "ZCTA5CE20",
    "GEOID20",
    "ZCTA5CE",
    "GEOID",
    "ZCTA",
    "ZIP",
    "ZIP_CODE",
)

SUBMARKET_ORDER = {
    "DFW Central Core": "dfw_central_core",
    "North DFW": "north_dfw",
    "Northeast DFW": "northeast_dfw",
    "East DFW": "east_dfw",
    "Southeast DFW": "southeast_dfw",
    "South DFW": "south_dfw",
    "Southwest DFW": "southwest_dfw",
    "West DFW": "west_dfw",
    "Northwest DFW": "northwest_dfw",
}


def load_config() -> ModuleType:
    """Load constants from 00_config.py, whose filename is not importable."""
    config_path = Path(__file__).with_name("00_config.py")
    spec = importlib.util.spec_from_file_location("pipeline_config", config_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load config from {config_path}")

    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    return config


config = load_config()


def validate_inputs() -> None:
    """Confirm the Milestone 3 Census-derived inputs exist."""
    missing = [
        str(path)
        for path in (config.DFW_ZCTAS_GEOJSON, config.DFW_CBSA_GEOJSON)
        if not path.exists()
    ]
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Milestone 4 requires existing Census-derived study area inputs. "
            "Run `python3 scripts/01_prepare_sources.py` first.\n"
            f"Missing files:\n{missing_text}"
        )


def to_project_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure a GeoDataFrame is in the platform export CRS."""
    if gdf.crs is None:
        return gdf.set_crs(config.PROJECT_CRS)
    if str(gdf.crs).upper() != config.PROJECT_CRS:
        return gdf.to_crs(config.PROJECT_CRS)
    return gdf


def repair_geometry(geometry: BaseGeometry | None) -> BaseGeometry | None:
    """Repair invalid geometries with make_valid when available, then buffer(0)."""
    if geometry is None or geometry.is_empty:
        return geometry
    if geometry.is_valid:
        return geometry

    try:
        from shapely import make_valid

        repaired = make_valid(geometry)
    except ImportError:
        try:
            from shapely.validation import make_valid

            repaired = make_valid(geometry)
        except ImportError:
            repaired = geometry.buffer(0)

    if repaired is not None and not repaired.is_empty and not repaired.is_valid:
        repaired = repaired.buffer(0)
    return repaired


def clean_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Repair invalid geometries and remove null or empty geometries."""
    cleaned = gdf.copy()
    cleaned["geometry"] = cleaned.geometry.apply(repair_geometry)
    cleaned = cleaned[cleaned.geometry.notna()]
    cleaned = cleaned[~cleaned.geometry.is_empty]
    return cleaned.reset_index(drop=True)


def detect_zcta_field(gdf: gpd.GeoDataFrame) -> str:
    """Find the best available ZCTA identifier field."""
    for field in PREFERRED_ZCTA_FIELDS:
        if field in gdf.columns:
            return field

    upper_lookup = {column.upper(): column for column in gdf.columns}
    for upper_name, original_name in upper_lookup.items():
        if upper_name.startswith("ZCTA") or "ZCTA5CE" in upper_name:
            return original_name

    for upper_name, original_name in upper_lookup.items():
        if "GEOID" in upper_name and "FQ" not in upper_name:
            return original_name

    raise ValueError(
        "Could not detect a ZCTA ID field. Expected one of: "
        f"{', '.join(PREFERRED_ZCTA_FIELDS)}."
    )


def normalize_zcta(value: object) -> str:
    """Normalize a source ZCTA value into a five-character Census ZCTA string."""
    text = str(value).strip()
    if "US" in text:
        text = text.rsplit("US", maxsplit=1)[-1]

    digits = re.sub(r"\D", "", text)
    if digits:
        return digits[-5:].zfill(5)
    return text


def standardize_zcta(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add a clean zcta field while preserving original Census ID fields."""
    zcta_field = detect_zcta_field(gdf)
    standardized = gdf.copy()
    standardized["zcta"] = standardized[zcta_field].apply(normalize_zcta)
    standardized = standardized[standardized["zcta"].astype(bool)]
    return standardized.reset_index(drop=True)


def sector_from_delta(dx: float, dy: float, distance_m: float) -> str:
    """Assign a directional sector label from centroid offsets."""
    if distance_m <= CENTRAL_CORE_RADIUS_M:
        return "DFW Central Core"

    angle = math.degrees(math.atan2(dy, dx))
    if -22.5 <= angle < 22.5:
        return "East DFW"
    if 22.5 <= angle < 67.5:
        return "Northeast DFW"
    if 67.5 <= angle < 112.5:
        return "North DFW"
    if 112.5 <= angle < 157.5:
        return "Northwest DFW"
    if angle >= 157.5 or angle < -157.5:
        return "West DFW"
    if -157.5 <= angle < -112.5:
        return "Southwest DFW"
    if -112.5 <= angle < -67.5:
        return "South DFW"
    return "Southeast DFW"


def build_definition(zctas: gpd.GeoDataFrame, dfw_cbsa: gpd.GeoDataFrame) -> pd.DataFrame:
    """Create deterministic analyst-defined sector assignments for each ZCTA."""
    zctas_analysis = zctas.to_crs(config.ANALYSIS_CRS)
    cbsa_analysis = dfw_cbsa.to_crs(config.ANALYSIS_CRS)
    cbsa_union = (
        cbsa_analysis.geometry.union_all()
        if hasattr(cbsa_analysis.geometry, "union_all")
        else cbsa_analysis.geometry.unary_union
    )
    cbsa_centroid = cbsa_union.centroid

    records = []
    for _, row in zctas_analysis.iterrows():
        centroid = row.geometry.centroid
        dx = centroid.x - cbsa_centroid.x
        dy = centroid.y - cbsa_centroid.y
        distance_m = math.hypot(dx, dy)
        submarket_name = sector_from_delta(dx, dy, distance_m)
        records.append(
            {
                "zcta": row["zcta"],
                "submarket_id": SUBMARKET_ORDER[submarket_name],
                "submarket_name": submarket_name,
                "definition_method": DEFINITION_METHOD,
                "is_official_submarket": False,
                "source_note": SOURCE_NOTE,
            }
        )

    definition = pd.DataFrame(records).sort_values("zcta").reset_index(drop=True)
    return definition


def load_or_create_definition(
    zctas: gpd.GeoDataFrame,
    dfw_cbsa: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Read an existing definition CSV or create a deterministic new one."""
    required_columns = {
        "zcta",
        "submarket_id",
        "submarket_name",
        "definition_method",
        "is_official_submarket",
        "source_note",
    }

    if config.SUBMARKET_DEFINITION_CSV.exists():
        definition = pd.read_csv(
            config.SUBMARKET_DEFINITION_CSV,
            dtype={"zcta": str},
        )
        missing = required_columns.difference(definition.columns)
        if missing:
            raise ValueError(
                f"Existing definition CSV is missing columns: {sorted(missing)}"
            )
        print(f"Using existing submarket definition: {config.SUBMARKET_DEFINITION_CSV}")
        return definition

    definition = build_definition(zctas, dfw_cbsa)
    config.SUBMARKET_DEFINITION_CSV.parent.mkdir(parents=True, exist_ok=True)
    definition.to_csv(config.SUBMARKET_DEFINITION_CSV, index=False)
    print(f"Generated submarket definition: {config.SUBMARKET_DEFINITION_CSV}")
    return definition


def build_submarkets(
    zctas: gpd.GeoDataFrame,
    definition: pd.DataFrame,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame]:
    """Join, dissolve, and summarize ZCTA sector proxy submarkets."""
    definition = definition.copy()
    definition["zcta"] = definition["zcta"].apply(normalize_zcta)

    zctas_with_submarkets = zctas.merge(definition, on="zcta", how="left", validate="m:1")
    missing_definition = zctas_with_submarkets[
        zctas_with_submarkets["submarket_id"].isna()
    ]["zcta"].tolist()
    if missing_definition:
        raise ValueError(
            "Submarket definition is missing ZCTAs: "
            + ", ".join(sorted(missing_definition))
        )

    zctas_analysis = zctas_with_submarkets.to_crs(config.ANALYSIS_CRS)
    grouping_fields = ["submarket_id", "submarket_name"]

    grouped = (
        zctas_analysis.groupby(grouping_fields)
        .agg(
            zcta_count=("zcta", "nunique"),
            zcta_list=("zcta", lambda values: ";".join(sorted(set(values)))),
            definition_method=("definition_method", "first"),
            is_official_submarket=("is_official_submarket", "first"),
            source_note=("source_note", "first"),
        )
        .reset_index()
    )

    submarkets = zctas_analysis.dissolve(by=grouping_fields, as_index=False)[
        grouping_fields + ["geometry"]
    ]
    submarkets = submarkets.merge(grouped, on=grouping_fields, how="left")
    submarkets["total_area_sq_km"] = (submarkets.geometry.area / 1_000_000).round(3)

    ordered_columns = [
        "submarket_id",
        "submarket_name",
        "zcta_count",
        "zcta_list",
        "total_area_sq_km",
        "definition_method",
        "is_official_submarket",
        "source_note",
        "geometry",
    ]
    submarkets = submarkets[ordered_columns].to_crs(config.PROJECT_CRS)
    zctas_with_submarkets = zctas_with_submarkets.to_crs(config.PROJECT_CRS)

    summary = submarkets.drop(columns="geometry").copy()
    summary = summary[
        [
            "submarket_id",
            "submarket_name",
            "zcta_count",
            "total_area_sq_km",
            "zcta_list",
            "definition_method",
            "is_official_submarket",
        ]
    ].sort_values("submarket_id")

    return zctas_with_submarkets, submarkets, summary


def export_outputs(
    zctas_with_submarkets: gpd.GeoDataFrame,
    submarkets: gpd.GeoDataFrame,
    summary: pd.DataFrame,
) -> None:
    """Write platform GeoJSON, summary CSV, and GeoPackage outputs."""
    config.ensure_directories()

    submarkets.to_file(config.DFW_SUBMARKETS_GEOJSON, driver="GeoJSON", index=False)
    summary.to_csv(config.SUBMARKET_SUMMARY_CSV, index=False)

    if config.DFW_SUBMARKETS_GPKG.exists():
        config.DFW_SUBMARKETS_GPKG.unlink()

    zctas_with_submarkets.to_file(
        config.DFW_SUBMARKETS_GPKG,
        layer="dfw_zctas_with_submarkets",
        driver="GPKG",
        index=False,
    )
    submarkets.to_file(
        config.DFW_SUBMARKETS_GPKG,
        layer="dfw_zcta_submarkets",
        driver="GPKG",
        index=False,
    )


def main() -> None:
    """Run the ZCTA-based DFW submarket proxy builder."""
    config.ensure_directories()
    validate_inputs()

    zctas = clean_geometries(to_project_crs(gpd.read_file(config.DFW_ZCTAS_GEOJSON)))
    dfw_cbsa = clean_geometries(to_project_crs(gpd.read_file(config.DFW_CBSA_GEOJSON)))
    zctas = standardize_zcta(zctas)

    definition = load_or_create_definition(zctas, dfw_cbsa)
    zctas_with_submarkets, submarkets, summary = build_submarkets(zctas, definition)
    export_outputs(zctas_with_submarkets, submarkets, summary)

    print(f"Input ZCTA feature count: {len(zctas)}")
    print(f"Submarket definition path: {config.SUBMARKET_DEFINITION_CSV}")
    print(f"Number of submarkets: {len(submarkets)}")
    print(f"Output GeoJSON path: {config.DFW_SUBMARKETS_GEOJSON}")
    print(f"Output summary CSV path: {config.SUBMARKET_SUMMARY_CSV}")
    print(f"Output GeoPackage path: {config.DFW_SUBMARKETS_GPKG}")


if __name__ == "__main__":
    main()
