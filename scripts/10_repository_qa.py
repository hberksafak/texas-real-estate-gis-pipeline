"""
Run lightweight repository QA checks for portfolio publication.

The script checks documentation, pipeline scripts, and locally generated
portfolio outputs. It does not download data or regenerate the pipeline.
"""

from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QA_REPORT_PATH = PROJECT_ROOT / "outputs" / "tables" / "repository_qa_report.csv"

TRACKED_DOCUMENTATION = [
    "README.md",
    "requirements.txt",
    ".gitignore",
    "LICENSE",
    "docs/data_sources.md",
    "docs/download_plan.md",
    "docs/methodology.md",
    "docs/data_dictionary.md",
    "docs/portfolio_case_study.md",
    "qgis/README.md",
    "screenshots/README.md",
]

REQUIRED_SCRIPTS = [
    "scripts/00_config.py",
    "scripts/01_prepare_sources.py",
    "scripts/02_clean_validate_layers.py",
    "scripts/03_build_zcta_submarkets.py",
    "scripts/04_build_real_estate_layers.py",
    "scripts/05_parcel_screening_rules.py",
    "scripts/06_score_rank_candidates.py",
    "scripts/07_export_platform_geojson.py",
    "scripts/08_create_interactive_webmap.py",
    "scripts/09_create_static_map_exports.py",
    "scripts/10_repository_qa.py",
]

KEY_LOCAL_OUTPUTS = [
    "data/final/csv/platform_layers_manifest.csv",
    "data/final/csv/ranked_site_candidates.csv",
    "data/final/csv/candidate_score_components.csv",
    "data/final/gpkg/export_ready_layers.gpkg",
    "outputs/webmap/texas_real_estate_sourcing_webmap.html",
    "outputs/tables/static_map_export_summary.csv",
    "outputs/maps/png/dfw_study_area_overview.png",
    "outputs/maps/png/dallas_candidate_screening_map.png",
    "outputs/maps/png/top_25_candidate_sites_map.png",
]


def check_path(check_name: str, relative_path: str, notes: str) -> dict[str, object]:
    """Return one QA check row for a relative path."""
    path = PROJECT_ROOT / relative_path
    exists = path.exists()
    return {
        "check_name": check_name,
        "path": str(path),
        "exists": exists,
        "status": "passed" if exists else "failed",
        "notes": notes,
    }


def build_checks() -> list[dict[str, object]]:
    """Build all repository QA checks."""
    rows = []
    for relative_path in TRACKED_DOCUMENTATION:
        rows.append(
            check_path(
                check_name=f"tracked_documentation::{relative_path}",
                relative_path=relative_path,
                notes="Required tracked documentation file.",
            )
        )

    for relative_path in REQUIRED_SCRIPTS:
        rows.append(
            check_path(
                check_name=f"pipeline_script::{relative_path}",
                relative_path=relative_path,
                notes="Required tracked pipeline or QA script.",
            )
        )

    for relative_path in KEY_LOCAL_OUTPUTS:
        rows.append(
            check_path(
                check_name=f"local_generated_output::{relative_path}",
                relative_path=relative_path,
                notes="Ignored generated portfolio output expected locally after pipeline run.",
            )
        )
    return rows


def write_report(rows: list[dict[str, object]]) -> None:
    """Write the QA report CSV."""
    QA_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["check_name", "path", "exists", "status", "notes"]
    with QA_REPORT_PATH.open("w", newline="", encoding="utf-8") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Run repository QA checks and write the report."""
    rows = build_checks()
    write_report(rows)

    total_checks = len(rows)
    passed_checks = sum(row["status"] == "passed" for row in rows)
    failed_checks = total_checks - passed_checks

    print(f"Total checks: {total_checks}")
    print(f"Passed checks: {passed_checks}")
    print(f"Failed checks: {failed_checks}")
    print(f"QA report path: {QA_REPORT_PATH}")


if __name__ == "__main__":
    main()
