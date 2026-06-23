"""
Score and rank qualified analyst-defined candidate-site proxy polygons.

This workflow ranks only qualified proxy candidates from the screening
foundation. The score is a transparent portfolio demonstration ranking, not a
legal parcel valuation or development feasibility determination.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import geopandas as gpd
import pandas as pd


IDEAL_MIN_ACRES = 25
IDEAL_MAX_ACRES = 120
MAX_TAPER_ACRES = 250
SCORING_MODEL_VERSION = "v1_proxy_candidate_scoring"
SCORING_NOTE = (
    "Transparent proxy ranking for portfolio demonstration; not a legal parcel "
    "valuation or development feasibility determination."
)

COMPONENT_WEIGHTS = {
    "size_score": 0.25,
    "grid_completeness_score": 0.20,
    "submarket_score": 0.20,
    "opportunity_score": 0.15,
    "school_context_score": 0.10,
    "geometry_score": 0.10,
}

RANKED_CSV_COLUMNS = [
    "candidate_rank",
    "candidate_id",
    "final_site_score",
    "size_score",
    "grid_completeness_score",
    "submarket_score",
    "opportunity_score",
    "school_context_score",
    "geometry_score",
    "area_acres",
    "area_ratio_to_full_grid",
    "submarket_name",
    "opportunity_zone_context",
    "school_district_name",
    "candidate_source",
    "is_official_parcel",
    "scoring_model_version",
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


def validate_inputs() -> None:
    """Confirm required scoring inputs exist."""
    input_paths = [
        config.QUALIFIED_CANDIDATES_GEOJSON,
        config.PARCEL_SCREENING_CANDIDATES_GEOJSON,
        config.DISQUALIFICATION_AUDIT_CSV,
    ]
    missing = [str(path) for path in input_paths if not path.exists()]
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Milestone 8 requires screening outputs from Milestone 7. "
            "Run `python3 scripts/05_parcel_screening_rules.py` first.\n"
            f"Missing files:\n{missing_text}"
        )


def to_project_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Standardize a layer to the final platform CRS."""
    if gdf.crs is None:
        return gdf.set_crs(config.PROJECT_CRS)
    if str(gdf.crs).upper() != config.PROJECT_CRS:
        return gdf.to_crs(config.PROJECT_CRS)
    return gdf


def load_qualified_candidates() -> gpd.GeoDataFrame:
    """Read qualified candidates and confirm the layer contains qualified rows."""
    candidates = to_project_crs(gpd.read_file(config.QUALIFIED_CANDIDATES_GEOJSON))
    if candidates.empty:
        raise ValueError("No qualified candidate sites were found to score.")

    if "qualified" not in candidates.columns:
        raise ValueError("Qualified candidate layer is missing the `qualified` field.")

    if not candidates["qualified"].astype(bool).all():
        raise ValueError("Qualified candidate layer contains non-qualified records.")

    required_fields = [
        "candidate_id",
        "candidate_source",
        "is_official_parcel",
        "area_acres",
        "submarket_name",
        "opportunity_zone_context",
        "school_district_name",
        "school_district_context",
        "geometry_valid",
    ]
    missing_fields = [field for field in required_fields if field not in candidates.columns]
    if missing_fields:
        raise ValueError(f"Qualified candidate layer is missing fields: {missing_fields}")

    if "area_ratio_to_full_grid" not in candidates.columns:
        candidates["area_ratio_to_full_grid"] = 1.0

    return candidates


def calculate_size_score(area_acres: float) -> float:
    """Score size suitability, favoring the ideal 25-120 acre range."""
    if IDEAL_MIN_ACRES <= area_acres <= IDEAL_MAX_ACRES:
        return 100.0
    if area_acres < IDEAL_MIN_ACRES:
        return max(0.0, min(100.0, (area_acres / IDEAL_MIN_ACRES) * 100))

    taper_span = MAX_TAPER_ACRES - IDEAL_MAX_ACRES
    score = ((MAX_TAPER_ACRES - area_acres) / taper_span) * 100
    return max(0.0, min(100.0, score))


def calculate_submarket_scores(candidates: gpd.GeoDataFrame) -> pd.Series:
    """Create neutral supply-depth scores from candidate distribution by submarket."""
    counts = candidates["submarket_name"].fillna("unknown").value_counts()
    min_count = int(counts.min())
    max_count = int(counts.max())

    if max_count == min_count:
        score_lookup = {submarket: 72.5 for submarket in counts.index}
    else:
        score_lookup = {
            submarket: 60 + 25 * ((count - min_count) / (max_count - min_count))
            for submarket, count in counts.items()
        }

    return candidates["submarket_name"].fillna("unknown").map(score_lookup).astype(float)


def has_clean_school_context(row: pd.Series) -> bool:
    """Return True when school district context is present and non-placeholder."""
    name = str(row.get("school_district_name", "")).strip().casefold()
    has_context = bool(row.get("school_district_context", False))
    return has_context and name not in {"", "nan", "none", "unknown"}


def add_score_fields(candidates: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calculate component scores, weighted final score, and deterministic ranks."""
    scored = candidates.copy()
    scored["size_score"] = scored["area_acres"].astype(float).apply(calculate_size_score)
    scored["grid_completeness_score"] = (
        scored["area_ratio_to_full_grid"].astype(float).clip(lower=0, upper=1) * 100
    )
    scored["submarket_score"] = calculate_submarket_scores(scored)
    scored["opportunity_score"] = scored["opportunity_zone_context"].astype(bool).map(
        {True: 100.0, False: 50.0}
    )
    scored["school_context_score"] = scored.apply(
        lambda row: 100.0 if has_clean_school_context(row) else 50.0,
        axis=1,
    )
    scored["geometry_score"] = scored["geometry_valid"].astype(bool).map(
        {True: 100.0, False: 0.0}
    )

    scored["final_site_score"] = 0.0
    for component, weight in COMPONENT_WEIGHTS.items():
        scored["final_site_score"] += scored[component] * weight
    scored["final_site_score"] = scored["final_site_score"].round(3)

    score_columns = [
        "size_score",
        "grid_completeness_score",
        "submarket_score",
        "opportunity_score",
        "school_context_score",
        "geometry_score",
    ]
    scored[score_columns] = scored[score_columns].round(3)

    scored["scoring_model_version"] = SCORING_MODEL_VERSION
    scored["scoring_note"] = SCORING_NOTE
    scored = scored.sort_values(
        [
            "final_site_score",
            "size_score",
            "grid_completeness_score",
            "candidate_id",
        ],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    scored["candidate_rank"] = scored.index + 1
    return gpd.GeoDataFrame(scored, geometry="geometry", crs=candidates.crs)


def build_score_components() -> pd.DataFrame:
    """Describe score components, weights, and neutral-use constraints."""
    rows = [
        {
            "component_name": "size_score",
            "component_weight": COMPONENT_WEIGHTS["size_score"],
            "description": "Scores candidate size suitability against the 25-120 acre ideal proxy range with tapering outside the range.",
            "neutral_use_note": "Proxy size suitability only; not a legal parcel valuation or development feasibility determination.",
        },
        {
            "component_name": "grid_completeness_score",
            "component_weight": COMPONENT_WEIGHTS["grid_completeness_score"],
            "description": "Rewards candidates that retain more of a full 1,000m grid cell after clipping.",
            "neutral_use_note": "Geometry reliability proxy only.",
        },
        {
            "component_name": "submarket_score",
            "component_weight": COMPONENT_WEIGHTS["submarket_score"],
            "description": "Uses neutral candidate supply distribution by analyst-defined submarket with moderated scores.",
            "neutral_use_note": "Does not imply market demand, rent growth, demographics, or investment performance.",
        },
        {
            "component_name": "opportunity_score",
            "component_weight": COMPONENT_WEIGHTS["opportunity_score"],
            "description": "Scores Opportunity Zone overlap as policy/incentive context.",
            "neutral_use_note": "Incentive context only; not demographic targeting.",
        },
        {
            "component_name": "school_context_score",
            "component_weight": COMPONENT_WEIGHTS["school_context_score"],
            "description": "Rewards the presence of a clean school district context assignment.",
            "neutral_use_note": "Neutral context completeness only; does not use school quality, ratings, demographics, or fair-housing-risk variables.",
        },
        {
            "component_name": "geometry_score",
            "component_weight": COMPONENT_WEIGHTS["geometry_score"],
            "description": "Rewards valid candidate geometry.",
            "neutral_use_note": "Geometry QA only.",
        },
    ]
    return pd.DataFrame(rows)


def export_outputs(ranked: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Export ranked GeoJSON, CSV, score components, top 25, and GeoPackage."""
    config.ensure_directories()
    ranked_project = ranked.to_crs(config.PROJECT_CRS)
    top_25 = ranked_project.head(25).copy()

    ranked_project.to_file(
        config.RANKED_SITE_CANDIDATES_GEOJSON,
        driver="GeoJSON",
        index=False,
    )
    top_25.to_file(
        config.TOP_25_CANDIDATE_SITES_GEOJSON,
        driver="GeoJSON",
        index=False,
    )
    ranked_project[RANKED_CSV_COLUMNS].to_csv(
        config.RANKED_SITE_CANDIDATES_CSV,
        index=False,
    )

    components = build_score_components()
    components.to_csv(config.CANDIDATE_SCORE_COMPONENTS_CSV, index=False)

    if config.RANKED_CANDIDATES_GPKG.exists():
        config.RANKED_CANDIDATES_GPKG.unlink()

    ranked_project.to_file(
        config.RANKED_CANDIDATES_GPKG,
        layer="ranked_site_candidates",
        driver="GPKG",
        index=False,
    )
    top_25.to_file(
        config.RANKED_CANDIDATES_GPKG,
        layer="top_25_candidate_sites",
        driver="GPKG",
        index=False,
    )
    return top_25, components


def main() -> None:
    """Run the weighted proxy candidate scoring workflow."""
    validate_inputs()
    candidates = load_qualified_candidates()
    ranked = add_score_fields(candidates)
    top_25, _ = export_outputs(ranked)

    min_score = round(float(ranked["final_site_score"].min()), 3)
    mean_score = round(float(ranked["final_site_score"].mean()), 3)
    max_score = round(float(ranked["final_site_score"].max()), 3)

    print(f"Qualified input candidate count: {len(candidates)}")
    print(f"Ranked candidate count: {len(ranked)}")
    print(f"Top 25 exported count: {len(top_25)}")
    print(f"Final site score min/mean/max: {min_score} / {mean_score} / {max_score}")
    print(f"Output CSV path: {config.RANKED_SITE_CANDIDATES_CSV}")
    print(f"Output GeoJSON path: {config.RANKED_SITE_CANDIDATES_GEOJSON}")
    print(f"Top 25 GeoJSON path: {config.TOP_25_CANDIDATE_SITES_GEOJSON}")
    print(f"Score components CSV path: {config.CANDIDATE_SCORE_COMPONENTS_CSV}")
    print(f"Output GeoPackage path: {config.RANKED_CANDIDATES_GPKG}")


if __name__ == "__main__":
    main()
