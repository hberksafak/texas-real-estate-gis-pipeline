"""
Run lightweight repository QA checks for portfolio publication.

The script checks documentation, pipeline scripts, and locally generated
portfolio outputs. It does not download data or regenerate the pipeline.
"""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QA_REPORT_PATH = PROJECT_ROOT / "outputs" / "tables" / "repository_qa_report.csv"

TRACKED_DOCUMENTATION = [
    "README.md",
    "requirements.txt",
    ".gitignore",
    "LICENSE",
    "docs/data_sources.md",
    "docs/download_plan.md",
    "docs/expected_outputs.md",
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
    "scripts/check_required_sources.py",
    "scripts/run_full_pipeline.py",
]

KEY_LOCAL_OUTPUTS = [
    "data/final/csv/platform_layers_manifest.csv",
    "data/final/csv/ranked_site_candidates.csv",
    "data/final/csv/candidate_score_components.csv",
    "data/final/csv/candidate_summary.csv",
    "data/final/csv/disqualification_audit.csv",
    "data/final/geojson/top_25_candidate_sites.geojson",
    "data/final/geojson/dallas_waterbodies.geojson",
    "data/final/gpkg/export_ready_layers.gpkg",
    "outputs/webmap/texas_real_estate_sourcing_webmap.html",
    "outputs/tables/top25_quality_audit.csv",
    "outputs/tables/top25_rank_stability_audit.csv",
    "outputs/tables/scoring_model_manifest.csv",
    "outputs/tables/scoring_component_variance_audit.csv",
    "outputs/tables/top25_scoring_audit.csv",
    "outputs/tables/static_map_export_summary.csv",
    "outputs/maps/png/dfw_study_area_overview.png",
    "outputs/maps/png/dallas_candidate_screening_map.png",
    "outputs/maps/png/top_25_candidate_sites_map.png",
    "outputs/maps/pdf/dfw_study_area_overview.pdf",
    "outputs/maps/pdf/dallas_candidate_screening_map.pdf",
    "outputs/maps/pdf/top_25_candidate_sites_map.pdf",
]


def load_config() -> ModuleType:
    """Load constants from 00_config.py, whose filename is not importable."""
    config_path = PROJECT_ROOT / "scripts" / "00_config.py"
    spec = importlib.util.spec_from_file_location("pipeline_config", config_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load config from {config_path}")

    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    return config


config = load_config()


def as_bool(value: object) -> bool:
    """Parse bool-like GeoJSON/CSV values without treating non-empty strings as True."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


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


def check_text_contains(
    check_name: str,
    relative_path: str,
    required_text: list[str],
    notes: str,
) -> dict[str, object]:
    """Return one QA check row confirming required release guidance is present."""
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return {
            "check_name": check_name,
            "path": str(path),
            "exists": False,
            "status": "failed",
            "notes": f"File is missing. {notes}",
        }

    text = path.read_text(encoding="utf-8")
    missing = [snippet for snippet in required_text if snippet not in text]
    status = "passed" if not missing else "failed"
    missing_note = "" if not missing else " Missing text: " + "; ".join(missing)
    return {
        "check_name": check_name,
        "path": str(path),
        "exists": True,
        "status": status,
        "notes": notes + missing_note,
    }


def read_csv_by_candidate_id(path: Path) -> dict[str, dict[str, str]]:
    """Read a CSV keyed by candidate_id when available."""
    if not path.exists():
        return {}
    with path.open("r", newline="", encoding="utf-8") as csv_file:
        return {
            row.get("candidate_id", ""): row
            for row in csv.DictReader(csv_file)
            if row.get("candidate_id")
        }


def build_top25_quality_audit() -> None:
    """Write a focused Top 25 QA audit CSV from the current generated outputs."""
    top_25_path = config.TOP_25_CANDIDATE_SITES_GEOJSON
    if not top_25_path.exists():
        return

    audit_lookup = read_csv_by_candidate_id(config.DISQUALIFICATION_AUDIT_CSV)
    with top_25_path.open("r", encoding="utf-8") as geojson_file:
        data = json.load(geojson_file)

    rows = []
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        candidate_id = str(properties.get("candidate_id", ""))
        audit_row = audit_lookup.get(candidate_id, {})
        rows.append(
            {
                "candidate_rank": properties.get("candidate_rank", ""),
                "candidate_id": candidate_id,
                "final_site_score": properties.get("final_site_score", ""),
                "qualified": properties.get("qualified", audit_row.get("qualified", "")),
                "is_official_parcel": properties.get("is_official_parcel", ""),
                "candidate_source": properties.get("candidate_source", ""),
                "submarket": properties.get("submarket_name", ""),
                "opportunity_zone_flag": properties.get("opportunity_zone_context", ""),
                "school_district_context": properties.get("school_district_context", ""),
                "school_district_name": properties.get("school_district_name", ""),
                "area_ratio_to_full_grid": properties.get("area_ratio_to_full_grid", ""),
                "water_overlap_ratio": properties.get("water_overlap_ratio", ""),
                "centroid_inside_water": properties.get("centroid_inside_water", ""),
                "rule_edge_fragment": properties.get("rule_edge_fragment", ""),
                "rule_waterbody_overlap": properties.get("rule_waterbody_overlap", ""),
                "failed_rule_count": properties.get(
                    "failed_rule_count",
                    audit_row.get("failed_rule_count", ""),
                ),
                "failed_rules": properties.get("failed_rules", audit_row.get("failed_rules", "")),
                "primary_disqualification_reason": properties.get(
                    "primary_disqualification_reason",
                    audit_row.get("primary_disqualification_reason", ""),
                ),
            }
        )

    rows.sort(key=lambda row: int(float(row["candidate_rank"] or 0)))
    config.TOP25_QUALITY_AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "candidate_rank",
        "candidate_id",
        "final_site_score",
        "qualified",
        "is_official_parcel",
        "candidate_source",
        "submarket",
        "opportunity_zone_flag",
        "school_district_context",
        "school_district_name",
        "area_ratio_to_full_grid",
        "water_overlap_ratio",
        "centroid_inside_water",
        "rule_edge_fragment",
        "rule_waterbody_overlap",
        "failed_rule_count",
        "failed_rules",
        "primary_disqualification_reason",
    ]
    with config.TOP25_QUALITY_AUDIT_CSV.open("w", newline="", encoding="utf-8") as audit_file:
        writer = csv.DictWriter(audit_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def check_waterbody_summary() -> dict[str, object]:
    """Confirm the candidate summary reports the waterbody QA rule count."""
    path = config.CANDIDATE_SUMMARY_CSV
    if not path.exists():
        return {
            "check_name": "waterbody_rule::candidate_summary",
            "path": str(path),
            "exists": False,
            "status": "failed",
            "notes": "Candidate summary CSV is missing.",
        }

    with path.open("r", newline="", encoding="utf-8") as summary_file:
        rows = list(csv.DictReader(summary_file))
    if not rows or "waterbody_disqualified_candidate_count" not in rows[0]:
        return {
            "check_name": "waterbody_rule::candidate_summary",
            "path": str(path),
            "exists": True,
            "status": "failed",
            "notes": "Candidate summary is missing waterbody_disqualified_candidate_count.",
        }

    count = rows[0]["waterbody_disqualified_candidate_count"]
    return {
        "check_name": "waterbody_rule::candidate_summary",
        "path": str(path),
        "exists": True,
        "status": "passed",
        "notes": f"Waterbody-disqualified candidate count: {count}.",
    }


def check_top_25_waterbody_exclusion() -> dict[str, object]:
    """Confirm Top 25 candidates do not fail the waterbody QA threshold."""
    path = config.TOP_25_CANDIDATE_SITES_GEOJSON
    if not path.exists():
        return {
            "check_name": "waterbody_rule::top_25_candidates",
            "path": str(path),
            "exists": False,
            "status": "failed",
            "notes": "Top 25 candidate GeoJSON is missing.",
        }

    with path.open("r", encoding="utf-8") as geojson_file:
        data = json.load(geojson_file)

    failed_candidates = []
    missing_fields = []
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        candidate_id = properties.get("candidate_id", "unknown")
        if (
            "centroid_inside_water" not in properties
            or "water_overlap_ratio" not in properties
            or "rule_edge_fragment" not in properties
            or "rule_waterbody_overlap" not in properties
        ):
            missing_fields.append(str(candidate_id))
            continue
        centroid_inside_water = as_bool(properties.get("centroid_inside_water"))
        rule_edge_fragment = as_bool(properties.get("rule_edge_fragment"))
        rule_waterbody_overlap = as_bool(properties.get("rule_waterbody_overlap"))
        water_overlap_ratio = float(properties.get("water_overlap_ratio") or 0)
        if (
            centroid_inside_water
            or rule_edge_fragment
            or rule_waterbody_overlap
            or water_overlap_ratio >= config.WATER_OVERLAP_RATIO_THRESHOLD
        ):
            failed_candidates.append(str(candidate_id))

    status = "passed" if not failed_candidates and not missing_fields else "failed"
    if missing_fields:
        notes = "Missing waterbody QA fields for candidates: " + ";".join(missing_fields[:10])
    elif failed_candidates:
        notes = "Top 25 waterbody QA failures: " + ";".join(failed_candidates[:10])
    else:
        notes = (
            "Top 25 candidates have centroid_inside_water=False and "
            f"water_overlap_ratio < {config.WATER_OVERLAP_RATIO_THRESHOLD}; "
            "rule_waterbody_overlap=False; rule_edge_fragment=False."
        )

    return {
        "check_name": "waterbody_rule::top_25_candidates",
        "path": str(path),
        "exists": True,
        "status": status,
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
    rows.append(check_waterbody_summary())
    rows.append(check_top_25_waterbody_exclusion())
    rows.append(
        check_text_contains(
            check_name="release_guidance::readme_source_preflight",
            relative_path="README.md",
            required_text=[
                "python3 scripts/check_required_sources.py",
                "source preflight",
                "Raw source files are intentionally not",
                "committed to git",
            ],
            notes="README documents source preflight and raw-data staging expectations.",
        )
    )
    rows.append(
        check_text_contains(
            check_name="release_guidance::docs_manual_source_staging",
            relative_path="docs/download_plan.md",
            required_text=[
                "Release Source Preflight Notes",
                "data/raw/hud_opportunity_zones/hud_opportunity_zones_tx.geojson",
                "data/raw/texas_school_districts/tl_2025_48_unsd.zip",
            ],
            notes="Download plan documents exact manual context source staging paths.",
        )
    )
    rows.append(
        check_text_contains(
            check_name="release_guidance::runner_calls_source_preflight",
            relative_path="scripts/run_full_pipeline.py",
            required_text=[
                "scripts/check_required_sources.py",
                "Required local source files are missing.",
            ],
            notes="Full pipeline runner invokes the source preflight before generating outputs.",
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
    build_top25_quality_audit()
    rows = build_checks()
    write_report(rows)

    total_checks = len(rows)
    passed_checks = sum(row["status"] == "passed" for row in rows)
    failed_checks = total_checks - passed_checks

    print(f"Total checks: {total_checks}")
    print(f"Passed checks: {passed_checks}")
    print(f"Failed checks: {failed_checks}")
    print(f"QA report path: {QA_REPORT_PATH}")
    if failed_checks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
