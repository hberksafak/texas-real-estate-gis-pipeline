"""
Create an interactive Folium/Leaflet web map demo.

The map uses platform-ready GeoJSON exports from Milestone 9. Candidate
polygons remain analyst-defined grid proxies, not official parcels.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import folium
import geopandas as gpd
import pandas as pd
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry


MAP_TITLE = "Texas Real Estate Sourcing GIS Pipeline — DFW Candidate Screening Demo"
WEBMAP_NOTE = (
    "Candidate polygons are analyst-defined grid proxies, not official parcels. "
    "Scores are transparent proxy rankings for portfolio demonstration. School "
    "district context is neutral context only. Opportunity Zones are policy/"
    "incentive context only."
)

LAYER_SPECS = [
    {
        "layer_name": "dfw_cbsa_boundary",
        "display_name": "DFW CBSA Boundary",
        "filename": "dfw_cbsa_boundary.geojson",
        "default_visible": True,
        "style": {"color": "#334155", "weight": 2, "fillOpacity": 0.02},
        "notes": "Regional study area boundary.",
        "tooltip_fields": ["namelsad", "name"],
        "popup_fields": ["namelsad", "name", "geoid"],
    },
    {
        "layer_name": "dallas_county_boundary",
        "display_name": "Dallas County Boundary",
        "filename": "dallas_county_boundary.geojson",
        "default_visible": True,
        "style": {"color": "#111827", "weight": 3, "fillOpacity": 0.01},
        "notes": "Primary county focus boundary.",
        "tooltip_fields": ["name", "namelsad"],
        "popup_fields": ["name", "namelsad", "geoid"],
    },
    {
        "layer_name": "dfw_zcta_submarkets",
        "display_name": "ZCTA-Based Submarkets",
        "filename": "dfw_zcta_submarkets.geojson",
        "default_visible": True,
        "style": {"color": "#2563eb", "weight": 1.5, "fillColor": "#60a5fa", "fillOpacity": 0.14},
        "notes": "Analyst-defined ZCTA sector proxy submarkets.",
        "tooltip_fields": ["submarket_name"],
        "popup_fields": ["submarket_name", "zcta_count", "total_area_sq_km"],
    },
    {
        "layer_name": "dfw_opportunity_zones",
        "display_name": "Opportunity Zones",
        "filename": "dfw_opportunity_zones.geojson",
        "default_visible": False,
        "style": {"color": "#7c3aed", "weight": 1, "fillColor": "#a78bfa", "fillOpacity": 0.18},
        "notes": "Policy/incentive context only.",
        "tooltip_fields": ["geoid10", "tract"],
        "popup_fields": ["geoid10", "county", "tract", "state_name"],
    },
    {
        "layer_name": "dfw_school_districts",
        "display_name": "School District Context",
        "filename": "dfw_school_districts.geojson",
        "default_visible": False,
        "style": {"color": "#0f766e", "weight": 1, "fillColor": "#5eead4", "fillOpacity": 0.08},
        "notes": "Neutral education context only.",
        "tooltip_fields": ["name"],
        "popup_fields": ["name", "geoid", "lograde", "higrade"],
    },
    {
        "layer_name": "qualified_candidate_sites",
        "display_name": "Qualified Candidate Sites",
        "filename": "qualified_candidate_sites.geojson",
        "default_visible": False,
        "style": {"color": "#16a34a", "weight": 0.8, "fillColor": "#22c55e", "fillOpacity": 0.16},
        "notes": "Qualified analyst-defined proxy candidate polygons.",
        "tooltip_fields": ["candidate_id", "submarket_name"],
        "popup_fields": [
            "candidate_id",
            "area_acres",
            "submarket_name",
            "opportunity_zone_context",
            "school_district_name",
            "candidate_source",
            "is_official_parcel",
        ],
    },
    {
        "layer_name": "disqualified_candidate_sites",
        "display_name": "Disqualified Candidate Sites",
        "filename": "disqualified_candidate_sites.geojson",
        "default_visible": True,
        "style": {"color": "#dc2626", "weight": 1.2, "fillColor": "#f87171", "fillOpacity": 0.28},
        "notes": "Proxy candidate polygons that failed initial screening rules.",
        "tooltip_fields": ["candidate_id", "primary_disqualification_reason"],
        "popup_fields": [
            "candidate_id",
            "area_acres",
            "submarket_name",
            "failed_rule_count",
            "failed_rules",
            "primary_disqualification_reason",
            "screening_stage",
            "candidate_source",
            "is_official_parcel",
        ],
    },
    {
        "layer_name": "ranked_site_candidates",
        "display_name": "Ranked Candidate Sites",
        "filename": "ranked_site_candidates.geojson",
        "default_visible": False,
        "style": {"color": "#f59e0b", "weight": 0.9, "fillColor": "#fbbf24", "fillOpacity": 0.16},
        "notes": "All qualified candidates with transparent proxy scores.",
        "tooltip_fields": ["candidate_rank", "candidate_id", "final_site_score"],
        "popup_fields": [
            "candidate_id",
            "candidate_rank",
            "final_site_score",
            "area_acres",
            "submarket_name",
            "opportunity_zone_context",
            "school_district_name",
            "candidate_source",
            "is_official_parcel",
        ],
    },
    {
        "layer_name": "top_25_candidate_sites",
        "display_name": "Top 25 Candidate Sites",
        "filename": "top_25_candidate_sites.geojson",
        "default_visible": True,
        "style": {"color": "#ea580c", "weight": 2.2, "fillColor": "#fb923c", "fillOpacity": 0.48},
        "notes": "Top-ranked proxy candidate polygons emphasized for demo review.",
        "tooltip_fields": ["candidate_rank", "candidate_id", "final_site_score"],
        "popup_fields": [
            "candidate_id",
            "candidate_rank",
            "final_site_score",
            "area_acres",
            "submarket_name",
            "opportunity_zone_context",
            "school_district_name",
            "candidate_source",
            "is_official_parcel",
            "scoring_model_version",
        ],
    },
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


def load_platform_layer(filename: str) -> gpd.GeoDataFrame:
    """Load one platform-ready GeoJSON layer."""
    path = config.PLATFORM_EXPORT_GEOJSON_DIR / filename
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(config.PROJECT_CRS)
    elif str(gdf.crs).upper() != config.PROJECT_CRS:
        gdf = gdf.to_crs(config.PROJECT_CRS)
    return clean_polygonal_web_geometries(gdf)


def polygonal_part(geometry: BaseGeometry | None) -> BaseGeometry | None:
    """Keep only polygonal components for Folium polygon display."""
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


def clean_polygonal_web_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Remove non-polygonal geometry fragments from web map display layers."""
    cleaned = gdf.copy()
    cleaned["geometry"] = cleaned.geometry.apply(polygonal_part)
    cleaned = cleaned[cleaned.geometry.notna()]
    cleaned = cleaned[~cleaned.geometry.is_empty]
    return cleaned.reset_index(drop=True)


def layer_path(filename: str) -> Path:
    """Return the platform export path for a layer filename."""
    return config.PLATFORM_EXPORT_GEOJSON_DIR / filename


def simplify_for_web(gdf: gpd.GeoDataFrame, feature_count: int) -> gpd.GeoDataFrame:
    """Simplify larger polygon layers in-memory for responsive web display."""
    if feature_count < 100:
        return gdf

    tolerance_m = 80 if feature_count > 1_000 else 40
    simplified = gdf.to_crs(config.ANALYSIS_CRS).copy()
    simplified["geometry"] = simplified.geometry.simplify(
        tolerance=tolerance_m,
        preserve_topology=True,
    )
    simplified = simplified[simplified.geometry.notna()]
    simplified = simplified[~simplified.geometry.is_empty]
    return simplified.to_crs(config.PROJECT_CRS)


def union_geometry(gdf: gpd.GeoDataFrame):
    """Return a unioned geometry compatible with older/newer GeoPandas."""
    return gdf.geometry.union_all() if hasattr(gdf.geometry, "union_all") else gdf.geometry.unary_union


def calculate_map_center(layers: dict[str, gpd.GeoDataFrame]) -> tuple[float, float]:
    """Calculate a stable Dallas/DFW map center."""
    source = layers.get("dallas_county_boundary")
    if source is None:
        source = layers.get("dfw_cbsa_boundary")
    if source is None or source.empty:
        return 32.7767, -96.7970

    centroid = union_geometry(source.to_crs(config.ANALYSIS_CRS)).centroid
    centroid_gdf = gpd.GeoDataFrame(geometry=[centroid], crs=config.ANALYSIS_CRS).to_crs(
        config.PROJECT_CRS
    )
    point = centroid_gdf.geometry.iloc[0]
    return point.y, point.x


def available_fields(gdf: gpd.GeoDataFrame, fields: list[str]) -> list[str]:
    """Return fields present in the layer."""
    return [field for field in fields if field in gdf.columns]


def add_geojson_layer(
    fmap: folium.Map,
    gdf: gpd.GeoDataFrame,
    spec: dict[str, object],
) -> None:
    """Add one styled GeoJSON layer to a Folium map."""
    display_name = str(spec["display_name"])
    feature_group = folium.FeatureGroup(
        name=display_name,
        show=bool(spec["default_visible"]),
        overlay=True,
    )

    popup_fields = available_fields(gdf, list(spec["popup_fields"]))
    tooltip_fields = available_fields(gdf, list(spec["tooltip_fields"]))
    popup = (
        folium.GeoJsonPopup(
            fields=popup_fields,
            aliases=[field.replace("_", " ").title() for field in popup_fields],
            localize=True,
            labels=True,
            max_width=420,
        )
        if popup_fields
        else None
    )
    tooltip = (
        folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=[field.replace("_", " ").title() for field in tooltip_fields],
            localize=True,
            sticky=True,
        )
        if tooltip_fields
        else None
    )

    style = dict(spec["style"])
    folium.GeoJson(
        data=json.loads(gdf.to_json()),
        name=display_name,
        style_function=lambda _feature, style=style: style,
        popup=popup,
        tooltip=tooltip,
    ).add_to(feature_group)
    feature_group.add_to(fmap)


def add_map_caption(fmap: folium.Map) -> None:
    """Add title and limitations note to the generated HTML map."""
    fmap.get_root().header.add_child(folium.Element(f"<title>{MAP_TITLE}</title>"))
    caption_html = f"""
    <div style="
        position: fixed;
        top: 12px;
        left: 50px;
        z-index: 9999;
        max-width: 520px;
        padding: 10px 12px;
        background: rgba(255, 255, 255, 0.94);
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.16);
        font-family: Arial, sans-serif;
        color: #0f172a;
    ">
        <div style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">{MAP_TITLE}</div>
        <div style="font-size: 12px; line-height: 1.35;">{WEBMAP_NOTE}</div>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(caption_html))


def build_layer_summary(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Write the web map layer summary CSV."""
    summary = pd.DataFrame(rows)
    summary.to_csv(config.WEBMAP_LAYER_SUMMARY_CSV, index=False)
    return summary


def main() -> None:
    """Run the interactive web map creation workflow."""
    config.ensure_directories()

    loaded_layers: dict[str, gpd.GeoDataFrame] = {}
    summary_rows = []
    skipped_layers = []

    for spec in LAYER_SPECS:
        path = layer_path(str(spec["filename"]))
        layer_name = str(spec["layer_name"])
        if not path.exists():
            skipped_layers.append(layer_name)
            summary_rows.append(
                {
                    "layer_name": layer_name,
                    "input_path": str(path),
                    "feature_count": 0,
                    "added_to_map": False,
                    "default_visible": bool(spec["default_visible"]),
                    "notes": "Layer missing from platform export folder.",
                }
            )
            continue

        gdf = load_platform_layer(str(spec["filename"]))
        feature_count = int(len(gdf))
        loaded_layers[layer_name] = gdf
        summary_rows.append(
            {
                "layer_name": layer_name,
                "input_path": str(path),
                "feature_count": feature_count,
                "added_to_map": True,
                "default_visible": bool(spec["default_visible"]),
                "notes": spec["notes"],
            }
        )

    map_center = calculate_map_center(loaded_layers)
    fmap = folium.Map(
        location=map_center,
        zoom_start=9,
        tiles="CartoDB positron",
        control_scale=True,
    )

    for spec in LAYER_SPECS:
        layer_name = str(spec["layer_name"])
        if layer_name not in loaded_layers:
            continue
        gdf = simplify_for_web(loaded_layers[layer_name], len(loaded_layers[layer_name]))
        add_geojson_layer(fmap, gdf, spec)

    add_map_caption(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    config.INTERACTIVE_WEBMAP_HTML.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(config.INTERACTIVE_WEBMAP_HTML)
    build_layer_summary(summary_rows)

    added_layers = [row["layer_name"] for row in summary_rows if row["added_to_map"]]
    print(f"Map center: {round(map_center[0], 6)}, {round(map_center[1], 6)}")
    print("Layers added:")
    for layer_name in added_layers:
        print(f"- {layer_name}")
    print("Layers skipped/missing:")
    if skipped_layers:
        for layer_name in skipped_layers:
            print(f"- {layer_name}")
    else:
        print("- none")
    print(f"Web map HTML path: {config.INTERACTIVE_WEBMAP_HTML}")
    print(f"Web map summary CSV path: {config.WEBMAP_LAYER_SUMMARY_CSV}")


if __name__ == "__main__":
    main()
