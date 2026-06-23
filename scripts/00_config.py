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
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
FINAL_DATA_DIR = DATA_DIR / "final"
FINAL_GEOJSON_DIR = FINAL_DATA_DIR / "geojson"
FINAL_CSV_DIR = FINAL_DATA_DIR / "csv"
FINAL_GPKG_DIR = FINAL_DATA_DIR / "gpkg"

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
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
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
