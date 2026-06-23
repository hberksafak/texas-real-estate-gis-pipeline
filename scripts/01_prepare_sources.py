"""
Download Census TIGER/Line 2025 boundaries and build the initial study area.

This workflow uses only U.S. Census boundary data to create the DFW CBSA,
Dallas County, and DFW-intersecting ZCTA layers used by later pipeline steps.
"""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path
from types import ModuleType

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry.base import BaseGeometry


CENSUS_DOWNLOADS = {
    "county": {
        "url": "https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip",
        "relative_path": Path("county") / "tl_2025_us_county.zip",
    },
    "cbsa": {
        "url": "https://www2.census.gov/geo/tiger/TIGER2025/CBSA/tl_2025_us_cbsa.zip",
        "relative_path": Path("cbsa") / "tl_2025_us_cbsa.zip",
    },
    "zcta": {
        "url": "https://www2.census.gov/geo/tiger/TIGER2025/ZCTA520/tl_2025_us_zcta520.zip",
        "relative_path": Path("zcta") / "tl_2025_us_zcta520.zip",
    },
}

SOURCE_LABEL = "U.S. Census TIGER/Line 2025"
TEXAS_STATEFP = "48"
DFW_NAME_TOKEN = "dallas-fort worth"


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


def census_zip_paths() -> dict[str, Path]:
    """Return local Census ZIP targets keyed by source name."""
    return {
        key: config.CENSUS_RAW_DIR / details["relative_path"]
        for key, details in CENSUS_DOWNLOADS.items()
    }


def download_if_missing(url: str, target_path: Path) -> str:
    """Download a source ZIP only when the local file is not already present."""
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists():
        if not zipfile.is_zipfile(target_path):
            raise ValueError(f"Existing file is not a valid ZIP: {target_path}")
        message = f"Skipped existing file: {target_path}"
        print(message)
        return message

    part_path = target_path.with_suffix(target_path.suffix + ".part")
    print(f"Downloading {url}")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with part_path.open("wb") as target_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    target_file.write(chunk)

    part_path.replace(target_path)
    if not zipfile.is_zipfile(target_path):
        target_path.unlink(missing_ok=True)
        raise ValueError(f"Downloaded file is not a valid ZIP: {target_path}")

    message = f"Downloaded file: {target_path}"
    print(message)
    return message


def read_census_zip(zip_path: Path, **kwargs) -> gpd.GeoDataFrame:
    """Read a TIGER/Line ZIP with GeoPandas using compatible path formats."""
    try:
        return gpd.read_file(zip_path, **kwargs)
    except Exception:
        return gpd.read_file(f"zip://{zip_path}", **kwargs)


def to_project_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure a GeoDataFrame is in the project export CRS."""
    if gdf.crs is None:
        gdf = gdf.set_crs(config.PROJECT_CRS)
    elif str(gdf.crs).upper() != config.PROJECT_CRS:
        gdf = gdf.to_crs(config.PROJECT_CRS)
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


def find_dallas_county(counties: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Filter the Census county layer to Dallas County, Texas."""
    texas_counties = counties[counties["STATEFP"].astype(str) == TEXAS_STATEFP]
    dallas_county = texas_counties[
        texas_counties["NAME"].astype(str).str.casefold() == "dallas"
    ].copy()

    if dallas_county.empty:
        raise ValueError("Dallas County was not found in the Census county layer.")

    return clean_geometries(to_project_crs(dallas_county))


def normalize_name(value: object) -> str:
    """Normalize Census name text for robust CBSA matching."""
    return (
        str(value)
        .casefold()
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )


def find_dfw_cbsa(cbsa: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Find the Dallas-Fort Worth CBSA using NAME and NAMELSAD fields."""
    name_columns = [column for column in ("NAME", "NAMELSAD") if column in cbsa.columns]
    if not name_columns:
        raise ValueError("CBSA layer does not include NAME or NAMELSAD fields.")

    mask = pd.Series(False, index=cbsa.index)
    for column in name_columns:
        mask = mask | cbsa[column].map(normalize_name).str.contains(
            DFW_NAME_TOKEN,
            na=False,
        )

    dfw_cbsa = cbsa[mask].copy()
    if dfw_cbsa.empty:
        raise ValueError("Dallas-Fort Worth CBSA was not found in the CBSA layer.")

    return clean_geometries(to_project_crs(dfw_cbsa))


def read_zctas_for_cbsa(zip_path: Path, dfw_cbsa: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Read ZCTAs with a DFW bbox when supported, then spatially filter."""
    bbox = tuple(dfw_cbsa.total_bounds)
    try:
        zctas = read_census_zip(zip_path, bbox=bbox)
        print("Read ZCTA layer using DFW CBSA bbox.")
    except Exception as exc:
        print(f"ZCTA bbox read failed; reading full ZCTA layer. Reason: {exc}")
        zctas = read_census_zip(zip_path)

    zctas = clean_geometries(to_project_crs(zctas))
    cbsa_union = (
        dfw_cbsa.geometry.union_all()
        if hasattr(dfw_cbsa.geometry, "union_all")
        else dfw_cbsa.geometry.unary_union
    )
    zctas = zctas[zctas.intersects(cbsa_union)].copy()
    zctas = clean_geometries(zctas)

    clipped = gpd.clip(zctas, dfw_cbsa[["geometry"]])
    return clean_geometries(to_project_crs(clipped))


def total_area_sq_km(gdf: gpd.GeoDataFrame) -> float:
    """Calculate total layer area in square kilometers using the analysis CRS."""
    analysis_gdf = gdf.to_crs(config.ANALYSIS_CRS)
    return round(float(analysis_gdf.geometry.area.sum() / 1_000_000), 3)


def export_layers(
    dallas_county: gpd.GeoDataFrame,
    dfw_cbsa: gpd.GeoDataFrame,
    dfw_zctas: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Export GeoJSON, GeoPackage, and summary CSV study-area outputs."""
    config.ensure_directories()

    outputs = {
        "dallas_county_boundary": (dallas_county, config.DALLAS_COUNTY_GEOJSON),
        "dfw_cbsa_boundary": (dfw_cbsa, config.DFW_CBSA_GEOJSON),
        "dfw_zctas": (dfw_zctas, config.DFW_ZCTAS_GEOJSON),
    }

    for _, (gdf, output_path) in outputs.items():
        gdf.to_crs(config.PROJECT_CRS).to_file(output_path, driver="GeoJSON", index=False)

    if config.STUDY_AREA_GPKG.exists():
        config.STUDY_AREA_GPKG.unlink()

    for layer_name, (gdf, _) in outputs.items():
        gdf.to_crs(config.PROJECT_CRS).to_file(
            config.STUDY_AREA_GPKG,
            layer=layer_name,
            driver="GPKG",
            index=False,
        )

    summary_rows = []
    for layer_name, (gdf, output_path) in outputs.items():
        summary_rows.append(
            {
                "layer_name": layer_name,
                "feature_count": int(len(gdf)),
                "crs": config.PROJECT_CRS,
                "area_sq_km": total_area_sq_km(gdf),
                "source": SOURCE_LABEL,
                "output_path": str(output_path),
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(config.STUDY_AREA_SUMMARY_CSV, index=False)
    return summary


def main() -> None:
    """Run the Census-only study-area source preparation workflow."""
    config.ensure_directories()
    paths = census_zip_paths()

    for key, target_path in paths.items():
        download_if_missing(CENSUS_DOWNLOADS[key]["url"], target_path)

    counties = clean_geometries(to_project_crs(read_census_zip(paths["county"])))
    dallas_county = find_dallas_county(counties)

    cbsa = clean_geometries(to_project_crs(read_census_zip(paths["cbsa"])))
    dfw_cbsa = find_dfw_cbsa(cbsa)

    dfw_zctas = read_zctas_for_cbsa(paths["zcta"], dfw_cbsa)

    summary = export_layers(dallas_county, dfw_cbsa, dfw_zctas)

    print(f"Dallas County feature count: {len(dallas_county)}")
    print(f"DFW CBSA feature count: {len(dfw_cbsa)}")
    print(f"DFW ZCTA feature count: {len(dfw_zctas)}")
    print("Final output paths:")
    print(f"- {config.DALLAS_COUNTY_GEOJSON}")
    print(f"- {config.DFW_CBSA_GEOJSON}")
    print(f"- {config.DFW_ZCTAS_GEOJSON}")
    print(f"- {config.STUDY_AREA_SUMMARY_CSV}")
    print(f"- {config.STUDY_AREA_GPKG}")
    print("Study area summary:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
