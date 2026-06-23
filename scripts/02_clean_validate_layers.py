"""
Reusable GIS layer cleaning and validation workflow.

This script validates the existing Census-derived real estate GIS layers,
standardizes schemas and CRS values, repairs geometries, removes unusable
records, and exports a validation report plus a cleaned GeoPackage.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import geopandas as gpd
import pandas as pd
from shapely.geometry.base import BaseGeometry


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

INPUT_LAYERS = {
    "dallas_county_boundary": config.DALLAS_COUNTY_GEOJSON,
    "dfw_cbsa_boundary": config.DFW_CBSA_GEOJSON,
    "dfw_zctas": config.DFW_ZCTAS_GEOJSON,
    "dfw_zcta_submarkets": config.DFW_SUBMARKETS_GEOJSON,
}


def load_layer(path: Path) -> gpd.GeoDataFrame:
    """Read a GIS layer from disk with GeoPandas."""
    if not path.exists():
        raise FileNotFoundError(f"Input layer not found: {path}")
    return gpd.read_file(path)


def snake_case(value: object) -> str:
    """Convert a column name to lowercase snake_case."""
    text = str(value).strip()
    text = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[^0-9A-Za-z]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_").lower()
    return text or "field"


def unique_column_names(columns: list[str]) -> list[str]:
    """Ensure normalized column names remain unique."""
    counts: dict[str, int] = {}
    unique_names = []
    for column in columns:
        base_name = snake_case(column)
        count = counts.get(base_name, 0)
        unique_names.append(base_name if count == 0 else f"{base_name}_{count + 1}")
        counts[base_name] = count + 1
    return unique_names


def normalize_column_names(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Normalize non-geometry column names to lowercase snake_case."""
    normalized = gdf.copy()
    geometry_column = normalized.geometry.name
    rename_map = {
        column: normalized_name
        for column, normalized_name in zip(
            normalized.columns,
            unique_column_names(list(normalized.columns)),
        )
    }
    rename_map[geometry_column] = geometry_column
    normalized = normalized.rename(columns=rename_map)
    normalized = normalized.set_geometry(geometry_column)
    return normalized


def repair_geometry(geometry: BaseGeometry | None) -> BaseGeometry | None:
    """Repair a single invalid geometry with make_valid when available."""
    if geometry is None or geometry.is_empty or geometry.is_valid:
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


def repair_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Repair invalid geometries while preserving layer attributes."""
    repaired = gdf.copy()
    repaired["geometry"] = repaired.geometry.apply(repair_geometry)
    repaired = repaired.set_geometry("geometry")
    return repaired


def empty_geometry_count(gdf: gpd.GeoDataFrame) -> int:
    """Count null or empty geometries."""
    null_count = int(gdf.geometry.isna().sum())
    non_null = gdf.geometry[gdf.geometry.notna()]
    return null_count + int(non_null.is_empty.sum())


def invalid_geometry_count(gdf: gpd.GeoDataFrame) -> int:
    """Count invalid non-empty geometries."""
    non_empty = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    return int((~non_empty.geometry.is_valid).sum())


def remove_empty_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Remove rows with null or empty geometry."""
    cleaned = gdf[gdf.geometry.notna()].copy()
    cleaned = cleaned[~cleaned.geometry.is_empty].copy()
    return cleaned.reset_index(drop=True)


def remove_duplicate_geometries_or_records(
    gdf: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, int]:
    """Remove exact duplicate records, including exact geometry matches."""
    if gdf.empty:
        return gdf.copy(), 0

    working = gdf.copy()
    geometry_column = working.geometry.name
    working["_geometry_wkb"] = working.geometry.apply(
        lambda geometry: geometry.wkb_hex if geometry is not None else None
    )
    duplicate_columns = [
        column for column in working.columns if column != geometry_column
    ]
    before = len(working)
    working = working.drop_duplicates(subset=duplicate_columns)
    removed = before - len(working)
    cleaned = working.drop(columns="_geometry_wkb")
    return gpd.GeoDataFrame(cleaned, geometry=geometry_column, crs=gdf.crs), removed


def calculate_area_sq_km(gdf: gpd.GeoDataFrame) -> float:
    """Calculate total area in square kilometers using the analysis CRS."""
    if gdf.empty:
        return 0.0
    analysis_gdf = gdf.to_crs(config.ANALYSIS_CRS)
    return round(float(analysis_gdf.geometry.area.sum() / 1_000_000), 3)


def geometry_types(gdf: gpd.GeoDataFrame) -> str:
    """Return sorted geometry type names for a layer."""
    if gdf.empty:
        return ""
    return ";".join(sorted(gdf.geometry.geom_type.dropna().unique()))


def validate_layer(
    layer_name: str,
    input_path: Path,
) -> tuple[dict[str, object], gpd.GeoDataFrame | None]:
    """Clean one layer and return its validation report row plus cleaned data."""
    if not input_path.exists():
        row = {
            "layer_name": layer_name,
            "input_path": str(input_path),
            "feature_count_before": 0,
            "feature_count_after": 0,
            "crs_before": "",
            "crs_after": "",
            "geometry_types": "",
            "invalid_geometries_before": 0,
            "invalid_geometries_after": 0,
            "empty_geometries_before": 0,
            "empty_geometries_after": 0,
            "duplicate_rows_removed": 0,
            "total_area_sq_km": 0.0,
            "status": "failed",
            "notes": "Input file missing.",
        }
        return row, None

    gdf = load_layer(input_path)
    feature_count_before = int(len(gdf))
    crs_before = str(gdf.crs) if gdf.crs is not None else ""
    invalid_before = invalid_geometry_count(gdf)
    empty_before = empty_geometry_count(gdf)

    notes = []
    cleaned = gdf.copy()
    if cleaned.crs is None:
        cleaned = cleaned.set_crs(config.PROJECT_CRS)
        notes.append("Input CRS missing; assigned project CRS.")
    elif str(cleaned.crs).upper() != config.PROJECT_CRS:
        cleaned = cleaned.to_crs(config.PROJECT_CRS)
        notes.append("Converted CRS to project CRS.")

    cleaned = normalize_column_names(cleaned)
    cleaned = repair_geometries(cleaned)
    cleaned = remove_empty_geometries(cleaned)
    cleaned, duplicate_rows_removed = remove_duplicate_geometries_or_records(cleaned)
    cleaned = cleaned.to_crs(config.PROJECT_CRS)

    invalid_after = invalid_geometry_count(cleaned)
    empty_after = empty_geometry_count(cleaned)
    status = "passed" if invalid_after == 0 and empty_after == 0 else "warning"
    if duplicate_rows_removed:
        notes.append(f"Removed {duplicate_rows_removed} exact duplicate row(s).")
    if invalid_before:
        notes.append("Attempted invalid geometry repair.")
    if empty_before:
        notes.append("Removed empty/null geometries.")
    if not notes:
        notes.append("Layer validated without required repairs.")

    row = {
        "layer_name": layer_name,
        "input_path": str(input_path),
        "feature_count_before": feature_count_before,
        "feature_count_after": int(len(cleaned)),
        "crs_before": crs_before,
        "crs_after": str(cleaned.crs),
        "geometry_types": geometry_types(cleaned),
        "invalid_geometries_before": invalid_before,
        "invalid_geometries_after": invalid_after,
        "empty_geometries_before": empty_before,
        "empty_geometries_after": empty_after,
        "duplicate_rows_removed": duplicate_rows_removed,
        "total_area_sq_km": calculate_area_sq_km(cleaned),
        "status": status,
        "notes": " ".join(notes),
    }
    return row, cleaned


def write_validation_report(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Write validation report rows to the final CSV folder."""
    report = pd.DataFrame(rows)
    report.to_csv(config.VALIDATION_REPORT_CSV, index=False)
    return report


def export_validated_layers(layers: dict[str, gpd.GeoDataFrame]) -> None:
    """Export cleaned in-memory layers to one GeoPackage."""
    if config.VALIDATED_LAYERS_GPKG.exists():
        config.VALIDATED_LAYERS_GPKG.unlink()

    for layer_name, gdf in layers.items():
        gdf.to_crs(config.PROJECT_CRS).to_file(
            config.VALIDATED_LAYERS_GPKG,
            layer=layer_name,
            driver="GPKG",
            index=False,
        )


def main() -> None:
    """Run reusable validation over existing Census-derived GIS layers."""
    config.ensure_directories()

    report_rows = []
    validated_layers = {}
    for layer_name, input_path in INPUT_LAYERS.items():
        row, cleaned = validate_layer(layer_name, input_path)
        report_rows.append(row)
        if cleaned is not None:
            validated_layers[layer_name] = cleaned

        print(f"Layer: {layer_name}")
        print(
            "  Feature count before/after: "
            f"{row['feature_count_before']} / {row['feature_count_after']}"
        )
        print(
            "  Invalid geometries before/after: "
            f"{row['invalid_geometries_before']} / {row['invalid_geometries_after']}"
        )
        print(f"  Total area sq km: {row['total_area_sq_km']}")

    write_validation_report(report_rows)
    export_validated_layers(validated_layers)

    print(f"Final validation report path: {config.VALIDATION_REPORT_CSV}")
    print(f"Final GeoPackage path: {config.VALIDATED_LAYERS_GPKG}")


if __name__ == "__main__":
    main()
