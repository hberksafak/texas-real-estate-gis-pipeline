"""
Build the platform-ready GeoJSON export package.

This workflow packages key project layers into normalized EPSG:4326 GeoJSON
files, a manifest CSV, an export summary CSV, and a GeoPackage with matching
layers.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import geopandas as gpd
import pandas as pd
from shapely.geometry.base import BaseGeometry


EXPORT_NOTE = (
    "Platform-ready GeoJSON package in EPSG:4326. Candidate layers are "
    "analyst-defined grid proxy polygons, not official parcels. Opportunity "
    "Zones are policy/incentive context only. School districts are neutral "
    "context overlays only."
)

EXPORT_LAYER_SPECS = [
    ("dallas_county_boundary", "boundary", "DALLAS_COUNTY_GEOJSON"),
    ("dfw_cbsa_boundary", "boundary", "DFW_CBSA_GEOJSON"),
    ("dfw_zctas", "boundary", "DFW_ZCTAS_GEOJSON"),
    ("dfw_zcta_submarkets", "submarket", "DFW_SUBMARKETS_GEOJSON"),
    ("dfw_opportunity_zones", "incentive_context", "DFW_OPPORTUNITY_ZONES_GEOJSON"),
    ("dfw_school_districts", "education_context", "DFW_SCHOOL_DISTRICTS_GEOJSON"),
    (
        "parcel_screening_candidates",
        "candidate_screening",
        "PARCEL_SCREENING_CANDIDATES_GEOJSON",
    ),
    ("qualified_candidate_sites", "candidate_screening", "QUALIFIED_CANDIDATES_GEOJSON"),
    (
        "disqualified_candidate_sites",
        "candidate_screening",
        "DISQUALIFIED_CANDIDATES_GEOJSON",
    ),
    ("ranked_site_candidates", "candidate_ranking", "RANKED_SITE_CANDIDATES_GEOJSON"),
    ("top_25_candidate_sites", "candidate_ranking", "TOP_25_CANDIDATE_SITES_GEOJSON"),
]


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


def snake_case(value: object) -> str:
    """Convert field names to lowercase snake_case."""
    text = str(value).strip()
    text = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[^0-9A-Za-z]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_").lower()
    return text or "field"


def unique_column_names(columns: list[str]) -> list[str]:
    """Normalize column names while preserving uniqueness."""
    counts: dict[str, int] = {}
    unique_names = []
    for column in columns:
        base_name = snake_case(column)
        count = counts.get(base_name, 0)
        unique_names.append(base_name if count == 0 else f"{base_name}_{count + 1}")
        counts[base_name] = count + 1
    return unique_names


def load_export_layer(layer_name: str, input_path: Path) -> gpd.GeoDataFrame:
    """Read one export layer from disk."""
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input for {layer_name}: {input_path}")
    return gpd.read_file(input_path)


def normalize_platform_fields(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Normalize non-geometry fields to platform-friendly snake_case."""
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
    return normalized.set_geometry(geometry_column)


def ensure_project_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Standardize a layer to EPSG:4326 for platform exports."""
    if gdf.crs is None:
        return gdf.set_crs(config.PROJECT_CRS)
    if str(gdf.crs).upper() != config.PROJECT_CRS:
        return gdf.to_crs(config.PROJECT_CRS)
    return gdf


def repair_geometry(geometry: BaseGeometry | None) -> BaseGeometry | None:
    """Repair invalid geometry with make_valid when available, then buffer(0)."""
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
    """Repair invalid geometries where possible."""
    repaired = gdf.copy()
    repaired["geometry"] = repaired.geometry.apply(repair_geometry)
    return repaired.set_geometry("geometry")


def remove_empty_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Remove null and empty geometry records."""
    cleaned = gdf[gdf.geometry.notna()].copy()
    cleaned = cleaned[~cleaned.geometry.is_empty].copy()
    return cleaned.reset_index(drop=True)


def calculate_layer_area_sq_km(gdf: gpd.GeoDataFrame) -> float:
    """Calculate total layer area in square kilometers using EPSG:32138."""
    if gdf.empty:
        return 0.0
    analysis_gdf = gdf.to_crs(config.ANALYSIS_CRS)
    return round(float(analysis_gdf.geometry.area.sum() / 1_000_000), 3)


def geometry_types(gdf: gpd.GeoDataFrame) -> str:
    """Return sorted geometry type names for a layer."""
    if gdf.empty:
        return ""
    return ";".join(sorted(gdf.geometry.geom_type.dropna().unique()))


def export_platform_geojson(gdf: gpd.GeoDataFrame, output_path: Path) -> Path:
    """Export one platform-ready GeoJSON layer."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_crs(config.PROJECT_CRS).to_file(output_path, driver="GeoJSON", index=False)
    return output_path


def file_size_mb(path: Path) -> float:
    """Return file size in megabytes."""
    if not path.exists():
        return 0.0
    return round(path.stat().st_size / (1024 * 1024), 3)


def build_manifest_row(
    layer_name: str,
    category: str,
    input_path: Path,
    output_geojson_path: Path,
    gdf: gpd.GeoDataFrame,
) -> dict[str, object]:
    """Build one manifest row for an exported platform layer."""
    return {
        "layer_name": layer_name,
        "category": category,
        "input_path": str(input_path),
        "output_geojson_path": str(output_geojson_path),
        "gpkg_layer_name": layer_name,
        "feature_count": int(len(gdf)),
        "geometry_types": geometry_types(gdf),
        "crs": str(gdf.crs),
        "total_area_sq_km": calculate_layer_area_sq_km(gdf),
        "file_size_mb": file_size_mb(output_geojson_path),
        "status": "exported",
        "notes": EXPORT_NOTE,
    }


def write_manifest(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Write the platform layers manifest CSV."""
    manifest = pd.DataFrame(rows)
    manifest.to_csv(config.PLATFORM_LAYERS_MANIFEST_CSV, index=False)
    return manifest


def write_export_summary(
    total_layers_expected: int,
    total_layers_exported: int,
    total_layers_missing: int,
    total_features_exported: int,
    total_geojson_size_mb: float,
) -> pd.DataFrame:
    """Write the one-row platform export summary CSV."""
    status = "complete" if total_layers_missing == 0 else "partial"
    summary = pd.DataFrame(
        [
            {
                "total_layers_expected": total_layers_expected,
                "total_layers_exported": total_layers_exported,
                "total_layers_missing": total_layers_missing,
                "total_features_exported": total_features_exported,
                "total_geojson_size_mb": round(total_geojson_size_mb, 3),
                "export_crs": config.PROJECT_CRS,
                "export_package_status": status,
                "export_note": EXPORT_NOTE,
            }
        ]
    )
    summary.to_csv(config.PLATFORM_EXPORT_SUMMARY_CSV, index=False)
    return summary


def export_gpkg(layers: dict[str, gpd.GeoDataFrame]) -> None:
    """Export all platform-ready layers to one GeoPackage."""
    if config.EXPORT_READY_LAYERS_GPKG.exists():
        config.EXPORT_READY_LAYERS_GPKG.unlink()

    for layer_name, gdf in layers.items():
        gdf.to_crs(config.PROJECT_CRS).to_file(
            config.EXPORT_READY_LAYERS_GPKG,
            layer=layer_name,
            driver="GPKG",
            index=False,
        )


def prepare_layer(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Normalize, repair, remove empties, and standardize CRS."""
    prepared = ensure_project_crs(gdf)
    prepared = normalize_platform_fields(prepared)
    prepared = repair_geometries(prepared)
    prepared = remove_empty_geometries(prepared)
    return ensure_project_crs(prepared)


def main() -> None:
    """Run the final platform GeoJSON export package workflow."""
    config.ensure_directories()

    manifest_rows = []
    exported_layers: dict[str, gpd.GeoDataFrame] = {}
    missing_layers = []

    for layer_name, category, config_attr in EXPORT_LAYER_SPECS:
        input_path = getattr(config, config_attr)
        if not input_path.exists():
            missing_layers.append(layer_name)
            print(f"Missing layer skipped: {layer_name} ({input_path})")
            continue

        raw_gdf = load_export_layer(layer_name, input_path)
        platform_gdf = prepare_layer(raw_gdf)
        output_path = config.PLATFORM_EXPORT_GEOJSON_DIR / f"{layer_name}.geojson"
        export_platform_geojson(platform_gdf, output_path)

        exported_layers[layer_name] = platform_gdf
        manifest_rows.append(
            build_manifest_row(
                layer_name=layer_name,
                category=category,
                input_path=input_path,
                output_geojson_path=output_path,
                gdf=platform_gdf,
            )
        )

    manifest = write_manifest(manifest_rows)
    total_geojson_size_mb = float(manifest["file_size_mb"].sum()) if not manifest.empty else 0.0
    total_features_exported = int(manifest["feature_count"].sum()) if not manifest.empty else 0
    summary = write_export_summary(
        total_layers_expected=len(EXPORT_LAYER_SPECS),
        total_layers_exported=len(exported_layers),
        total_layers_missing=len(missing_layers),
        total_features_exported=total_features_exported,
        total_geojson_size_mb=total_geojson_size_mb,
    )
    export_gpkg(exported_layers)

    exported_layer_names = list(exported_layers.keys())
    print(f"Total expected layers: {len(EXPORT_LAYER_SPECS)}")
    print(f"Exported layer count: {len(exported_layers)}")
    print(f"Missing layer count: {len(missing_layers)}")
    print("Exported layer names:")
    for layer_name in exported_layer_names:
        print(f"- {layer_name}")
    print(f"Manifest CSV path: {config.PLATFORM_LAYERS_MANIFEST_CSV}")
    print(f"Export summary CSV path: {config.PLATFORM_EXPORT_SUMMARY_CSV}")
    print(f"GeoPackage path: {config.EXPORT_READY_LAYERS_GPKG}")
    print(f"Platform export GeoJSON folder: {config.PLATFORM_EXPORT_GEOJSON_DIR}")
    print(
        "Export package status: "
        f"{summary.loc[0, 'export_package_status']} "
        f"({summary.loc[0, 'total_features_exported']} features)"
    )


if __name__ == "__main__":
    main()
