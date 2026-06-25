"""
Run the full release pipeline in dependency order.

This runner is intended for portfolio reviewers and local release QA. It does
not change analysis logic; it calls the existing milestone scripts, stops on
the first failure, writes a small output-consistency audit, and prints a final
summary from generated pipeline artifacts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PIPELINE_STEPS = [
    ("Configuration and directory check", "scripts/00_config.py"),
    ("Census boundary source preparation", "scripts/01_prepare_sources.py"),
    ("ZCTA submarket proxy build", "scripts/03_build_zcta_submarkets.py"),
    ("Reusable layer cleaning and validation", "scripts/02_clean_validate_layers.py"),
    ("Real estate context layer catalog", "scripts/04_build_real_estate_layers.py"),
    ("Candidate proxy screening rules", "scripts/05_parcel_screening_rules.py"),
    ("Frozen v2 candidate scoring and ranking", "scripts/06_score_rank_candidates.py"),
    ("Platform-ready GeoJSON export", "scripts/07_export_platform_geojson.py"),
    ("Interactive Folium web map", "scripts/08_create_interactive_webmap.py"),
    ("Static portfolio map exports", "scripts/09_create_static_map_exports.py"),
]

QA_STEP = ("Repository QA", "scripts/10_repository_qa.py")

OUTPUT_FOLDERS = [
    "data/final/geojson",
    "data/final/csv",
    "data/final/gpkg",
    "outputs/maps/png",
    "outputs/maps/pdf",
    "outputs/tables",
    "outputs/webmap",
]


def run_source_preflight() -> None:
    """Run required source preflight before generating outputs."""
    script_path = "scripts/check_required_sources.py"
    print("[preflight] Required local source files", flush=True)
    print(f"Running: {sys.executable} {script_path}", flush=True)
    env = os.environ.copy()
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            "\nRequired local source files are missing. "
            "See docs/data_sources.md and docs/download_plan.md."
        )


def run_step(step_number: int, step_count: int, label: str, script_path: str) -> None:
    """Run one pipeline script and stop immediately if it fails."""
    print(f"\n[{step_number}/{step_count}] {label}", flush=True)
    print(f"Running: {sys.executable} {script_path}", flush=True)
    env = os.environ.copy()
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    try:
        subprocess.run(
            [sys.executable, script_path],
            cwd=PROJECT_ROOT,
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"\nPipeline failed during step {step_number}: {label}\n"
            f"Script: {script_path}\n"
            f"Exit code: {exc.returncode}"
        ) from exc


def read_top25_geojson_rows(path: Path) -> pd.DataFrame:
    """Read Top 25 GeoJSON properties for consistency comparison."""
    with path.open("r", encoding="utf-8") as geojson_file:
        data = json.load(geojson_file)

    rows = [feature.get("properties", {}) for feature in data.get("features", [])]
    if not rows:
        return pd.DataFrame(columns=["candidate_rank", "candidate_id", "final_site_score"])
    return pd.DataFrame(rows).sort_values("candidate_rank").reset_index(drop=True)


def write_rank_stability_audit() -> Path:
    """Compare ranked CSV Top 25 against exported Top 25 GeoJSON."""
    ranked_path = PROJECT_ROOT / "data" / "final" / "csv" / "ranked_site_candidates.csv"
    top25_geojson_path = (
        PROJECT_ROOT / "data" / "final" / "geojson" / "top_25_candidate_sites.geojson"
    )
    audit_path = PROJECT_ROOT / "outputs" / "tables" / "top25_rank_stability_audit.csv"

    ranked = pd.read_csv(ranked_path).sort_values("candidate_rank").head(25).reset_index(drop=True)
    top25 = read_top25_geojson_rows(top25_geojson_path).head(25).reset_index(drop=True)

    rows = []
    row_count = max(len(ranked), len(top25))
    for index in range(row_count):
        ranked_row = ranked.iloc[index] if index < len(ranked) else pd.Series(dtype=object)
        top25_row = top25.iloc[index] if index < len(top25) else pd.Series(dtype=object)
        rank_1 = ranked_row.get("candidate_rank", "")
        rank_2 = top25_row.get("candidate_rank", "")
        id_1 = ranked_row.get("candidate_id", "")
        id_2 = top25_row.get("candidate_id", "")
        score_1 = ranked_row.get("final_site_score", "")
        score_2 = top25_row.get("final_site_score", "")
        rank_match = str(rank_1) == str(rank_2)
        id_match = str(id_1) == str(id_2)
        score_match = float(score_1) == float(score_2) if score_1 != "" and score_2 != "" else False

        rows.append(
            {
                "candidate_rank": rank_1 or rank_2,
                "candidate_id_run_1": id_1,
                "candidate_id_run_2": id_2,
                "score_run_1": score_1,
                "score_run_2": score_2,
                "rank_match": rank_match,
                "id_match": id_match,
                "score_match": score_match,
                "notes": "ranked_csv_to_top25_geojson_match"
                if rank_match and id_match and score_match
                else "mismatch",
            }
        )

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(audit_path, index=False)
    print(f"\nTop 25 rank stability audit path: {audit_path}", flush=True)
    return audit_path


def load_candidate_summary() -> dict[str, object]:
    """Read candidate counts from the generated summary CSV."""
    path = PROJECT_ROOT / "data" / "final" / "csv" / "candidate_summary.csv"
    if not path.exists():
        return {}
    return pd.read_csv(path).iloc[0].to_dict()


def count_top25_features() -> int:
    """Count features in the generated Top 25 GeoJSON."""
    path = PROJECT_ROOT / "data" / "final" / "geojson" / "top_25_candidate_sites.geojson"
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as geojson_file:
        data = json.load(geojson_file)
    return len(data.get("features", []))


def load_repository_qa_result() -> tuple[int, int, int]:
    """Read repository QA totals from the generated QA report."""
    path = PROJECT_ROOT / "outputs" / "tables" / "repository_qa_report.csv"
    if not path.exists():
        return 0, 0, 0
    qa = pd.read_csv(path)
    total = len(qa)
    failed = int((qa["status"] != "passed").sum())
    passed = total - failed
    return total, passed, failed


def print_final_summary() -> None:
    """Print a reviewer-friendly summary of the generated pipeline outputs."""
    summary = load_candidate_summary()
    total_qa, passed_qa, failed_qa = load_repository_qa_result()
    print("\nFull pipeline complete.", flush=True)
    print(f"Total candidates: {int(summary.get('total_candidates', 0))}", flush=True)
    print(f"Qualified candidates: {int(summary.get('qualified_candidates', 0))}", flush=True)
    print(f"Disqualified candidates: {int(summary.get('disqualified_candidates', 0))}", flush=True)
    print(f"Top 25 count: {count_top25_features()}", flush=True)
    print(f"Repository QA result: {passed_qa}/{total_qa} passed; {failed_qa} failed", flush=True)
    print("Output folders generated:", flush=True)
    for folder in OUTPUT_FOLDERS:
        path = PROJECT_ROOT / folder
        print(f"- {path}", flush=True)


def main() -> None:
    """Run the release-grade reproducibility pipeline."""
    run_source_preflight()
    step_count = len(PIPELINE_STEPS) + 1
    for index, (label, script_path) in enumerate(PIPELINE_STEPS, start=1):
        run_step(index, step_count, label, script_path)

    write_rank_stability_audit()
    run_step(step_count, step_count, *QA_STEP)
    print_final_summary()


if __name__ == "__main__":
    main()
