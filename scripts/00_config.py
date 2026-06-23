"""
Project configuration for the Texas Real Estate Sourcing GIS Pipeline.

Defines shared coordinate reference systems, project paths, and a small
startup check for expected local directories.
"""

from pathlib import Path

PROJECT_CRS = "EPSG:4326"
ANALYSIS_CRS = "EPSG:32138"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DATA_DIR = RAW_DIR
PROCESSED_DATA_DIR = PROCESSED_DIR
FINAL_DATA_DIR = DATA_DIR / "final"
FINAL_GEOJSON_DIR = FINAL_DATA_DIR / "geojson"
FINAL_CSV_DIR = FINAL_DATA_DIR / "csv"
FINAL_GPKG_DIR = FINAL_DATA_DIR / "gpkg"
CENSUS_RAW_DIR = RAW_DIR / "census_tiger_2025"
STUDY_AREA_PROCESSED_DIR = PROCESSED_DIR / "study_area"
SUBMARKET_PROCESSED_DIR = PROCESSED_DIR / "submarkets"
SUBMARKET_DEFINITION_CSV = SUBMARKET_PROCESSED_DIR / "dfw_submarket_definition.csv"
STUDY_AREA_GPKG = FINAL_GPKG_DIR / "census_study_area.gpkg"
DALLAS_COUNTY_GEOJSON = FINAL_GEOJSON_DIR / "dallas_county_boundary.geojson"
DFW_CBSA_GEOJSON = FINAL_GEOJSON_DIR / "dfw_cbsa_boundary.geojson"
DFW_ZCTAS_GEOJSON = FINAL_GEOJSON_DIR / "dfw_zctas.geojson"
STUDY_AREA_SUMMARY_CSV = FINAL_CSV_DIR / "study_area_summary.csv"
DFW_SUBMARKETS_GEOJSON = FINAL_GEOJSON_DIR / "dfw_zcta_submarkets.geojson"
SUBMARKET_SUMMARY_CSV = FINAL_CSV_DIR / "submarket_summary.csv"
DFW_SUBMARKETS_GPKG = FINAL_GPKG_DIR / "dfw_submarkets.gpkg"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MAPS_DIR = OUTPUTS_DIR / "maps"
MAPS_PNG_DIR = MAPS_DIR / "png"
MAPS_PDF_DIR = MAPS_DIR / "pdf"
REPORT_DIR = OUTPUTS_DIR / "report"
WEBMAP_DIR = OUTPUTS_DIR / "webmap"
TABLES_DIR = OUTPUTS_DIR / "tables"

DOCS_DIR = PROJECT_ROOT / "docs"
QGIS_DIR = PROJECT_ROOT / "qgis"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

REQUIRED_DIRECTORIES = [
    RAW_DIR,
    PROCESSED_DIR,
    CENSUS_RAW_DIR,
    STUDY_AREA_PROCESSED_DIR,
    SUBMARKET_PROCESSED_DIR,
    FINAL_GEOJSON_DIR,
    FINAL_CSV_DIR,
    FINAL_GPKG_DIR,
    MAPS_PNG_DIR,
    MAPS_PDF_DIR,
    REPORT_DIR,
    WEBMAP_DIR,
    TABLES_DIR,
    DOCS_DIR,
    QGIS_DIR,
    SCREENSHOTS_DIR,
]


def ensure_directories() -> None:
    """Create expected local project directories if they do not exist."""
    for directory in REQUIRED_DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Print configuration values and confirm directory availability."""
    ensure_directories()
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Project CRS: {PROJECT_CRS}")
    print(f"Analysis CRS: {ANALYSIS_CRS}")
    print("Directory check complete.")


if __name__ == "__main__":
    main()
