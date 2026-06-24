"""
Score and rank qualified analyst-defined candidate-site proxy polygons.

The v2 workflow ranks only qualified proxy candidates from the screening
foundation. It uses available project GIS fields for a more discriminating
professional proxy score and explicitly marks major recommended data inputs
that are not yet implemented.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


IDEAL_MIN_ACRES = 25
IDEAL_MAX_ACRES = 120
MAX_TAPER_ACRES = 250
PROXY_IDEAL_MIN_ACRES = 60
PROXY_IDEAL_MAX_ACRES = 185
PROXY_MAX_ACRES = 250
DALLAS_CBD_LON = -96.7969
DALLAS_CBD_LAT = 32.7767
CBD_CORE_DISTANCE_KM = 15
CBD_OUTER_DISTANCE_KM = 45
CLUSTER_RADIUS_M = 5_000
SCORING_MODEL_VERSION = "v2_professional_proxy_screening_limited"
SCORING_NOTE = (
    "Professional proxy screening score for portfolio demonstration; not a "
    "parcel acquisition recommendation, legal parcel valuation, or development "
    "feasibility determination."
)
DATA_AVAILABILITY_WARNING = (
    "Road accessibility, FEMA flood, and NCTCOG land-use suitability scoring are "
    "not implemented because those source layers are not staged in the current "
    "local workflow."
)

V1_COMPONENT_WEIGHTS = {
    "size_score": 0.25,
    "grid_completeness_score": 0.20,
    "submarket_score": 0.20,
    "opportunity_score": 0.15,
    "school_context_score": 0.10,
    "geometry_score": 0.10,
}

COMPONENT_WEIGHTS = {
    "developable_geometry_score": 0.30,
    "constraint_avoidance_score": 0.25,
    "spatial_context_score": 0.25,
    "submarket_context_score": 0.15,
    "opportunity_incentive_score": 0.05,
}

RECOMMENDED_COMPONENT_STATUS = {
    "road_accessibility_score": "not_implemented_source_not_staged",
    "flood_constraint_score": "not_implemented_source_not_staged",
    "land_use_context_score": "not_implemented_source_not_staged",
}

RANKED_CSV_COLUMNS = [
    "candidate_rank",
    "candidate_id",
    "final_site_score",
    "developable_geometry_score",
    "constraint_avoidance_score",
    "spatial_context_score",
    "submarket_context_score",
    "opportunity_incentive_score",
    "developable_geometry_contribution",
    "constraint_avoidance_contribution",
    "spatial_context_contribution",
    "submarket_context_contribution",
    "opportunity_incentive_contribution",
    "usable_area_score",
    "area_integrity_score",
    "water_avoidance_score",
    "distance_to_waterbody_m",
    "waterbody_distance_score",
    "edge_integrity_score",
    "distance_to_county_boundary_m",
    "county_edge_score",
    "distance_to_dallas_cbd_km",
    "distance_to_dallas_cbd_score",
    "local_candidate_count_5km",
    "candidate_cluster_score",
    "road_accessibility_score",
    "flood_constraint_score",
    "land_use_context_score",
    "model_data_completeness_score",
    "model_data_completeness_note",
    "data_availability_warning",
    "area_acres",
    "area_ratio_to_full_grid",
    "rule_edge_fragment",
    "water_overlap_sq_m",
    "water_overlap_ratio",
    "centroid_inside_water",
    "rule_waterbody_overlap",
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
        config.DALLAS_COUNTY_GEOJSON,
        config.DALLAS_WATERBODIES_GEOJSON,
    ]
    missing = [str(path) for path in input_paths if not path.exists()]
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Scoring requires candidate screening outputs. "
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


def load_project_layer(path: Path) -> gpd.GeoDataFrame:
    """Read one project layer and standardize to the project CRS."""
    return to_project_crs(gpd.read_file(path))


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
        "area_ratio_to_full_grid",
        "rule_edge_fragment",
        "submarket_name",
        "opportunity_zone_context",
        "school_district_name",
        "school_district_context",
        "geometry_valid",
        "water_overlap_sq_m",
        "water_overlap_ratio",
        "centroid_inside_water",
        "rule_waterbody_overlap",
        "failed_rule_count",
        "failed_rules",
        "primary_disqualification_reason",
    ]
    missing_fields = [field for field in required_fields if field not in candidates.columns]
    if missing_fields:
        raise ValueError(f"Qualified candidate layer is missing fields: {missing_fields}")

    return candidates


def calculate_v1_size_score(area_acres: float) -> float:
    """Legacy v1 size score for variance audit only."""
    if IDEAL_MIN_ACRES <= area_acres <= IDEAL_MAX_ACRES:
        return 100.0
    if area_acres < IDEAL_MIN_ACRES:
        return max(0.0, min(100.0, (area_acres / IDEAL_MIN_ACRES) * 100))

    taper_span = MAX_TAPER_ACRES - IDEAL_MAX_ACRES
    score = ((MAX_TAPER_ACRES - area_acres) / taper_span) * 100
    return max(0.0, min(100.0, score))


def calculate_usable_area_score(area_acres: float) -> float:
    """Score candidate proxy footprint size without rewarding oversized cells."""
    if area_acres <= 0:
        return 0.0
    if area_acres < IDEAL_MIN_ACRES:
        return max(0.0, (area_acres / IDEAL_MIN_ACRES) * 75)
    if area_acres < PROXY_IDEAL_MIN_ACRES:
        return 75 + 25 * (
            (area_acres - IDEAL_MIN_ACRES) / (PROXY_IDEAL_MIN_ACRES - IDEAL_MIN_ACRES)
        )
    if area_acres <= PROXY_IDEAL_MAX_ACRES:
        return 100.0
    if area_acres <= PROXY_MAX_ACRES:
        return 100 - 25 * (
            (area_acres - PROXY_IDEAL_MAX_ACRES) / (PROXY_MAX_ACRES - PROXY_IDEAL_MAX_ACRES)
        )
    return 0.0


def calculate_area_integrity_score(area_ratio: float) -> float:
    """Score how much of a full proxy grid cell remains after clipping."""
    lower_bound = 0.60
    clipped = max(lower_bound, min(float(area_ratio), 1.0))
    return ((clipped - lower_bound) / (1.0 - lower_bound)) * 100


def calculate_water_avoidance_score(water_overlap_ratio: float) -> float:
    """Penalize candidates that approach the waterbody disqualification threshold."""
    threshold = config.WATER_OVERLAP_RATIO_THRESHOLD
    ratio = max(0.0, min(float(water_overlap_ratio), threshold))
    return max(0.0, 100 - (ratio / threshold) * 100)


def calculate_distance_score_ramp(
    distance_m: float,
    near_m: float,
    far_m: float,
    near_score: float,
    far_score: float,
) -> float:
    """Score a distance measure on a simple linear ramp."""
    if distance_m <= near_m:
        return near_score
    if distance_m >= far_m:
        return far_score
    return near_score + (far_score - near_score) * ((distance_m - near_m) / (far_m - near_m))


def calculate_distance_score(distance_km: float) -> float:
    """Score neutral spatial proximity to a project-defined Downtown Dallas reference."""
    if distance_km <= CBD_CORE_DISTANCE_KM:
        return 100.0
    if distance_km >= CBD_OUTER_DISTANCE_KM:
        return 40.0
    span = CBD_OUTER_DISTANCE_KM - CBD_CORE_DISTANCE_KM
    return 100 - 60 * ((distance_km - CBD_CORE_DISTANCE_KM) / span)


def normalize_series(series: pd.Series, low: float = 35.0, high: float = 100.0) -> pd.Series:
    """Normalize a numeric series to a bounded score range."""
    numeric = pd.to_numeric(series, errors="coerce").fillna(0)
    min_value = float(numeric.min())
    max_value = float(numeric.max())
    if max_value == min_value:
        return pd.Series([((low + high) / 2)] * len(numeric), index=series.index)
    return low + (numeric - min_value) * ((high - low) / (max_value - min_value))


def calculate_submarket_scores(candidates: gpd.GeoDataFrame) -> pd.Series:
    """Create neutral supply-depth scores from candidate distribution by submarket."""
    counts = candidates["submarket_name"].fillna("unknown").value_counts()
    min_count = int(counts.min())
    max_count = int(counts.max())

    if max_count == min_count:
        score_lookup = {submarket: 70.0 for submarket in counts.index}
    else:
        score_lookup = {
            submarket: 55 + 35 * ((count - min_count) / (max_count - min_count))
            for submarket, count in counts.items()
        }

    return candidates["submarket_name"].fillna("unknown").map(score_lookup).astype(float)


def has_clean_school_context(row: pd.Series) -> bool:
    """Return True when school district context is present and non-placeholder."""
    name = str(row.get("school_district_name", "")).strip().casefold()
    has_context = bool(row.get("school_district_context", False))
    return has_context and name not in {"", "nan", "none", "unknown"}


def add_spatial_context_fields(scored: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add neutral spatial context fields from existing project geometry."""
    analysis = scored.to_crs(config.ANALYSIS_CRS)
    centroids = analysis.geometry.centroid
    dallas_county = load_project_layer(config.DALLAS_COUNTY_GEOJSON).to_crs(config.ANALYSIS_CRS)
    county_union = (
        dallas_county.geometry.union_all()
        if hasattr(dallas_county.geometry, "union_all")
        else dallas_county.geometry.unary_union
    )
    cbd = gpd.GeoSeries(
        [Point(DALLAS_CBD_LON, DALLAS_CBD_LAT)],
        crs=config.PROJECT_CRS,
    ).to_crs(config.ANALYSIS_CRS).iloc[0]

    scored["distance_to_dallas_cbd_km"] = (centroids.distance(cbd) / 1_000).round(3)
    scored["distance_to_dallas_cbd_score"] = scored["distance_to_dallas_cbd_km"].apply(
        calculate_distance_score
    )

    spatial_index = centroids.sindex
    local_counts = []
    for idx, point in centroids.items():
        nearby_idx = spatial_index.query(point.buffer(CLUSTER_RADIUS_M), predicate="intersects")
        local_counts.append(max(0, len(nearby_idx) - 1))
    scored["local_candidate_count_5km"] = local_counts
    scored["candidate_cluster_score"] = normalize_series(
        scored["local_candidate_count_5km"],
        low=45,
        high=100,
    )
    scored["distance_to_county_boundary_m"] = centroids.distance(county_union.boundary).round(3)
    scored["county_edge_score"] = scored["distance_to_county_boundary_m"].apply(
        lambda distance_m: calculate_distance_score_ramp(
            float(distance_m),
            near_m=500,
            far_m=4_000,
            near_score=45,
            far_score=100,
        )
    )

    scored["spatial_context_score"] = (
        scored["distance_to_dallas_cbd_score"] * 0.45
        + scored["candidate_cluster_score"] * 0.30
        + scored["county_edge_score"] * 0.25
    )
    return scored


def add_waterbody_distance_fields(scored: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add distance-to-waterbody constraint context from the staged Census layer."""
    analysis = scored.to_crs(config.ANALYSIS_CRS)
    centroids = analysis.geometry.centroid
    waterbodies = load_project_layer(config.DALLAS_WATERBODIES_GEOJSON).to_crs(config.ANALYSIS_CRS)
    water_union = (
        waterbodies.geometry.union_all()
        if hasattr(waterbodies.geometry, "union_all")
        else waterbodies.geometry.unary_union
    )
    scored["distance_to_waterbody_m"] = centroids.distance(water_union).round(3)
    scored["waterbody_distance_score"] = scored["distance_to_waterbody_m"].apply(
        lambda distance_m: calculate_distance_score_ramp(
            float(distance_m),
            near_m=0,
            far_m=3_000,
            near_score=50,
            far_score=100,
        )
    )
    return scored


def add_centroid_lon_lat(scored: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add candidate centroid longitude/latitude for audit exports."""
    centroids_analysis = scored.to_crs(config.ANALYSIS_CRS).geometry.centroid
    centroid_gdf = gpd.GeoDataFrame(geometry=centroids_analysis, crs=config.ANALYSIS_CRS)
    centroids_project = centroid_gdf.to_crs(config.PROJECT_CRS).geometry
    scored["candidate_centroid_lon"] = centroids_project.x.round(6).values
    scored["candidate_centroid_lat"] = centroids_project.y.round(6).values
    return scored


def add_v1_audit_fields(candidates: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calculate legacy v1 component fields for variance audit only."""
    audited = candidates.copy()
    audited["size_score"] = audited["area_acres"].astype(float).apply(calculate_v1_size_score)
    audited["grid_completeness_score"] = (
        audited["area_ratio_to_full_grid"].astype(float).clip(lower=0, upper=1) * 100
    )
    audited["submarket_score"] = calculate_submarket_scores(audited)
    audited["opportunity_score"] = audited["opportunity_zone_context"].astype(bool).map(
        {True: 100.0, False: 50.0}
    )
    audited["school_context_score"] = audited.apply(
        lambda row: 100.0 if has_clean_school_context(row) else 50.0,
        axis=1,
    )
    audited["geometry_score"] = audited["geometry_valid"].astype(bool).map(
        {True: 100.0, False: 0.0}
    )
    return audited


def add_score_fields(candidates: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calculate v2 component scores, weighted final score, and deterministic ranks."""
    scored = candidates.copy()
    scored["usable_area_score"] = scored["area_acres"].astype(float).apply(calculate_usable_area_score)
    scored["area_integrity_score"] = scored["area_ratio_to_full_grid"].astype(float).apply(
        calculate_area_integrity_score
    )
    scored["edge_integrity_score"] = scored["area_integrity_score"]
    scored["water_avoidance_score"] = scored["water_overlap_ratio"].astype(float).apply(
        calculate_water_avoidance_score
    )
    scored = add_waterbody_distance_fields(scored)
    scored["developable_geometry_score"] = (
        scored["usable_area_score"] * 0.45 + scored["area_integrity_score"] * 0.55
    )
    scored["constraint_avoidance_score"] = (
        scored["water_avoidance_score"] * 0.50
        + scored["edge_integrity_score"] * 0.25
        + scored["waterbody_distance_score"] * 0.25
    )
    scored = add_spatial_context_fields(scored)
    scored["submarket_context_score"] = calculate_submarket_scores(scored)
    scored["opportunity_incentive_score"] = scored["opportunity_zone_context"].astype(bool).map(
        {True: 100.0, False: 50.0}
    )

    scored["road_accessibility_score"] = float("nan")
    scored["flood_constraint_score"] = float("nan")
    scored["land_use_context_score"] = float("nan")
    scored["model_data_completeness_score"] = 50.0
    scored["model_data_completeness_note"] = (
        "Implemented: geometry, waterbody constraints, neutral spatial context, "
        "submarket context, Opportunity Zone incentive context. Missing: roads, "
        "FEMA flood, NCTCOG land use."
    )
    scored["data_availability_warning"] = DATA_AVAILABILITY_WARNING

    for component, weight in COMPONENT_WEIGHTS.items():
        contribution_name = component.replace("_score", "_contribution")
        scored[contribution_name] = scored[component].astype(float) * weight

    contribution_columns = [
        component.replace("_score", "_contribution") for component in COMPONENT_WEIGHTS
    ]
    scored["final_site_score"] = scored[contribution_columns].sum(axis=1)

    score_columns = [
        "usable_area_score",
        "area_integrity_score",
        "edge_integrity_score",
        "water_avoidance_score",
        "waterbody_distance_score",
        "distance_to_dallas_cbd_score",
        "candidate_cluster_score",
        "county_edge_score",
        *COMPONENT_WEIGHTS.keys(),
    ]
    scored[score_columns] = scored[score_columns].round(3)
    scored[contribution_columns] = scored[contribution_columns].round(6)
    scored["final_site_score"] = scored["final_site_score"].round(6)
    scored = add_centroid_lon_lat(scored)

    scored["scoring_model_version"] = SCORING_MODEL_VERSION
    scored["scoring_note"] = SCORING_NOTE
    scored = scored.sort_values(
        [
            "final_site_score",
            "developable_geometry_score",
            "constraint_avoidance_score",
            "spatial_context_score",
            "candidate_id",
        ],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)
    scored["candidate_rank"] = scored.index + 1
    return gpd.GeoDataFrame(scored, geometry="geometry", crs=candidates.crs)


def audit_component(
    df: pd.DataFrame,
    component_name: str,
    weight: float,
    recommendation: str,
    default_value: float | None = None,
) -> dict[str, object]:
    """Build one scoring component variance audit row."""
    series = pd.to_numeric(df[component_name], errors="coerce")
    missing = series.isna()
    non_missing = series[~missing]
    if non_missing.empty:
        stats = {"min": pd.NA, "max": pd.NA, "mean": pd.NA, "std": pd.NA, "unique": 0}
    else:
        stats = {
            "min": round(float(non_missing.min()), 3),
            "max": round(float(non_missing.max()), 3),
            "mean": round(float(non_missing.mean()), 3),
            "std": round(float(non_missing.std(ddof=0)), 3),
            "unique": int(non_missing.nunique()),
        }

    if default_value is None or len(series) == 0:
        percent_default = 0.0
    else:
        percent_default = round(float((series == default_value).mean() * 100), 3)

    return {
        "component_name": component_name,
        "weight": weight,
        "min": stats["min"],
        "max": stats["max"],
        "mean": stats["mean"],
        "std": stats["std"],
        "unique_value_count": stats["unique"],
        "percent_missing": round(float(missing.mean() * 100), 3) if len(series) else 0.0,
        "percent_default_value": percent_default,
        "recommendation": recommendation,
    }


def write_scoring_component_variance_audit(
    v1_audited: gpd.GeoDataFrame,
    ranked: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Write current/legacy and v2 component variance diagnostics."""
    rows = []
    legacy_recommendations = {
        "size_score": "replace",
        "grid_completeness_score": "reduce_weight",
        "submarket_score": "reduce_weight",
        "opportunity_score": "reduce_weight",
        "school_context_score": "remove",
        "geometry_score": "remove",
    }
    for component, weight in V1_COMPONENT_WEIGHTS.items():
        default = 100.0 if component in {"school_context_score", "geometry_score"} else None
        rows.append(
            audit_component(
                v1_audited,
                component,
                weight,
                legacy_recommendations[component],
                default_value=default,
            )
        )

    for component, weight in COMPONENT_WEIGHTS.items():
        rows.append(audit_component(ranked, component, weight, "keep"))

    for component, status in RECOMMENDED_COMPONENT_STATUS.items():
        ranked[component] = pd.NA
        rows.append(audit_component(ranked, component, 0.0, status))

    audit = pd.DataFrame(rows)
    audit.to_csv(config.SCORING_COMPONENT_VARIANCE_AUDIT_CSV, index=False)
    return audit


def build_score_components() -> pd.DataFrame:
    """Describe score components, weights, and neutral-use constraints."""
    rows = [
        {
            "component_name": "developable_geometry_score",
            "component_weight": COMPONENT_WEIGHTS["developable_geometry_score"],
            "implemented": True,
            "description": "Combines usable proxy footprint size and retained grid-cell integrity after Dallas County clipping.",
            "neutral_use_note": "Proxy geometry suitability only; not parcel valuation or development feasibility.",
        },
        {
            "component_name": "constraint_avoidance_score",
            "component_weight": COMPONENT_WEIGHTS["constraint_avoidance_score"],
            "implemented": True,
            "description": "Penalizes residual waterbody overlap below the disqualification threshold, proximity to staged Census waterbody polygons, and lower retained grid-cell integrity.",
            "neutral_use_note": "Screening QA constraint proxy only; not engineering, hydrologic, or legal due diligence.",
        },
        {
            "component_name": "spatial_context_score",
            "component_weight": COMPONENT_WEIGHTS["spatial_context_score"],
            "implemented": True,
            "description": "Combines neutral distance to a project-defined Downtown Dallas reference, local candidate cluster density, and distance from the Dallas County boundary.",
            "neutral_use_note": "Spatial organization proxy only; does not use demographics or protected-class variables.",
        },
        {
            "component_name": "submarket_context_score",
            "component_weight": COMPONENT_WEIGHTS["submarket_context_score"],
            "implemented": True,
            "description": "Uses neutral candidate supply distribution by analyst-defined ZCTA submarket with moderated scores.",
            "neutral_use_note": "Does not imply demand, rents, demographics, or investment performance.",
        },
        {
            "component_name": "opportunity_incentive_score",
            "component_weight": COMPONENT_WEIGHTS["opportunity_incentive_score"],
            "implemented": True,
            "description": "Small policy/incentive context factor based on Opportunity Zone overlap.",
            "neutral_use_note": "Incentive context only; not demographic targeting.",
        },
        {
            "component_name": "road_accessibility_score",
            "component_weight": 0.0,
            "implemented": False,
            "description": "Not implemented because TxDOT/OSM road network source is not staged in the local workflow.",
            "neutral_use_note": "Do not infer legal access or driveway access from this project version.",
        },
        {
            "component_name": "flood_constraint_score",
            "component_weight": 0.0,
            "implemented": False,
            "description": "Not implemented because FEMA NFHL is not staged in the local workflow.",
            "neutral_use_note": "Floodplain due diligence remains required before acquisition analysis.",
        },
        {
            "component_name": "land_use_context_score",
            "component_weight": 0.0,
            "implemented": False,
            "description": "Not implemented because NCTCOG land-use context is not staged in the local workflow.",
            "neutral_use_note": "Land use is not legal zoning; zoning validation remains required.",
        },
    ]
    return pd.DataFrame(rows)


def write_scoring_model_manifest() -> pd.DataFrame:
    """Write frozen v2 scoring model metadata for reproducibility QA."""
    weights_sum = round(sum(COMPONENT_WEIGHTS.values()), 6)
    if weights_sum != 1.0:
        raise ValueError(f"Scoring weights must sum to 1.0; found {weights_sum}.")

    manifest = pd.DataFrame(
        [
            {
                "model_version": SCORING_MODEL_VERSION,
                "scoring_weights": json.dumps(COMPONENT_WEIGHTS, sort_keys=True),
                "weights_sum": weights_sum,
                "waterbody_threshold": config.WATER_OVERLAP_RATIO_THRESHOLD,
                "edge_fragment_threshold": config.EDGE_FRAGMENT_MIN_AREA_RATIO,
                "missing_professional_variables": (
                    "road accessibility not implemented; FEMA flood not implemented; "
                    "NCTCOG land use not implemented"
                ),
                "deterministic_sort": (
                    "final_site_score desc; developable_geometry_score desc; "
                    "constraint_avoidance_score desc; spatial_context_score desc; "
                    "candidate_id asc final tie-breaker"
                ),
                "generated_at": pd.Timestamp.now("UTC").isoformat(),
            }
        ]
    )
    manifest.to_csv(config.SCORING_MODEL_MANIFEST_CSV, index=False)
    return manifest


def explain_top25_reason(row: pd.Series) -> str:
    """Create a short audit note explaining why a Top 25 candidate ranked high."""
    reasons = []
    if row["developable_geometry_score"] >= 85:
        reasons.append("strong proxy footprint integrity")
    if row["constraint_avoidance_score"] >= 85:
        reasons.append("low residual water/edge constraint penalty")
    if row["spatial_context_score"] >= 75:
        reasons.append("favorable neutral spatial context")
    if bool(row.get("opportunity_zone_context", False)):
        reasons.append("Opportunity Zone incentive context")
    if not reasons:
        reasons.append("balanced v2 component profile")
    return "; ".join(reasons)


def write_top25_scoring_audit(ranked_project: gpd.GeoDataFrame) -> pd.DataFrame:
    """Write a focused Top 25 scoring audit CSV."""
    top_25 = ranked_project.head(25).copy()
    top_25["ranking_notes"] = top_25.apply(explain_top25_reason, axis=1)
    columns = [
        "candidate_rank",
        "candidate_id",
        "final_site_score",
        "developable_geometry_score",
        "constraint_avoidance_score",
        "spatial_context_score",
        "submarket_context_score",
        "opportunity_incentive_score",
        "developable_geometry_contribution",
        "constraint_avoidance_contribution",
        "spatial_context_contribution",
        "submarket_context_contribution",
        "opportunity_incentive_contribution",
        "usable_area_score",
        "area_integrity_score",
        "water_avoidance_score",
        "distance_to_waterbody_m",
        "waterbody_distance_score",
        "edge_integrity_score",
        "distance_to_county_boundary_m",
        "county_edge_score",
        "distance_to_dallas_cbd_km",
        "distance_to_dallas_cbd_score",
        "local_candidate_count_5km",
        "candidate_cluster_score",
        "road_accessibility_score",
        "flood_constraint_score",
        "land_use_context_score",
        "model_data_completeness_score",
        "area_ratio_to_full_grid",
        "rule_edge_fragment",
        "water_overlap_ratio",
        "centroid_inside_water",
        "rule_waterbody_overlap",
        "failed_rule_count",
        "failed_rules",
        "primary_disqualification_reason",
        "submarket_name",
        "opportunity_zone_context",
        "school_district_context",
        "candidate_centroid_lon",
        "candidate_centroid_lat",
        "ranking_notes",
    ]
    audit = pd.DataFrame(top_25[columns])
    audit.to_csv(config.TOP25_SCORING_AUDIT_CSV, index=False)
    return audit


def export_outputs(
    ranked: gpd.GeoDataFrame,
    v1_audited: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Export ranked GeoJSON, CSV, score components, audits, top 25, and GeoPackage."""
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
    write_scoring_model_manifest()
    write_scoring_component_variance_audit(v1_audited, ranked_project)
    write_top25_scoring_audit(ranked_project)

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
    """Run the v2 professional proxy candidate scoring workflow."""
    validate_inputs()
    candidates = load_qualified_candidates()
    v1_audited = add_v1_audit_fields(candidates)
    ranked = add_score_fields(candidates)
    top_25, _ = export_outputs(ranked, v1_audited)

    min_score = round(float(ranked["final_site_score"].min()), 3)
    mean_score = round(float(ranked["final_site_score"].mean()), 3)
    max_score = round(float(ranked["final_site_score"].max()), 3)
    tie_count = int(ranked["final_site_score"].duplicated(keep=False).sum())

    print(f"Scoring model version: {SCORING_MODEL_VERSION}")
    print(f"Qualified input candidate count: {len(candidates)}")
    print(f"Ranked candidate count: {len(ranked)}")
    print(f"Top 25 exported count: {len(top_25)}")
    print(f"Final site score min/mean/max: {min_score} / {mean_score} / {max_score}")
    print(f"Candidates sharing rounded 3-decimal scores: {tie_count}")
    print(f"Output CSV path: {config.RANKED_SITE_CANDIDATES_CSV}")
    print(f"Output GeoJSON path: {config.RANKED_SITE_CANDIDATES_GEOJSON}")
    print(f"Top 25 GeoJSON path: {config.TOP_25_CANDIDATE_SITES_GEOJSON}")
    print(f"Score components CSV path: {config.CANDIDATE_SCORE_COMPONENTS_CSV}")
    print(f"Scoring model manifest path: {config.SCORING_MODEL_MANIFEST_CSV}")
    print(f"Scoring variance audit path: {config.SCORING_COMPONENT_VARIANCE_AUDIT_CSV}")
    print(f"Top 25 scoring audit path: {config.TOP25_SCORING_AUDIT_CSV}")
    print(f"Output GeoPackage path: {config.RANKED_CANDIDATES_GPKG}")


if __name__ == "__main__":
    main()
