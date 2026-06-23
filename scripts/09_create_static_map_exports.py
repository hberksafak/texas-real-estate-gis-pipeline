"""
Create static portfolio map exports from platform-ready GeoJSON layers.

The maps support portfolio screenshots, case-study visuals, and optional QGIS
refinement. Candidate polygons remain analyst-defined grid proxies, not
official parcels.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType

os.environ.setdefault("MPLCONFIGDIR", "/tmp/texas_real_estate_gis_pipeline_mpl")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry


MAP_NOTE = (
    "Candidate polygons are analyst-defined grid proxies, not official parcels. "
    "Scores are proxy rankings for portfolio demonstration."
)

LAYER_FILES = {
    "dallas_county_boundary": "dallas_county_boundary.geojson",
    "dfw_cbsa_boundary": "dfw_cbsa_boundary.geojson",
    "dfw_zcta_submarkets": "dfw_zcta_submarkets.geojson",
    "dfw_opportunity_zones": "dfw_opportunity_zones.geojson",
    "dfw_school_districts": "dfw_school_districts.geojson",
    "ranked_site_candidates": "ranked_site_candidates.geojson",
    "top_25_candidate_sites": "top_25_candidate_sites.geojson",
}

MAP_OUTPUTS = {
    "dfw_study_area_overview": {
        "title": "DFW Study Area Overview",
        "png": "dfw_study_area_overview.png",
        "pdf": "dfw_study_area_overview.pdf",
        "purpose": "Portfolio overview of DFW study area, Dallas County focus, submarkets, and context overlays.",
        "layers": [
            "dfw_cbsa_boundary",
            "dallas_county_boundary",
            "dfw_zcta_submarkets",
            "dfw_opportunity_zones",
            "dfw_school_districts",
        ],
    },
    "dallas_candidate_screening_map": {
        "title": "Dallas Candidate Screening and Ranked Sites",
        "png": "dallas_candidate_screening_map.png",
        "pdf": "dallas_candidate_screening_map.pdf",
        "purpose": "Screening map showing ranked proxy candidates and emphasized top-ranked sites in Dallas County.",
        "layers": [
            "dallas_county_boundary",
            "dfw_zcta_submarkets",
            "ranked_site_candidates",
            "top_25_candidate_sites",
        ],
    },
    "top_25_candidate_sites_map": {
        "title": "Top 25 Candidate Sites Close-Up",
        "png": "top_25_candidate_sites_map.png",
        "pdf": "top_25_candidate_sites_map.pdf",
        "purpose": "Close-up portfolio map of the top 25 ranked proxy candidate sites.",
        "layers": [
            "dallas_county_boundary",
            "dfw_zcta_submarkets",
            "ranked_site_candidates",
            "top_25_candidate_sites",
        ],
    },
}


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


def polygonal_part(geometry: BaseGeometry | None) -> BaseGeometry | None:
    """Keep only polygonal geometry for static map display."""
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


def load_platform_layer(layer_name: str) -> gpd.GeoDataFrame:
    """Load one platform GeoJSON layer and reproject to the analysis CRS."""
    path = config.PLATFORM_EXPORT_GEOJSON_DIR / LAYER_FILES[layer_name]
    if not path.exists():
        raise FileNotFoundError(f"Missing platform layer: {path}")

    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(config.PROJECT_CRS)
    elif str(gdf.crs).upper() != config.PROJECT_CRS:
        gdf = gdf.to_crs(config.PROJECT_CRS)

    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.apply(polygonal_part)
    gdf = gdf[gdf.geometry.notna()]
    gdf = gdf[~gdf.geometry.is_empty]
    return gdf.to_crs(config.ANALYSIS_CRS).reset_index(drop=True)


def load_layers() -> dict[str, gpd.GeoDataFrame]:
    """Load all required static map layers."""
    return {layer_name: load_platform_layer(layer_name) for layer_name in LAYER_FILES}


def set_extent(ax, gdf: gpd.GeoDataFrame, pad_ratio: float = 0.08) -> None:
    """Set an axis extent around a layer with proportional padding."""
    minx, miny, maxx, maxy = gdf.total_bounds
    width = maxx - minx
    height = maxy - miny
    pad = max(width, height) * pad_ratio
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)


def add_scale_bar(ax, length_km: int = 20) -> None:
    """Add a simple projected-coordinate scale bar."""
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    x = x_min + (x_max - x_min) * 0.06
    y = y_min + (y_max - y_min) * 0.06
    length_m = length_km * 1_000
    ax.plot([x, x + length_m], [y, y], color="#111827", linewidth=3, solid_capstyle="butt")
    ax.text(
        x + length_m / 2,
        y + (y_max - y_min) * 0.018,
        f"{length_km} km",
        ha="center",
        va="bottom",
        fontsize=8,
        color="#111827",
    )


def add_north_arrow(ax) -> None:
    """Add a small north arrow."""
    ax.annotate(
        "N",
        xy=(0.955, 0.88),
        xytext=(0.955, 0.78),
        xycoords="axes fraction",
        arrowprops={"facecolor": "#111827", "edgecolor": "#111827", "width": 3, "headwidth": 9},
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="#111827",
    )


def add_title_and_note(fig, title: str) -> None:
    """Add title, subtitle, and limitation note."""
    fig.suptitle(title, fontsize=18, fontweight="bold", x=0.08, ha="left", y=0.965)
    fig.text(
        0.08,
        0.925,
        "Texas Real Estate Sourcing GIS Pipeline & Parcel Screening System",
        fontsize=10,
        color="#334155",
        ha="left",
    )
    fig.text(0.08, 0.035, MAP_NOTE, fontsize=8.5, color="#475569", ha="left")


def finalize_map(fig, ax, title: str, png_path: Path, pdf_path: Path) -> None:
    """Apply final map formatting and save PNG/PDF outputs."""
    add_title_and_note(fig, title)
    add_scale_bar(ax)
    add_north_arrow(ax)
    ax.set_axis_off()
    fig.savefig(png_path, dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_study_area(layers: dict[str, gpd.GeoDataFrame], png_path: Path, pdf_path: Path) -> None:
    """Create DFW study area overview map."""
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_facecolor("#f8fafc")

    layers["dfw_cbsa_boundary"].plot(ax=ax, color="#f8fafc", edgecolor="#334155", linewidth=1.8)
    layers["dfw_school_districts"].boundary.plot(ax=ax, color="#94a3b8", linewidth=0.25, alpha=0.45)
    layers["dfw_opportunity_zones"].plot(ax=ax, color="#a78bfa", edgecolor="#7c3aed", linewidth=0.25, alpha=0.22)
    layers["dfw_zcta_submarkets"].plot(ax=ax, column="submarket_name", cmap="tab20", alpha=0.22, linewidth=0.5, edgecolor="#2563eb")
    layers["dallas_county_boundary"].plot(ax=ax, color="none", edgecolor="#111827", linewidth=2.4)

    for _, row in layers["dfw_zcta_submarkets"].iterrows():
        point = row.geometry.representative_point()
        ax.text(point.x, point.y, row["submarket_name"], fontsize=7.5, color="#1e293b", ha="center", va="center")

    set_extent(ax, layers["dfw_cbsa_boundary"], pad_ratio=0.04)
    handles = [
        Patch(facecolor="#f8fafc", edgecolor="#334155", label="DFW CBSA boundary"),
        Patch(facecolor="none", edgecolor="#111827", label="Dallas County boundary"),
        Patch(facecolor="#60a5fa", edgecolor="#2563eb", alpha=0.35, label="ZCTA submarket proxy"),
        Patch(facecolor="#a78bfa", edgecolor="#7c3aed", alpha=0.35, label="Opportunity Zones"),
        Line2D([0], [0], color="#94a3b8", linewidth=1, label="School district context"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=True, framealpha=0.94, fontsize=8)
    finalize_map(fig, ax, MAP_OUTPUTS["dfw_study_area_overview"]["title"], png_path, pdf_path)


def plot_candidate_screening(layers: dict[str, gpd.GeoDataFrame], png_path: Path, pdf_path: Path) -> None:
    """Create Dallas candidate screening and ranked sites map."""
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_facecolor("#f8fafc")

    layers["dfw_zcta_submarkets"].plot(ax=ax, color="#e0f2fe", edgecolor="#93c5fd", linewidth=0.35, alpha=0.45)
    layers["ranked_site_candidates"].plot(
        ax=ax,
        column="final_site_score",
        cmap="YlOrBr",
        alpha=0.34,
        linewidth=0,
        legend=True,
        legend_kwds={"label": "Final proxy score", "shrink": 0.58},
    )
    layers["top_25_candidate_sites"].plot(ax=ax, color="#fb923c", edgecolor="#9a3412", linewidth=1.2, alpha=0.78)
    layers["dallas_county_boundary"].plot(ax=ax, color="none", edgecolor="#111827", linewidth=2.0)

    set_extent(ax, layers["dallas_county_boundary"], pad_ratio=0.05)
    handles = [
        Patch(facecolor="#e0f2fe", edgecolor="#93c5fd", alpha=0.45, label="ZCTA submarket proxy"),
        Patch(facecolor="#facc15", edgecolor="none", alpha=0.45, label="Ranked qualified candidates"),
        Patch(facecolor="#fb923c", edgecolor="#9a3412", alpha=0.78, label="Top 25 candidates"),
        Patch(facecolor="none", edgecolor="#111827", label="Dallas County boundary"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=True, framealpha=0.94, fontsize=8)
    finalize_map(fig, ax, MAP_OUTPUTS["dallas_candidate_screening_map"]["title"], png_path, pdf_path)


def plot_top_25(layers: dict[str, gpd.GeoDataFrame], png_path: Path, pdf_path: Path) -> None:
    """Create top 25 candidate close-up map."""
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_facecolor("#f8fafc")

    layers["dfw_zcta_submarkets"].plot(ax=ax, color="#e5e7eb", edgecolor="#cbd5e1", linewidth=0.35, alpha=0.55)
    layers["ranked_site_candidates"].plot(ax=ax, color="#fed7aa", edgecolor="none", alpha=0.18)
    layers["top_25_candidate_sites"].plot(
        ax=ax,
        column="final_site_score",
        cmap="Oranges",
        edgecolor="#7c2d12",
        linewidth=1.2,
        alpha=0.86,
        legend=True,
        legend_kwds={"label": "Top 25 proxy score", "shrink": 0.58},
    )
    layers["dallas_county_boundary"].plot(ax=ax, color="none", edgecolor="#111827", linewidth=1.8)

    label_layer = layers["top_25_candidate_sites"].sort_values("candidate_rank").head(12)
    for _, row in label_layer.iterrows():
        point = row.geometry.representative_point()
        ax.text(point.x, point.y, str(int(row["candidate_rank"])), fontsize=7.5, fontweight="bold", color="#111827", ha="center", va="center")

    set_extent(ax, layers["top_25_candidate_sites"], pad_ratio=0.20)
    handles = [
        Patch(facecolor="#e5e7eb", edgecolor="#cbd5e1", alpha=0.55, label="Submarket context"),
        Patch(facecolor="#fed7aa", edgecolor="none", alpha=0.3, label="Ranked candidates"),
        Patch(facecolor="#fb923c", edgecolor="#7c2d12", alpha=0.86, label="Top 25 candidates"),
        Patch(facecolor="none", edgecolor="#111827", label="Dallas County boundary"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=True, framealpha=0.94, fontsize=8)
    finalize_map(fig, ax, MAP_OUTPUTS["top_25_candidate_sites_map"]["title"], png_path, pdf_path)


def build_summary(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Write the static map export summary CSV."""
    summary = pd.DataFrame(rows)
    summary.to_csv(config.TABLES_DIR / "static_map_export_summary.csv", index=False)
    return summary


def main() -> None:
    """Run static portfolio map export workflow."""
    config.ensure_directories()
    layers = load_layers()

    output_rows = []
    map_functions = {
        "dfw_study_area_overview": plot_study_area,
        "dallas_candidate_screening_map": plot_candidate_screening,
        "top_25_candidate_sites_map": plot_top_25,
    }

    for map_name, map_config in MAP_OUTPUTS.items():
        png_path = config.MAPS_PNG_DIR / map_config["png"]
        pdf_path = config.MAPS_PDF_DIR / map_config["pdf"]
        png_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        map_functions[map_name](layers, png_path, pdf_path)
        output_rows.append(
            {
                "map_name": map_name,
                "png_path": str(png_path),
                "pdf_path": str(pdf_path),
                "layers_used": ";".join(map_config["layers"]),
                "output_purpose": map_config["purpose"],
                "status": "exported",
                "notes": MAP_NOTE,
            }
        )

    summary = build_summary(output_rows)
    print("Maps exported:")
    for _, row in summary.iterrows():
        print(f"- {row['map_name']}: {row['png_path']} | {row['pdf_path']}")
    print(f"Static map summary CSV path: {config.TABLES_DIR / 'static_map_export_summary.csv'}")


if __name__ == "__main__":
    main()
