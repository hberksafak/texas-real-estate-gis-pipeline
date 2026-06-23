"""
Build a platform-ready real estate GIS layer catalog for DFW.

This workflow packages existing Census-derived validated layers and optionally
adds two controlled public context layers: HUD Opportunity Zones and Texas
school district boundaries. It does not use parcel, flood, road, OSM, NCTCOG,
or Microsoft building footprint data.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType
from urllib.parse import urlparse

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry.base import BaseGeometry


HUD_OPPORTUNITY_ZONES_DOWNLOAD_URL = None
SCHOOL_DISTRICTS_DOWNLOAD_URL = None

SOURCE_NOTES = {
    "dfw_opportunity_zones": (
        "HUD Opportunity Zones are used only as policy/incentive business context, "
        "not demographic targeting."
    ),
    "dfw_school_districts": (
        "School districts are neutral context overlays only and are not ranking "
        "criteria or fair-housing-risk targeting inputs."
    ),
}

VECTOR_SUFFIXES = (".gpkg", ".geojson", ".json", ".shp", ".zip")


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
    """Convert a field name to lowercase snake_case."""
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


def normalize_column_names(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Normalize non-geometry columns to lowercase snake_case."""
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
    """Repair invalid geometries and remove null/empty geometries."""
    repaired = gdf.copy()
    repaired["geometry"] = repaired.geometry.apply(repair_geometry)
    repaired = repaired[repaired.geometry.notna()].copy()
    repaired = repaired[~repaired.geometry.is_empty].copy()
    return repaired.reset_index(drop=True)


def to_project_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Standardize a layer to the project platform CRS."""
    if gdf.crs is None:
        return gdf.set_crs(config.PROJECT_CRS)
    if str(gdf.crs).upper() != config.PROJECT_CRS:
        return gdf.to_crs(config.PROJECT_CRS)
    return gdf


def read_vector(path: Path, layer_name: str | None = None) -> gpd.GeoDataFrame:
    """Read a vector file, including ZIP-wrapped shapefiles when supported."""
    kwargs = {"layer": layer_name} if layer_name else {}
    try:
        return gpd.read_file(path, **kwargs)
    except Exception:
        if path.suffix.lower() == ".zip":
            return gpd.read_file(f"zip://{path}", **kwargs)
        raise


def load_boundary_layers() -> dict[str, gpd.GeoDataFrame]:
    """Load existing validated Census/submarket layers for catalog packaging."""
    layer_paths = {
        "dallas_county_boundary": config.DALLAS_COUNTY_GEOJSON,
        "dfw_cbsa_boundary": config.DFW_CBSA_GEOJSON,
        "dfw_zctas": config.DFW_ZCTAS_GEOJSON,
        "dfw_zcta_submarkets": config.DFW_SUBMARKETS_GEOJSON,
    }

    layers = {}
    for layer_name, geojson_path in layer_paths.items():
        if config.VALIDATED_LAYERS_GPKG.exists():
            try:
                gdf = read_vector(config.VALIDATED_LAYERS_GPKG, layer_name=layer_name)
            except Exception:
                gdf = read_vector(geojson_path)
        else:
            gdf = read_vector(geojson_path)

        layers[layer_name] = repair_geometries(
            normalize_column_names(to_project_crs(gdf))
        )
        print(f"Loaded existing layer: {layer_name}")

    return layers


def download_file_if_missing(url: str, output_path: Path) -> Path:
    """Download a file only if a stable direct URL has been configured."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        print(f"Skipped existing download: {output_path}")
        return output_path

    print(f"Downloading {url}")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with output_path.open("wb") as target_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    target_file.write(chunk)
    return output_path


def download_target_for_url(raw_dir: Path, url: str) -> Path:
    """Infer a local download target filename from a direct URL."""
    parsed = urlparse(url)
    filename = Path(parsed.path).name or "downloaded_layer"
    return raw_dir / filename


def find_vector_file(folder: Path) -> Path | None:
    """Find the first supported vector file in a raw source folder."""
    if not folder.exists():
        return None

    candidates = [
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in VECTOR_SUFFIXES
    ]
    suffix_rank = {suffix: index for index, suffix in enumerate(VECTOR_SUFFIXES)}
    candidates = sorted(
        candidates,
        key=lambda path: (suffix_rank.get(path.suffix.lower(), 99), str(path)),
    )
    return candidates[0] if candidates else None


def load_public_layer(
    layer_name: str,
    raw_dir: Path,
    optional_download_url: str | None = None,
) -> tuple[gpd.GeoDataFrame | None, str]:
    """Load an optional public context layer from download URL or manual file."""
    raw_dir.mkdir(parents=True, exist_ok=True)

    if optional_download_url:
        target_path = download_target_for_url(raw_dir, optional_download_url)
        download_file_if_missing(optional_download_url, target_path)

    vector_path = find_vector_file(raw_dir)
    if vector_path is None:
        message = (
            f"{layer_name} not available. Place an official .zip, .shp, .geojson, "
            f".json, or .gpkg file in {raw_dir} and rerun this script."
        )
        print(message)
        return None, message

    print(f"Loaded optional context layer from: {vector_path}")
    return read_vector(vector_path), f"Loaded from {vector_path}"


def clean_context_layer(gdf: gpd.GeoDataFrame, layer_name: str) -> gpd.GeoDataFrame:
    """Standardize CRS, fields, and geometry for an optional context layer."""
    cleaned = to_project_crs(gdf)
    cleaned = normalize_column_names(cleaned)
    cleaned = repair_geometries(cleaned)
    cleaned["context_layer"] = layer_name
    return cleaned


def clip_to_dfw(
    gdf: gpd.GeoDataFrame,
    dfw_boundary: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Clip/intersect a context layer to the DFW CBSA boundary."""
    source = to_project_crs(gdf)
    boundary = to_project_crs(dfw_boundary)[["geometry"]]
    clipped = gpd.clip(source, boundary)
    return repair_geometries(to_project_crs(clipped))


def calculate_layer_area(gdf: gpd.GeoDataFrame) -> float:
    """Calculate total layer area in square kilometers using the analysis CRS."""
    if gdf.empty:
        return 0.0
    analysis_gdf = gdf.to_crs(config.ANALYSIS_CRS)
    return round(float(analysis_gdf.geometry.area.sum() / 1_000_000), 3)


def geometry_types(gdf: gpd.GeoDataFrame) -> str:
    """Return sorted geometry type names for a layer."""
    if gdf.empty:
        return ""
    return ";".join(sorted(gdf.geometry.geom_type.dropna().unique()))


def export_geojson(gdf: gpd.GeoDataFrame, output_path: Path) -> Path:
    """Export a platform-ready GeoJSON layer in EPSG:4326."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_crs(config.PROJECT_CRS).to_file(output_path, driver="GeoJSON", index=False)
    return output_path


def catalog_row(
    layer_name: str,
    category: str,
    source: str,
    source_type: str,
    gdf: gpd.GeoDataFrame | None,
    output_geojson: Path | None,
    status: str,
    notes: str,
) -> dict[str, object]:
    """Build one layer catalog row."""
    return {
        "layer_name": layer_name,
        "category": category,
        "source": source,
        "source_type": source_type,
        "feature_count": int(len(gdf)) if gdf is not None else 0,
        "geometry_types": geometry_types(gdf) if gdf is not None else "",
        "crs": str(gdf.crs) if gdf is not None else "",
        "total_area_sq_km": calculate_layer_area(gdf) if gdf is not None else 0.0,
        "output_geojson": str(output_geojson) if output_geojson else "",
        "gpkg_layer_name": layer_name if gdf is not None else "",
        "status": status,
        "notes": notes,
    }


def build_layer_catalog(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Write the real estate layer catalog CSV."""
    catalog = pd.DataFrame(rows)
    catalog.to_csv(config.REAL_ESTATE_LAYER_CATALOG_CSV, index=False)
    return catalog


def export_catalog_gpkg(layers: dict[str, gpd.GeoDataFrame]) -> None:
    """Export all available catalog layers to one GeoPackage."""
    if config.REAL_ESTATE_LAYER_CATALOG_GPKG.exists():
        config.REAL_ESTATE_LAYER_CATALOG_GPKG.unlink()

    for layer_name, gdf in layers.items():
        gdf.to_crs(config.PROJECT_CRS).to_file(
            config.REAL_ESTATE_LAYER_CATALOG_GPKG,
            layer=layer_name,
            driver="GPKG",
            index=False,
        )


def main() -> None:
    """Run the platform-ready real estate layer catalog workflow."""
    config.ensure_directories()

    rows = []
    catalog_layers = load_boundary_layers()
    existing_metadata = {
        "dallas_county_boundary": (
            "boundary",
            "U.S. Census TIGER/Line 2025",
            config.DALLAS_COUNTY_GEOJSON,
        ),
        "dfw_cbsa_boundary": (
            "boundary",
            "U.S. Census TIGER/Line 2025",
            config.DFW_CBSA_GEOJSON,
        ),
        "dfw_zctas": (
            "boundary",
            "U.S. Census TIGER/Line 2025",
            config.DFW_ZCTAS_GEOJSON,
        ),
        "dfw_zcta_submarkets": (
            "submarket",
            "Analyst-defined ZCTA sector proxy from Census TIGER/Line 2025",
            config.DFW_SUBMARKETS_GEOJSON,
        ),
    }

    for layer_name, layer in catalog_layers.items():
        category, source, output_geojson = existing_metadata[layer_name]
        rows.append(
            catalog_row(
                layer_name=layer_name,
                category=category,
                source=source,
                source_type="existing_validated_layer",
                gdf=layer,
                output_geojson=output_geojson,
                status="available",
                notes="Existing Census-derived platform layer loaded.",
            )
        )

    dfw_boundary = catalog_layers["dfw_cbsa_boundary"]

    opportunity_zones, opportunity_note = load_public_layer(
        "dfw_opportunity_zones",
        config.HUD_RAW_DIR,
        HUD_OPPORTUNITY_ZONES_DOWNLOAD_URL,
    )
    if opportunity_zones is not None:
        opportunity_zones = clip_to_dfw(
            clean_context_layer(opportunity_zones, "dfw_opportunity_zones"),
            dfw_boundary,
        )
        export_geojson(opportunity_zones, config.DFW_OPPORTUNITY_ZONES_GEOJSON)
        catalog_layers["dfw_opportunity_zones"] = opportunity_zones
        rows.append(
            catalog_row(
                layer_name="dfw_opportunity_zones",
                category="incentive_context",
                source="HUD Opportunity Zones",
                source_type="manual_public_source_file",
                gdf=opportunity_zones,
                output_geojson=config.DFW_OPPORTUNITY_ZONES_GEOJSON,
                status="available",
                notes=f"{SOURCE_NOTES['dfw_opportunity_zones']} {opportunity_note}",
            )
        )
        print(f"Output GeoJSON path: {config.DFW_OPPORTUNITY_ZONES_GEOJSON}")
    else:
        rows.append(
            catalog_row(
                layer_name="dfw_opportunity_zones",
                category="incentive_context",
                source="HUD Opportunity Zones",
                source_type="manual_public_source_file",
                gdf=None,
                output_geojson=config.DFW_OPPORTUNITY_ZONES_GEOJSON,
                status="missing",
                notes=f"{SOURCE_NOTES['dfw_opportunity_zones']} {opportunity_note}",
            )
        )

    school_districts, school_note = load_public_layer(
        "dfw_school_districts",
        config.SCHOOL_DISTRICTS_RAW_DIR,
        SCHOOL_DISTRICTS_DOWNLOAD_URL,
    )
    if school_districts is not None:
        school_districts = clip_to_dfw(
            clean_context_layer(school_districts, "dfw_school_districts"),
            dfw_boundary,
        )
        export_geojson(school_districts, config.DFW_SCHOOL_DISTRICTS_GEOJSON)
        catalog_layers["dfw_school_districts"] = school_districts
        rows.append(
            catalog_row(
                layer_name="dfw_school_districts",
                category="education_context",
                source="Texas Legislative Council / Texas Capitol Data Portal",
                source_type="manual_public_source_file",
                gdf=school_districts,
                output_geojson=config.DFW_SCHOOL_DISTRICTS_GEOJSON,
                status="available",
                notes=f"{SOURCE_NOTES['dfw_school_districts']} {school_note}",
            )
        )
        print(f"Output GeoJSON path: {config.DFW_SCHOOL_DISTRICTS_GEOJSON}")
    else:
        rows.append(
            catalog_row(
                layer_name="dfw_school_districts",
                category="education_context",
                source="Texas Legislative Council / Texas Capitol Data Portal",
                source_type="manual_public_source_file",
                gdf=None,
                output_geojson=config.DFW_SCHOOL_DISTRICTS_GEOJSON,
                status="missing",
                notes=f"{SOURCE_NOTES['dfw_school_districts']} {school_note}",
            )
        )

    catalog = build_layer_catalog(rows)
    export_catalog_gpkg(catalog_layers)

    print("Layer catalog rows:")
    print(catalog[["layer_name", "status", "feature_count"]].to_string(index=False))
    print("Output GeoJSON paths:")
    for row in rows:
        if row["output_geojson"]:
            print(f"- {row['layer_name']} ({row['status']}): {row['output_geojson']}")
    print(f"Layer catalog CSV path: {config.REAL_ESTATE_LAYER_CATALOG_CSV}")
    print(f"GeoPackage path: {config.REAL_ESTATE_LAYER_CATALOG_GPKG}")


if __name__ == "__main__":
    main()
