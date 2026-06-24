# Download Plan

## Milestone 2 Objective

Document the verified source plan and recommended data acquisition sequence before downloading any real GIS data.

This milestone does not download data, create fake data, create notebooks, or implement analysis logic. It prepares the project for a controlled first real-data milestone.

## Source Priority Table

| Priority | Source | Why It Comes Here | Initial Storage Target |
|---:|---|---|---|
| 1 | U.S. Census TIGER/Line 2025 boundaries | Establishes official county, CBSA / MSA, and ZCTA geography. | `data/raw/census_tiger_2025/` |
| 2 | DFW / Dallas County clipping layer | Defines the study area before larger context layers are processed. | `data/raw/study_area/` |
| 3 | ZCTA boundaries | Supports submarket construction and summary geography. | `data/raw/census_tiger_2025/zcta/` |
| 4 | NCTCOG 2020 Land Use | Provides regional context and land-use proxy after the study area is defined. | `data/raw/nctcog/` |
| 5 | TxDOT roads | Enables road access and accessibility context. | `data/raw/txdot/` |
| 6 | FEMA National Flood Hazard Layer | Adds constraint overlay for screening and penalty logic. | `data/raw/fema_nfhl/` |
| 7 | Texas school district boundaries | Adds neutral context overlay. | `data/raw/texas_school_districts/` |
| 8 | HUD Opportunity Zones | Adds incentive/context geography. | `data/raw/hud_opportunity_zones/` |
| 9 | Dallas CAD parcel data | Enables the Dallas County parcel screening pilot after core context is staged. | `data/raw/dallas_cad/` |
| 10 | OSM amenities / roads | Adds supplemental services and amenity context via OSMnx. | `data/raw/osm/` |

## Recommended Download Order

1. Census boundaries
2. DFW / Dallas County boundary clipping layer
3. ZCTA boundaries
4. NCTCOG land use
5. TxDOT roads
6. FEMA flood
7. School districts
8. HUD Opportunity Zones
9. Dallas CAD parcel data
10. OSM amenities / roads

Waterbody exclusion QA uses the minimum additional official source needed for the screening rule: Census TIGER/Line 2025 Dallas County Area Water. It is staged only when the candidate screening workflow runs.

## What Goes Into `data/raw/`

Store original downloaded source packages and metadata in provider-specific folders, such as:

- Original ZIP files, shapefiles, GeoPackages, CSV files, or service-export packages
- Source metadata, codebooks, schema notes, and license/disclaimer files
- Download date notes
- Provider URLs and query parameters used for retrieval
- Checksums or file-size notes when useful for large downloads

Use a consistent folder convention:

```text
data/raw/<provider_or_source>/<download_date_or_release>/
```

Example:

```text
data/raw/census_tiger_2025/2025_release/
data/raw/dallas_cad/2026_parcel_geom/
```

## What Should Not Be Committed To Git

Do not commit:

- Raw GIS downloads
- Processed GIS layers
- Final generated GeoJSON, CSV, or GeoPackage exports
- Web map outputs
- Static map exports
- Large archives
- Temporary QGIS files
- Local credentials, tokens, or `.env` files

Only documentation, scripts, configuration templates, small metadata notes, and intentional `.gitkeep` files should be tracked.

## Dallas CAD Parcel Fallback Strategy

Dallas CAD parcel geometry is planned for the Dallas County parcel screening pilot, but it may be unavailable, blocked, too large, unsuitable, or restricted by terms of use.

If Dallas CAD parcel data cannot be used:

- Document the blocker clearly in `docs/data_sources.md` and the project methodology.
- Do not fabricate parcel data.
- Create a candidate polygon proxy only after a real, appropriate source is identified or after manual candidate geometries are legitimately created from project-defined areas.
- Keep the proxy clearly labeled as a candidate-site screening proxy, not an official parcel layer.
- Continue the pipeline using official boundary, land use, road, flood, and context layers until parcel-level screening can be added.

## First Real-Data Milestone After This Step

The next milestone should download and stage only the minimum boundary data needed to define the study area:

1. Census TIGER/Line 2025 county boundaries
2. Census TIGER/Line 2025 CBSA / MSA boundary
3. Census TIGER/Line 2025 ZCTA boundaries if appropriate for the submarket workflow

The first real-data milestone should then create documented local source folders and verify CRS, schema, and basic geometry availability before any screening or scoring logic is implemented.

## Milestone 3 Execution Notes

- Census boundary workflow is the first real-data milestone.
- Raw Census ZIPs are stored locally under `data/raw/census_tiger_2025/`.
- Final study area outputs are stored locally under `data/final/`.
- Raw and generated outputs are intentionally not committed to git.

## Milestone 6B Manual Staging Notes

- HUD Opportunity Zones were staged locally under `data/raw/hud_opportunity_zones/`.
- Texas school district data was staged locally under `data/raw/texas_school_districts/`.
- The Texas Capitol / Texas Legislative Council school district download attempt was blocked, so U.S. Census TIGER/Line 2025 Texas Unified School Districts was used as the official accessible fallback.
- The school district ZIP used by the project was `data/raw/texas_school_districts/tl_2025_48_unsd.zip`.
- The catalog workflow now produces `data/final/geojson/dfw_opportunity_zones.geojson`, `data/final/geojson/dfw_school_districts.geojson`, `data/final/csv/real_estate_layer_catalog.csv`, and `data/final/gpkg/real_estate_layer_catalog.gpkg`.
- Current catalog status includes six available layers: `dallas_county_boundary`, `dfw_cbsa_boundary`, `dfw_zctas`, `dfw_zcta_submarkets`, `dfw_opportunity_zones`, and `dfw_school_districts`.
- Generated raw and final outputs remain ignored and are not committed to git.

## Waterbody Exclusion QA Staging Notes

- Census TIGER/Line 2025 Dallas County Area Water is used as the official vector waterbody source for candidate screening QA.
- Raw source ZIP: `data/raw/census_tiger_2025/areawater/tl_2025_48113_areawater.zip`.
- Generated clipped layer: `data/final/geojson/dallas_waterbodies.geojson`.
- Candidate screening disqualifies proxy cells whose centroid falls inside a waterbody or whose water overlap ratio is at least `0.10`.
- Basemap tiles are visual context only and are not used as analysis data.
- Raw and generated final outputs remain ignored and are not committed.

## Scoring V2 Source Availability Notes

- The v2 scoring model uses existing staged project layers only.
- Implemented scoring inputs include proxy candidate geometry, Dallas County boundary, Census Area Water, ZCTA submarket proxies, and Opportunity Zone context.
- TxDOT/OSM road accessibility, FEMA flood constraints, and NCTCOG land-use suitability are not implemented because those source layers are not staged in the current local workflow.
- Missing professional variables are marked as not implemented and are not replaced with constant default scores.
