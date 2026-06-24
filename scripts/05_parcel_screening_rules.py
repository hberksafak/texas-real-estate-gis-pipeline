"""
Build a candidate-site screening foundation using documented proxy polygons.

Official Dallas CAD parcel data is not used in this milestone. The workflow
creates analyst-defined grid proxy polygons inside Dallas County so screening
rules, context overlays, and audit outputs can be developed before parcel
acquisition.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry


GRID_SIZE_M = 1_000
EDGE_FRAGMENT_MIN_AREA_RATIO = 0.60
CENSUS_DALLAS_AREAWATER_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2025/AREAWATER/"
    "tl_2025_48113_areawater.zip"
)
WATERBODY_SOURCE = "U.S. Census TIGER/Line 2025 Area Water, Dallas County (48113)"
MIN_AREA_ACRES = 10
MAX_AREA_ACRES = 250
SQ_M_PER_ACRE = 4_046.8564224
CANDIDATE_SOURCE = "analyst_defined_grid_proxy"
PASSED_STAGE = "passed_initial_proxy_screening"
FAILED_STAGE = "failed_initial_proxy_screening"

SCHOOL_DISTRICT_NAME_FIELDS = (
    "name",
    "district_name",
    "district",
    "school_district",
    "namelsad",
    "unsdlea",
    "geoid",
)


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
    """Confirm required Milestone 7 input layers exist."""
    input_paths = [
        config.DALLAS_COUNTY_GEOJSON,
        config.DFW_SUBMARKETS_GEOJSON,
        config.DFW_OPPORTUNITY_ZONES_GEOJSON,
        config.DFW_SCHOOL_DISTRICTS_GEOJSON,
    ]
    missing = [str(path) for path in input_paths if not path.exists()]
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Milestone 7 requires existing boundary and context GeoJSON inputs. "
            "Run prior milestones first.\n"
            f"Missing files:\n{missing_text}"
        )


def to_project_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Standardize a layer to the final platform CRS."""
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


def polygonal_part(geometry: BaseGeometry | None) -> BaseGeometry | None:
    """Keep only polygonal components from clipped candidate geometry."""
    if geometry is None or geometry.is_empty:
        return None
    if isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry
    if isinstance(geometry, GeometryCollection):
        polygons = []
        for part in geometry.geoms:
            polygon = polygonal_part(part)
            if isinstance(polygon, Polygon):
                polygons.append(polygon)
            elif isinstance(polygon, MultiPolygon):
                polygons.extend(list(polygon.geoms))
        if not polygons:
            return None
        return MultiPolygon(polygons) if len(polygons) > 1 else polygons[0]
    return None


def clean_polygon_layer(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Repair geometries, remove empty geometry, and keep polygonal parts."""
    cleaned = gdf.copy()
    cleaned["geometry"] = cleaned.geometry.apply(repair_geometry).apply(polygonal_part)
    cleaned = cleaned[cleaned.geometry.notna()].copy()
    cleaned = cleaned[~cleaned.geometry.is_empty].copy()
    return cleaned.reset_index(drop=True)


def load_layer(path: Path) -> gpd.GeoDataFrame:
    """Read a GeoJSON layer and standardize CRS/geometry."""
    return clean_polygon_layer(to_project_crs(gpd.read_file(path)))


def download_file(url: str, output_path: Path) -> str:
    """Download a source file only when it is not already staged locally."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        return "skipped"

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    with output_path.open("wb") as output_file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                output_file.write(chunk)
    return "downloaded"


def union_geometry(gdf: gpd.GeoDataFrame) -> BaseGeometry:
    """Return a single unioned geometry for a GeoDataFrame."""
    return (
        gdf.geometry.union_all()
        if hasattr(gdf.geometry, "union_all")
        else gdf.geometry.unary_union
    )


def load_or_prepare_waterbodies(dallas_county: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Stage Census Area Water and export a clipped Dallas County waterbody layer."""
    status = download_file(CENSUS_DALLAS_AREAWATER_URL, config.DALLAS_AREAWATER_ZIP)
    print(f"Census Dallas Area Water ZIP {status}: {config.DALLAS_AREAWATER_ZIP}")

    waterbodies = gpd.read_file(f"zip://{config.DALLAS_AREAWATER_ZIP}")
    waterbodies = clean_polygon_layer(to_project_crs(waterbodies))
    dallas_project = dallas_county.to_crs(config.PROJECT_CRS)
    clipped = gpd.overlay(
        waterbodies,
        dallas_project[["geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    clipped = clean_polygon_layer(to_project_crs(clipped))
    clipped["waterbody_source"] = WATERBODY_SOURCE

    config.DALLAS_WATERBODIES_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
    clipped.to_crs(config.PROJECT_CRS).to_file(
        config.DALLAS_WATERBODIES_GEOJSON,
        driver="GeoJSON",
        index=False,
    )
    return clipped.to_crs(config.ANALYSIS_CRS)


def create_candidate_grid(dallas_county: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Create a regular grid clipped to Dallas County in the analysis CRS."""
    county_analysis = dallas_county.to_crs(config.ANALYSIS_CRS)
    county_geometry = union_geometry(county_analysis)
    minx, miny, maxx, maxy = county_geometry.bounds

    cells = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cell = box(x, y, min(x + GRID_SIZE_M, maxx), min(y + GRID_SIZE_M, maxy))
            if cell.intersects(county_geometry):
                cells.append(cell)
            y += GRID_SIZE_M
        x += GRID_SIZE_M

    grid = gpd.GeoDataFrame({"geometry": cells}, geometry="geometry", crs=config.ANALYSIS_CRS)
    clipped = gpd.clip(grid, county_analysis[["geometry"]])
    clipped = clean_polygon_layer(clipped)
    clipped["area_sq_m"] = clipped.geometry.area.round(3)
    clipped = clipped[clipped["area_sq_m"] > 0].copy().reset_index(drop=True)
    clipped["full_grid_area_sq_m"] = GRID_SIZE_M * GRID_SIZE_M
    clipped["area_ratio_to_full_grid"] = (
        clipped["area_sq_m"] / clipped["full_grid_area_sq_m"]
    ).round(6)
    clipped["rule_edge_fragment"] = (
        clipped["area_ratio_to_full_grid"] < EDGE_FRAGMENT_MIN_AREA_RATIO
    )
    clipped["candidate_id"] = [
        f"CAND_{index:06d}" for index in range(1, len(clipped) + 1)
    ]
    clipped["candidate_source"] = CANDIDATE_SOURCE
    clipped["is_official_parcel"] = False
    clipped["area_acres"] = (clipped["area_sq_m"] / SQ_M_PER_ACRE).round(3)
    clipped["geometry_valid"] = clipped.geometry.is_valid
    return clipped[
        [
            "candidate_id",
            "candidate_source",
            "is_official_parcel",
            "area_sq_m",
            "full_grid_area_sq_m",
            "area_ratio_to_full_grid",
            "rule_edge_fragment",
            "area_acres",
            "geometry_valid",
            "geometry",
        ]
    ]


def largest_overlap_assignment(
    candidates: gpd.GeoDataFrame,
    context: gpd.GeoDataFrame,
    context_fields: list[str],
) -> pd.DataFrame:
    """Assign context fields by largest overlap area per candidate."""
    if context.empty:
        return pd.DataFrame({"candidate_id": candidates["candidate_id"]})

    overlay = gpd.overlay(
        candidates[["candidate_id", "geometry"]],
        context[context_fields + ["geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    if overlay.empty:
        return pd.DataFrame({"candidate_id": candidates["candidate_id"]})

    overlay = overlay.to_crs(config.ANALYSIS_CRS)
    overlay["overlap_area_sq_m"] = overlay.geometry.area
    idx = overlay.groupby("candidate_id")["overlap_area_sq_m"].idxmax()
    assigned = overlay.loc[idx, ["candidate_id"] + context_fields].copy()
    return assigned.reset_index(drop=True)


def assign_submarkets(
    candidates: gpd.GeoDataFrame,
    submarkets: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Assign submarket ID and name by largest polygon overlap."""
    assignments = largest_overlap_assignment(
        candidates,
        submarkets.to_crs(config.ANALYSIS_CRS),
        ["submarket_id", "submarket_name"],
    )
    enriched = candidates.merge(assignments, on="candidate_id", how="left")
    return gpd.GeoDataFrame(enriched, geometry="geometry", crs=candidates.crs)


def assign_opportunity_zone_context(
    candidates: gpd.GeoDataFrame,
    opportunity_zones: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Mark candidates that overlap any Opportunity Zone geometry."""
    enriched = candidates.copy()
    enriched["opportunity_zone_context"] = False
    enriched["opportunity_zone_overlap"] = False

    if opportunity_zones.empty:
        return enriched

    overlay = gpd.overlay(
        candidates[["candidate_id", "geometry"]],
        opportunity_zones[["geometry"]].to_crs(config.ANALYSIS_CRS),
        how="intersection",
        keep_geom_type=False,
    )
    if overlay.empty:
        return enriched

    overlay = overlay.to_crs(config.ANALYSIS_CRS)
    overlay["overlap_area_sq_m"] = overlay.geometry.area
    overlapping_ids = set(overlay.loc[overlay["overlap_area_sq_m"] > 0, "candidate_id"])
    enriched["opportunity_zone_context"] = enriched["candidate_id"].isin(overlapping_ids)
    enriched["opportunity_zone_overlap"] = enriched["opportunity_zone_context"]
    return enriched


def detect_school_district_name_field(school_districts: gpd.GeoDataFrame) -> str | None:
    """Find a reasonable district-name field in a school district layer."""
    lower_lookup = {column.lower(): column for column in school_districts.columns}
    for field in SCHOOL_DISTRICT_NAME_FIELDS:
        if field in lower_lookup:
            return lower_lookup[field]

    for column in school_districts.columns:
        lower = column.lower()
        if "name" in lower or "district" in lower:
            return column
    return None


def assign_school_district_context(
    candidates: gpd.GeoDataFrame,
    school_districts: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Assign school district context by largest overlap area."""
    enriched = candidates.copy()
    enriched["school_district_context"] = False
    enriched["school_district_name"] = "unknown"

    if school_districts.empty:
        return enriched

    name_field = detect_school_district_name_field(school_districts)
    context = school_districts.to_crs(config.ANALYSIS_CRS).copy()
    if name_field is None:
        context["school_district_name"] = "unknown"
    else:
        context["school_district_name"] = context[name_field].fillna("unknown").astype(str)

    assignments = largest_overlap_assignment(
        candidates,
        context,
        ["school_district_name"],
    )
    enriched = enriched.merge(assignments, on="candidate_id", how="left", suffixes=("", "_assigned"))
    if "school_district_name_assigned" in enriched.columns:
        enriched["school_district_name"] = enriched["school_district_name_assigned"].fillna(
            enriched["school_district_name"]
        )
        enriched = enriched.drop(columns="school_district_name_assigned")
    enriched["school_district_context"] = enriched["school_district_name"].ne("unknown")
    return gpd.GeoDataFrame(enriched, geometry="geometry", crs=candidates.crs)


def assign_waterbody_exclusion_metrics(
    candidates: gpd.GeoDataFrame,
    waterbodies: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Calculate candidate overlap with official Census Area Water polygons."""
    enriched = candidates.copy()
    enriched["water_overlap_sq_m"] = 0.0
    enriched["water_overlap_ratio"] = 0.0
    enriched["centroid_inside_water"] = False

    if waterbodies.empty:
        enriched["rule_waterbody_overlap"] = False
        return gpd.GeoDataFrame(enriched, geometry="geometry", crs=candidates.crs)

    water_analysis = clean_polygon_layer(waterbodies.to_crs(config.ANALYSIS_CRS))
    if water_analysis.empty:
        enriched["rule_waterbody_overlap"] = False
        return gpd.GeoDataFrame(enriched, geometry="geometry", crs=candidates.crs)

    water_union = union_geometry(water_analysis)
    centroids = enriched.geometry.centroid
    enriched["centroid_inside_water"] = centroids.apply(
        lambda point: bool(water_union.covers(point))
    )

    overlay = gpd.overlay(
        enriched[["candidate_id", "geometry"]],
        water_analysis[["geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    if not overlay.empty:
        overlay = clean_polygon_layer(overlay.to_crs(config.ANALYSIS_CRS))
        overlay["water_overlap_sq_m"] = overlay.geometry.area
        water_overlap = overlay.groupby("candidate_id")["water_overlap_sq_m"].sum()
        enriched["water_overlap_sq_m"] = (
            enriched["candidate_id"].map(water_overlap).fillna(0.0).round(3)
        )

    enriched["water_overlap_ratio"] = (
        enriched["water_overlap_sq_m"] / enriched["area_sq_m"].replace(0, pd.NA)
    ).fillna(0.0).round(6)
    enriched["rule_waterbody_overlap"] = (
        enriched["centroid_inside_water"].astype(bool)
        | (
            enriched["water_overlap_ratio"].astype(float)
            >= config.WATER_OVERLAP_RATIO_THRESHOLD
        )
    )
    return gpd.GeoDataFrame(enriched, geometry="geometry", crs=candidates.crs)


def failed_rules_for_candidate(row: pd.Series) -> list[str]:
    """Evaluate transparent initial proxy screening rules for one candidate."""
    failed_rules = []
    if not bool(row["geometry_valid"]):
        failed_rules.append("rule_geometry_valid")
    if row["area_acres"] < MIN_AREA_ACRES:
        failed_rules.append("rule_min_area")
    if row["area_acres"] > MAX_AREA_ACRES:
        failed_rules.append("rule_max_area")
    if bool(row.get("rule_edge_fragment", False)):
        failed_rules.append("rule_edge_fragment")
    if bool(row.get("rule_waterbody_overlap", False)):
        failed_rules.append("rule_waterbody_overlap")
    if pd.isna(row["submarket_id"]) or pd.isna(row["submarket_name"]):
        failed_rules.append("rule_has_submarket")
    return failed_rules


def apply_screening_rules(candidates: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Apply initial proxy screening rules and create audit fields."""
    screened = candidates.copy()
    failed_rule_lists = screened.apply(failed_rules_for_candidate, axis=1)
    screened["failed_rule_count"] = failed_rule_lists.apply(len)
    screened["failed_rules"] = failed_rule_lists.apply(lambda rules: ";".join(rules))
    screened["primary_disqualification_reason"] = failed_rule_lists.apply(
        lambda rules: rules[0] if rules else ""
    )
    screened["qualified"] = screened["failed_rule_count"] == 0
    screened["screening_stage"] = screened["qualified"].map(
        {True: PASSED_STAGE, False: FAILED_STAGE}
    )
    return gpd.GeoDataFrame(screened, geometry="geometry", crs=candidates.crs)


def build_audit_table(candidates: gpd.GeoDataFrame) -> pd.DataFrame:
    """Create one audit row per candidate."""
    columns = [
        "candidate_id",
        "qualified",
        "failed_rule_count",
        "failed_rules",
        "primary_disqualification_reason",
        "screening_stage",
        "area_acres",
        "full_grid_area_sq_m",
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
    ]
    return pd.DataFrame(candidates[columns]).sort_values("candidate_id")


def build_candidate_summary(candidates: gpd.GeoDataFrame) -> pd.DataFrame:
    """Build a one-row candidate screening summary."""
    total_candidates = int(len(candidates))
    qualified_candidates = int(candidates["qualified"].sum())
    disqualified_candidates = total_candidates - qualified_candidates
    qualification_rate = (
        round(qualified_candidates / total_candidates, 4) if total_candidates else 0.0
    )
    waterbody_failed = candidates["rule_waterbody_overlap"].astype(bool)
    summary = {
        "total_candidates": total_candidates,
        "qualified_candidates": qualified_candidates,
        "disqualified_candidates": disqualified_candidates,
        "qualification_rate": qualification_rate,
        "min_area_acres": round(float(candidates["area_acres"].min()), 3),
        "max_area_acres": round(float(candidates["area_acres"].max()), 3),
        "mean_area_acres": round(float(candidates["area_acres"].mean()), 3),
        "edge_fragment_candidate_count": int(
            (candidates["area_ratio_to_full_grid"] < EDGE_FRAGMENT_MIN_AREA_RATIO).sum()
        ),
        "min_area_ratio_to_full_grid": round(
            float(candidates["area_ratio_to_full_grid"].min()), 6
        ),
        "mean_area_ratio_to_full_grid": round(
            float(candidates["area_ratio_to_full_grid"].mean()), 6
        ),
        "max_area_ratio_to_full_grid": round(
            float(candidates["area_ratio_to_full_grid"].max()), 6
        ),
        "waterbody_disqualified_candidate_count": int(waterbody_failed.sum()),
        "centroid_inside_water_count": int(
            candidates["centroid_inside_water"].astype(bool).sum()
        ),
        "water_overlap_candidate_count": int(
            (candidates["water_overlap_sq_m"].astype(float) > 0).sum()
        ),
        "water_overlap_threshold": config.WATER_OVERLAP_RATIO_THRESHOLD,
        "max_water_overlap_ratio": round(
            float(candidates["water_overlap_ratio"].astype(float).max()), 6
        ),
        "opportunity_zone_candidate_count": int(
            candidates["opportunity_zone_context"].sum()
        ),
        "school_district_context_count": int(candidates["school_district_context"].sum()),
        "candidate_source": CANDIDATE_SOURCE,
        "is_official_parcel": False,
    }
    return pd.DataFrame([summary])


def export_outputs(candidates: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Export candidate GeoJSON, audit CSV, summary CSV, and GeoPackage outputs."""
    candidates_project = candidates.to_crs(config.PROJECT_CRS)
    qualified = candidates_project[candidates_project["qualified"]].copy()
    disqualified = candidates_project[~candidates_project["qualified"]].copy()

    candidates_project.to_file(
        config.PARCEL_SCREENING_CANDIDATES_GEOJSON,
        driver="GeoJSON",
        index=False,
    )
    qualified.to_file(config.QUALIFIED_CANDIDATES_GEOJSON, driver="GeoJSON", index=False)
    disqualified.to_file(
        config.DISQUALIFIED_CANDIDATES_GEOJSON,
        driver="GeoJSON",
        index=False,
    )

    audit = build_audit_table(candidates_project)
    summary = build_candidate_summary(candidates_project)
    audit.to_csv(config.DISQUALIFICATION_AUDIT_CSV, index=False)
    summary.to_csv(config.CANDIDATE_SUMMARY_CSV, index=False)

    if config.PARCEL_SCREENING_GPKG.exists():
        config.PARCEL_SCREENING_GPKG.unlink()

    candidates_project.to_file(
        config.PARCEL_SCREENING_GPKG,
        layer="parcel_screening_candidates",
        driver="GPKG",
        index=False,
    )
    qualified.to_file(
        config.PARCEL_SCREENING_GPKG,
        layer="qualified_candidate_sites",
        driver="GPKG",
        index=False,
    )
    disqualified.to_file(
        config.PARCEL_SCREENING_GPKG,
        layer="disqualified_candidate_sites",
        driver="GPKG",
        index=False,
    )
    return audit, summary


def main() -> None:
    """Run the candidate-site proxy screening foundation workflow."""
    config.ensure_directories()
    validate_inputs()

    dallas_county = load_layer(config.DALLAS_COUNTY_GEOJSON)
    submarkets = load_layer(config.DFW_SUBMARKETS_GEOJSON)
    opportunity_zones = load_layer(config.DFW_OPPORTUNITY_ZONES_GEOJSON)
    school_districts = load_layer(config.DFW_SCHOOL_DISTRICTS_GEOJSON)
    waterbodies = load_or_prepare_waterbodies(dallas_county)

    candidates = create_candidate_grid(dallas_county)
    candidates = assign_submarkets(candidates, submarkets)
    candidates = assign_opportunity_zone_context(candidates, opportunity_zones)
    candidates = assign_school_district_context(candidates, school_districts)
    candidates = assign_waterbody_exclusion_metrics(candidates, waterbodies)
    candidates = apply_screening_rules(candidates)

    _, summary = export_outputs(candidates)
    summary_row = summary.iloc[0]

    print(f"Total candidate count: {summary_row['total_candidates']}")
    print(f"Qualified candidate count: {summary_row['qualified_candidates']}")
    print(f"Disqualified candidate count: {summary_row['disqualified_candidates']}")
    print(f"Qualification rate: {summary_row['qualification_rate']}")
    print(f"Edge fragment candidate count: {summary_row['edge_fragment_candidate_count']}")
    print(
        "Waterbody-disqualified candidate count: "
        f"{summary_row['waterbody_disqualified_candidate_count']}"
    )
    print(
        "Waterbody overlap threshold: "
        f"{summary_row['water_overlap_threshold']}"
    )
    print("Output GeoJSON paths:")
    print(f"- {config.PARCEL_SCREENING_CANDIDATES_GEOJSON}")
    print(f"- {config.QUALIFIED_CANDIDATES_GEOJSON}")
    print(f"- {config.DISQUALIFIED_CANDIDATES_GEOJSON}")
    print(f"- {config.DALLAS_WATERBODIES_GEOJSON}")
    print(f"Audit CSV path: {config.DISQUALIFICATION_AUDIT_CSV}")
    print(f"Candidate summary CSV path: {config.CANDIDATE_SUMMARY_CSV}")
    print(f"GeoPackage path: {config.PARCEL_SCREENING_GPKG}")


if __name__ == "__main__":
    main()
