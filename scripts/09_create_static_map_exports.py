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
from matplotlib.patches import Patch, Rectangle
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry

try:
    import contextily as ctx
except ImportError:
    ctx = None


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
        "title": "Top 25 Ranked Candidate Sites",
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


def extent_from_bounds(
    bounds: tuple[float, float, float, float],
    pad_ratio: float,
    min_pad_m: float,
    target_aspect: float,
) -> tuple[float, float, float, float]:
    """Build a padded extent with a fixed plotting aspect ratio."""
    minx, miny, maxx, maxy = bounds
    width = max(maxx - minx, 1_000)
    height = max(maxy - miny, 1_000)
    pad_x = max(width * pad_ratio, min_pad_m)
    pad_y = max(height * pad_ratio, min_pad_m)
    xmin, xmax = minx - pad_x, maxx + pad_x
    ymin, ymax = miny - pad_y, maxy + pad_y

    extent_width = xmax - xmin
    extent_height = ymax - ymin
    center_x = (xmin + xmax) / 2
    center_y = (ymin + ymax) / 2
    if extent_width / extent_height > target_aspect:
        extent_height = extent_width / target_aspect
        ymin = center_y - extent_height / 2
        ymax = center_y + extent_height / 2
    else:
        extent_width = extent_height * target_aspect
        xmin = center_x - extent_width / 2
        xmax = center_x + extent_width / 2

    return xmin, xmax, ymin, ymax


def select_densest_top_candidate_cluster(
    top_25: gpd.GeoDataFrame,
    cluster_size: int = 10,
) -> gpd.GeoDataFrame:
    """Select the most compact cluster of Top 25 candidates for the close-up panel."""
    cluster_size = min(len(top_25), cluster_size)
    if cluster_size == len(top_25):
        return top_25

    points = top_25.geometry.representative_point()
    best_indices = top_25.index
    best_score: tuple[float, float, int] | None = None

    for candidate_index, point in points.items():
        distances = points.distance(point)
        nearest_indices = distances.sort_values(kind="mergesort").head(cluster_size).index
        cluster = top_25.loc[nearest_indices]
        minx, miny, maxx, maxy = cluster.total_bounds
        cluster_area = (maxx - minx) * (maxy - miny)
        rank_value = int(pd.to_numeric(top_25.loc[candidate_index, "candidate_rank"], errors="coerce"))
        score = (cluster_area, float(distances.loc[nearest_indices].sum()), rank_value)
        if best_score is None or score < best_score:
            best_score = score
            best_indices = nearest_indices

    return top_25.loc[best_indices].sort_values("candidate_rank")


def choose_scale_bar_length_km(xmin: float, xmax: float) -> int:
    """Choose a compact scale bar length for the current extent."""
    target_km = ((xmax - xmin) / 1_000) * 0.22
    previous_length_km = 1
    for length_km in [1, 2, 5, 10, 20]:
        if length_km > target_km:
            return max(1, previous_length_km)
        previous_length_km = length_km
    return 20


def add_compact_title_and_note(fig, title: str) -> None:
    """Add a compact title block for the close-up portfolio map."""
    generated_date = pd.Timestamp.today().strftime("%Y-%m-%d")
    fig.suptitle(title, fontsize=17, fontweight="bold", x=0.04, ha="left", y=0.962)
    fig.text(
        0.04,
        0.924,
        "Texas Real Estate Sourcing GIS Pipeline & Parcel Screening System",
        fontsize=9.5,
        color="#334155",
        ha="left",
    )
    fig.text(
        0.04,
        0.041,
        "Candidate polygons are analyst-defined proxies, not official parcels. "
        "Scores are for portfolio demonstration only.",
        fontsize=7.8,
        color="#475569",
        ha="left",
    )
    fig.text(
        0.04,
        0.024,
        "Basemap: OpenStreetMap / Contextily. Boundary and candidate layers: project screening dataset. "
        f"Generated: {generated_date}.",
        fontsize=5.9,
        color="#64748b",
        ha="left",
    )
    fig.text(
        0.04,
        0.011,
        "Validate against official parcel records, zoning, ownership, floodplain, utilities, and access constraints before acquisition analysis.",
        fontsize=5.9,
        color="#64748b",
        ha="left",
    )


def add_compact_scale_bar(ax, length_km: int) -> None:
    """Add a smaller scale bar for the close-up map."""
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    x = x_min + (x_max - x_min) * 0.055
    y = y_min + (y_max - y_min) * 0.065
    length_m = length_km * 1_000
    ax.plot([x, x + length_m], [y, y], color="#111827", linewidth=2.2, solid_capstyle="butt")
    ax.text(
        x + length_m / 2,
        y + (y_max - y_min) * 0.017,
        f"{length_km} km",
        ha="center",
        va="bottom",
        fontsize=7,
        color="#111827",
    )


def add_compact_north_arrow(ax) -> None:
    """Add a smaller north arrow for the close-up map."""
    ax.annotate(
        "N",
        xy=(0.955, 0.875),
        xytext=(0.955, 0.805),
        xycoords="axes fraction",
        arrowprops={"facecolor": "#111827", "edgecolor": "#111827", "width": 1.9, "headwidth": 6},
        ha="center",
        va="center",
        fontsize=7.4,
        fontweight="bold",
        color="#111827",
    )


def add_light_basemap(
    ax,
    zoom: int,
    panel_name: str,
    alpha: float = 0.56,
    zoom_adjust: int = 0,
) -> bool:
    """Add a light CartoDB/OSM basemap for Top 25 static-map panels."""
    if ctx is None:
        if not getattr(add_light_basemap, "_missing_contextily_warning_printed", False):
            print("Warning: contextily is not installed; Top 25 basemap skipped.")
            add_light_basemap._missing_contextily_warning_printed = True
        return False

    try:
        source = ctx.providers.CartoDB.Positron
        ctx.add_basemap(
            ax,
            crs=config.ANALYSIS_CRS,
            source=source,
            zoom=zoom,
            zoom_adjust=zoom_adjust,
            reset_extent=True,
            attribution=False,
            alpha=alpha,
            interpolation="bilinear",
            zorder=0,
        )
        return True
    except Exception as exc:
        print(f"Warning: Top 25 basemap unavailable for {panel_name}: {exc}")
        return False


def create_centroid_points_for_labeling(top_25: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Create display-only centroid points from Top 25 candidate footprints."""
    points = top_25.copy()
    points["candidate_rank_numeric"] = pd.to_numeric(points["candidate_rank"], errors="coerce")
    points["final_site_score_numeric"] = pd.to_numeric(points["final_site_score"], errors="coerce")
    points["point_size"] = points["candidate_rank_numeric"].apply(
        lambda rank: 96 if rank <= 5 else 68 if rank <= 10 else 48
    )
    return gpd.GeoDataFrame(points, geometry=top_25.geometry.representative_point(), crs=top_25.crs)


def calculate_balanced_extent(top_25: gpd.GeoDataFrame) -> tuple[float, float, float, float]:
    """Calculate a balanced main-panel extent that keeps all Top 25 sites visible."""
    return extent_from_bounds(
        tuple(top_25.total_bounds),
        pad_ratio=0.035,
        min_pad_m=1_650,
        target_aspect=1.52,
    )


def add_top_5_rank_labels(
    ax,
    centroid_points: gpd.GeoDataFrame,
    extent: tuple[float, float, float, float],
) -> None:
    """Label visible Top 5 centroid points with deterministic offsets."""
    xmin, xmax, ymin, ymax = extent
    extent_width = xmax - xmin
    extent_height = ymax - ymin
    visible_area = box(xmin, ymin, xmax, ymax)
    label_layer = centroid_points[
        (centroid_points["candidate_rank_numeric"] <= 5) & centroid_points.intersects(visible_area)
    ].sort_values("candidate_rank_numeric")

    label_offset = max(min(max(extent_width, extent_height) * 0.032, 1_450), 800)
    label_margin_x = extent_width * 0.022
    label_margin_y = extent_height * 0.035
    rank_offsets = {
        1: [(1.0, 0.7), (0.65, 1.0), (1.25, 0.3)],
        2: [(0.95, -0.25), (1.05, 0.55), (0.35, -0.75)],
        3: [(-1.05, 1.05), (-1.35, 0.55), (-0.8, 1.45)],
        4: [(-1.35, -1.25), (-1.65, 0.15), (-0.55, -1.65)],
        5: [(1.35, -1.25), (1.65, 0.15), (0.55, -1.65)],
    }
    fallback_offsets = [(1.1, 0.9), (-1.1, 0.9), (1.1, -0.9), (-1.1, -0.9), (0.0, 1.45)]
    placed_labels: list[tuple[float, float]] = []

    for label_index, (_, row) in enumerate(label_layer.iterrows()):
        point = row.geometry
        rank = int(row["candidate_rank_numeric"])
        offset_candidates = rank_offsets.get(rank, fallback_offsets[label_index:] + fallback_offsets[:label_index])
        candidate_positions = []
        for dx_factor, dy_factor in offset_candidates:
            label_x = min(max(point.x + dx_factor * label_offset, xmin + label_margin_x), xmax - label_margin_x)
            label_y = min(max(point.y + dy_factor * label_offset, ymin + label_margin_y), ymax - label_margin_y)
            overlap_score = sum(
                max(0, extent_width * 0.04 - abs(label_x - placed_x))
                + max(0, extent_height * 0.06 - abs(label_y - placed_y))
                for placed_x, placed_y in placed_labels
            )
            candidate_positions.append((overlap_score, label_x, label_y))
            if overlap_score == 0:
                break
        _, label_x, label_y = min(candidate_positions, key=lambda item: item[0])
        placed_labels.append((label_x, label_y))
        ax.annotate(
            f"#{rank}",
            xy=(point.x, point.y),
            xytext=(label_x, label_y),
            fontsize=7.4,
            fontweight="bold",
            color="#111827",
            ha="center",
            va="center",
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": "white",
                "edgecolor": "#cbd5e1",
                "alpha": 0.98,
            },
            arrowprops={"arrowstyle": "-", "color": "#64748b", "linewidth": 0.5, "alpha": 0.72},
            zorder=9,
        )


def add_cluster_inset(
    inset_ax,
    layers: dict[str, gpd.GeoDataFrame],
    top_25: gpd.GeoDataFrame,
    centroid_points: gpd.GeoDataFrame,
) -> bool:
    """Add a Dallas County context inset highlighting the primary Top 25 cluster."""
    dense_cluster = select_densest_top_candidate_cluster(top_25, cluster_size=15)
    cluster_xmin, cluster_xmax, cluster_ymin, cluster_ymax = extent_from_bounds(
        tuple(dense_cluster.total_bounds),
        pad_ratio=0.25,
        min_pad_m=1_400,
        target_aspect=1.18,
    )

    inset_ax.set_facecolor("white")
    set_extent(inset_ax, layers["dallas_county_boundary"], pad_ratio=0.16)
    basemap_used = add_light_basemap(
        inset_ax,
        zoom=10,
        panel_name="primary cluster inset",
        alpha=0.54,
        zoom_adjust=0,
    )
    layers["dallas_county_boundary"].plot(
        ax=inset_ax,
        color="none",
        edgecolor="#475569",
        linewidth=0.58,
        alpha=0.86,
        zorder=2,
    )
    centroid_points.plot(
        ax=inset_ax,
        color="#f97316",
        edgecolor="#7c2d12",
        markersize=16,
        linewidth=0.45,
        alpha=0.96,
        zorder=3,
    )
    inset_ax.add_patch(
        Rectangle(
            (cluster_xmin, cluster_ymin),
            cluster_xmax - cluster_xmin,
            cluster_ymax - cluster_ymin,
            facecolor="none",
            edgecolor="#2563eb",
            linewidth=1.0,
            zorder=4,
        )
    )
    inset_ax.set_axis_off()
    inset_ax.text(
        0.04,
        0.88,
        "Primary Cluster (Context)",
        transform=inset_ax.transAxes,
        fontsize=7,
        fontweight="bold",
        color="#334155",
        ha="left",
        va="top",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1.6},
    )
    for spine in inset_ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor("#cbd5e1")
        spine.set_linewidth(0.8)
    return basemap_used


def add_rank_callout_table(table_ax, centroid_points: gpd.GeoDataFrame) -> None:
    """Add a compact Top 10 ranked candidate callout table."""
    table_ax.set_facecolor("white")
    table_ax.set_xticks([])
    table_ax.set_yticks([])
    for spine in table_ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor("#cbd5e1")
        spine.set_linewidth(0.8)

    top_10 = centroid_points.sort_values("candidate_rank_numeric").head(10)
    rounded_scores_have_ties = top_10["final_site_score_numeric"].round(2).duplicated(keep=False).any()
    table_ax.text(
        0.05,
        0.94,
        "Top 10 Ranked Candidates",
        transform=table_ax.transAxes,
        fontsize=8.4,
        fontweight="bold",
        color="#111827",
        ha="left",
        va="top",
    )
    table_ax.text(
        0.05,
        0.81,
        "Rank   Candidate     Score",
        transform=table_ax.transAxes,
        fontsize=6.6,
        color="#475569",
        family="monospace",
        ha="left",
        va="top",
    )

    y = 0.735
    for _, row in top_10.iterrows():
        candidate_id = str(row["candidate_id"])
        score = float(row["final_site_score_numeric"])
        rank = int(row["candidate_rank_numeric"])
        table_ax.text(
            0.05,
            y,
            f"{rank:>2}     {candidate_id:<10}  {score:>5.2f}",
            transform=table_ax.transAxes,
            fontsize=6.4,
            color="#111827" if rank <= 5 else "#334155",
            fontweight="bold" if rank <= 5 else "normal",
            family="monospace",
            ha="left",
            va="top",
        )
        y -= 0.057

    table_note = "Proxy scores for portfolio demonstration."
    if rounded_scores_have_ties:
        table_note += "\nScores rounded to 2 decimals."
    table_ax.text(
        0.05,
        0.055,
        table_note,
        transform=table_ax.transAxes,
        fontsize=5.8,
        color="#64748b",
        ha="left",
        va="bottom",
        wrap=True,
    )


def add_methodology_note(note_ax) -> None:
    """Add a compact scoring-methodology note to the Top 25 side panel."""
    note_ax.set_facecolor("white")
    note_ax.set_xticks([])
    note_ax.set_yticks([])
    for spine in note_ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor("#cbd5e1")
        spine.set_linewidth(0.8)

    note_ax.text(
        0.05,
        0.76,
        "Scoring Methodology",
        transform=note_ax.transAxes,
        fontsize=6.5,
        fontweight="bold",
        color="#111827",
        ha="left",
        va="top",
    )
    note_ax.text(
        0.05,
        0.47,
        "Weighted proxy index: location context, footprint,\nclustering, accessibility, and constraints.\nParcel-level validation required.",
        transform=note_ax.transAxes,
        fontsize=5.35,
        color="#475569",
        ha="left",
        va="top",
        linespacing=1.15,
    )


def add_clean_legend(legend_ax) -> None:
    """Add a compact legend for the Top 25 result map."""
    legend_ax.set_facecolor("white")
    legend_ax.set_xticks([])
    legend_ax.set_yticks([])
    for spine in legend_ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor("#cbd5e1")
        spine.set_linewidth(0.8)

    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#f97316",
            markeredgecolor="#7c2d12",
            markersize=6,
            label="Top 25 candidate centroid",
        ),
        Patch(facecolor="#fed7aa", edgecolor="#c2410c", alpha=0.22, label="Top 25 candidate footprint"),
        Patch(facecolor="none", edgecolor="#475569", label="Dallas County boundary"),
    ]
    legend_ax.legend(
        handles=handles,
        loc="center left",
        bbox_to_anchor=(0.02, 0.5),
        ncol=1,
        frameon=False,
        fontsize=5.9,
        handlelength=1.6,
        borderaxespad=0,
    )


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
    fig.subplots_adjust(right=0.82)
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
    ax.legend(
        handles=handles,
        loc="lower left",
        bbox_to_anchor=(1.02, 0.04),
        frameon=True,
        framealpha=0.94,
        fontsize=7.5,
        borderpad=0.7,
        labelspacing=0.45,
    )
    finalize_map(fig, ax, MAP_OUTPUTS["dallas_candidate_screening_map"]["title"], png_path, pdf_path)


def plot_top_25(layers: dict[str, gpd.GeoDataFrame], png_path: Path, pdf_path: Path) -> None:
    """Create top 25 candidate close-up map."""
    top_25 = layers["top_25_candidate_sites"].copy()
    centroid_points = create_centroid_points_for_labeling(top_25)
    xmin, xmax, ymin, ymax = calculate_balanced_extent(top_25)

    submarket_context = layers["dfw_zcta_submarkets"].cx[xmin:xmax, ymin:ymax]
    main_top_25 = top_25.cx[xmin:xmax, ymin:ymax]
    main_centroids = centroid_points.cx[xmin:xmax, ymin:ymax]

    fig = plt.figure(figsize=(12, 7.2))
    ax = fig.add_axes([0.04, 0.14, 0.69, 0.755])
    table_ax = fig.add_axes([0.755, 0.585, 0.225, 0.305])
    methodology_ax = fig.add_axes([0.755, 0.492, 0.225, 0.07])
    legend_ax = fig.add_axes([0.755, 0.425, 0.225, 0.048])
    inset_ax = fig.add_axes([0.755, 0.12, 0.225, 0.285])
    ax.set_facecolor("#f8fafc")

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")
    main_basemap_used = add_light_basemap(
        ax,
        zoom=11,
        panel_name="main Top 25 map",
        alpha=0.56,
        zoom_adjust=0,
    )

    submarket_context.boundary.plot(ax=ax, color="#cbd5e1", linewidth=0.22, alpha=0.34, zorder=1)
    main_top_25.plot(
        ax=ax,
        color="#fed7aa",
        edgecolor="#c2410c",
        linewidth=0.5,
        alpha=0.2,
        zorder=5,
    )
    main_centroids.plot(
        ax=ax,
        color="#f97316",
        marker="o",
        markersize=main_centroids["point_size"],
        edgecolor="#7c2d12",
        linewidth=0.8,
        alpha=0.98,
        zorder=7,
    )
    layers["dallas_county_boundary"].plot(
        ax=ax,
        color="none",
        edgecolor="#475569",
        linewidth=0.7,
        alpha=0.82,
        zorder=6,
    )

    add_top_5_rank_labels(ax, centroid_points, (xmin, xmax, ymin, ymax))
    add_rank_callout_table(table_ax, centroid_points)
    add_methodology_note(methodology_ax)
    add_clean_legend(legend_ax)
    inset_basemap_used = add_cluster_inset(inset_ax, layers, top_25, centroid_points)
    print(f"Top 25 basemap used: {'yes' if main_basemap_used or inset_basemap_used else 'no'}")

    add_compact_title_and_note(fig, MAP_OUTPUTS["top_25_candidate_sites_map"]["title"])
    add_compact_scale_bar(ax, choose_scale_bar_length_km(xmin, xmax))
    add_compact_north_arrow(ax)
    ax.set_axis_off()
    fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


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
