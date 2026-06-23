# Methodology

This document outlines the planned analytical workflow. It will be updated once real data sources, assumptions, and outputs are finalized.

## 1. Source Preparation

Organize downloaded GIS sources by provider, geography, and date. Preserve original files and metadata in `data/raw/` while keeping source data out of version control.

## 2. Cleaning and Validation

Standardize field names, repair invalid geometries, remove empty geometries, confirm CRS metadata, and create consistent processed layers in `data/processed/`.

### Reusable GIS Cleaning and Validation Factory

Government and public GIS layers often arrive with different schemas, CRS metadata, geometry validity issues, duplicate records, and occasional empty geometries. The project uses a reusable validation workflow so each layer is checked consistently before it is used in downstream screening, scoring, mapping, or export steps.

The validation factory standardizes every input layer to the project platform CRS, `EPSG:4326`, for final delivery compatibility. Area calculations are performed separately in the DFW analysis CRS, `EPSG:32138`, so reported square-kilometer measurements are calculated in a projected coordinate system rather than from geographic coordinates.

For each layer, the workflow normalizes column names to lowercase snake case, repairs invalid geometries using Shapely `make_valid` when available or `buffer(0)` as a fallback, removes empty or null geometries, checks for exact duplicate records, and writes a validation report. Cleaned layers are exported to a GeoPackage while preserving `EPSG:4326` platform-ready output geometry.

## 3. ZCTA Submarket Creation

Use Census ZCTA boundaries and the Census-derived DFW CBSA boundary to create analyst-defined submarket polygons for aggregation, filtering, and map presentation.

### ZCTA-Based Submarket Creation

The project uses U.S. Census ZCTA geography as the base unit for the first portfolio demonstration submarket workflow. These submarkets are analyst-defined directional sector proxies based on each ZCTA centroid's position relative to the DFW CBSA centroid.

The workflow demonstrates a reproducible ZIP/ZCTA-to-submarket polygon production process: standardize ZCTA IDs, assign each ZCTA to a deterministic directional sector, join the assignment back to the ZCTA layer, dissolve by submarket, calculate area in `EPSG:32138`, and export platform-ready GeoJSON in `EPSG:4326`.

These polygons are not official commercial, brokerage, county, city, government, zoning, or regulatory boundaries. They are portfolio demonstration proxies for organizing DFW ZCTAs into readable real estate market sectors.

## 4. Real Estate Layer Factory

Create reusable real estate context layers, including parcels, roads, flood zones, school districts, opportunity zones, amenities, and other investment-relevant overlays.

### Platform-Ready Real Estate Layer Catalog

Real estate GIS workflows need a clean layer catalog so analysts can see which boundaries, submarkets, and context overlays are available, where each layer came from, how many features it contains, and which platform-ready files should be used for mapping or downstream analysis.

The catalog packages existing Census-derived boundaries, ZCTA layers, analyst-defined submarkets, and controlled public context overlays into GeoJSON and GeoPackage outputs. All final platform layers are standardized to `EPSG:4326`, while area fields are calculated in `EPSG:32138` for DFW-appropriate projected measurements.

School district boundaries are included only as neutral education context overlays. They are not ranking criteria, demographic targeting inputs, or fair-housing-risk scoring variables.

HUD Opportunity Zones are included only as policy and incentive context for business review. They are not used as demographic targeting inputs.

## 5. Parcel and Candidate Screening

Apply transparent screening rules to identify candidate parcels or sites. Planned rules may include parcel size, location, zoning or land-use context, access, flood exposure, and exclusion constraints.

### Candidate Site Screening Foundation

Official parcel data is not used yet. Until Dallas CAD parcel geometry is acquired and validated, the project uses analyst-defined grid proxy polygons clipped to Dallas County as a documented candidate-site screening base. These proxy polygons are not official parcels and are labeled with `candidate_source = analyst_defined_grid_proxy` and `is_official_parcel = False`.

This proxy approach is useful for developing the screening workflow before parcel acquisition because it lets the project test geometry handling, area thresholds, submarket assignment, context overlays, output schemas, and audit tables against real geography without inventing parcel ownership or legal parcel boundaries.

Initial screening rules validate geometry, minimum and maximum candidate area, boundary-edge grid fragmentation, and submarket assignment. Boundary-edge fragments are disqualified when a clipped grid cell retains less than 60% of the full 1,000m grid cell area because these partial proxy cells are less reliable for candidate screening than complete interior cells. Each candidate receives a disqualification audit trail with failed rule counts, semicolon-delimited failed rule names, a primary disqualification reason, and a screening stage.

School district context is included only as a neutral education context overlay. It is not a qualification rule, ranking criterion, demographic targeting input, or fair-housing-risk targeting input.

Opportunity Zones are included only as policy and incentive context. Opportunity Zone overlap is not a qualification rule and is not used for demographic targeting.

## 6. Disqualification Audit Trail

Maintain explicit audit fields for each disqualification rule so rejected parcels can be reviewed and explained rather than silently removed.

## 7. Weighted Scoring

Score qualified candidates with configurable weighted criteria. Planned scoring categories include access, market context, constraint risk, amenity proximity, and strategic fit.

### Weighted Candidate Scoring and Ranking

The first candidate ranking model scores only qualified analyst-defined grid proxy candidates. It is a transparent proxy sourcing score for portfolio demonstration, not a legal parcel valuation, entitlement review, engineering assessment, or development feasibility determination.

The v1 scoring model uses weighted 0-100 component scores: 25% size suitability, 20% grid completeness / shape reliability, 20% neutral submarket candidate-supply context, 15% Opportunity Zone incentive context, 10% school district context completeness, and 10% geometry reliability.

Size suitability favors candidates in the 25-120 acre ideal proxy range, with tapering outside that range. Grid completeness rewards near-full grid cells over clipped cells. Submarket context uses a moderated, reproducible candidate-distribution proxy and does not imply market demand, pricing, rent growth, or investment performance.

School district context is neutral context completeness only. The model does not use school quality, school ratings, demographics, income, race, ethnicity, protected class variables, or fair-housing-risk variables.

Opportunity Zone context is used only as policy and incentive context. It is not demographic targeting.

Scores should be interpreted as a transparent prioritization aid for demonstration workflows. They are not a substitute for parcel due diligence, zoning review, flood review, access analysis, title review, appraisal, underwriting, or legal advice.

## 8. GeoJSON Export

Export selected submarkets and candidate sites to `EPSG:4326` GeoJSON for platform compatibility and interactive web mapping.

### Platform-Ready GeoJSON Export Package

The final delivery workflow packages project layers as platform-ready GeoJSON because GeoJSON is broadly supported by web maps, portfolio demos, lightweight GIS viewers, and downstream location-intelligence tools. Each export is standardized to `EPSG:4326` so browser maps and common geospatial platforms can read the layers without additional reprojection.

The export package is manifest-driven. Each exported layer is listed with its category, source path, platform GeoJSON path, feature count, geometry types, CRS, file size, and area summary. A separate export summary records expected layers, exported layers, missing layers, total features, total GeoJSON size, and package status.

The same export-ready layers are also written to a GeoPackage for desktop GIS review and handoff. GeoPackage delivery keeps related layers together while the GeoJSON folder supports platform upload workflows.

Candidate layers remain analyst-defined grid proxy polygons and are not official parcels. School district layers are neutral context overlays only. Opportunity Zones are included only as policy and incentive context.

## 9. QGIS Atlas

Use QGIS layouts and atlas tooling to generate static map packages for shortlisted submarkets and candidate sites.

### Static Portfolio Map Exports

Static map exports provide portfolio-ready visuals for website screenshots, case-study figures, PDF inserts, and optional QGIS refinement. They complement the interactive web map by giving reviewers fixed, curated views of the study area, candidate screening workflow, and top-ranked proxy sites.

The static export workflow uses the platform-ready GeoJSON package and plots layers in `EPSG:32138` for consistent DFW map geometry. PNG and PDF outputs are written to `outputs/maps/` and a summary table documents the map name, files, layers used, purpose, status, and notes.

Candidate geometries shown in these maps are analyst-defined grid proxy polygons and are not official parcels. School district context remains neutral context only. Opportunity Zones remain policy and incentive context only.

## 10. Interactive Web Map

Create an interactive web map for portfolio presentation and stakeholder review after real outputs are available.

### Interactive Web Map Demo

The interactive demo visualizes the final platform-ready GeoJSON package in a Folium/Leaflet web map. Core boundaries, ZCTA-based submarkets, Opportunity Zones, school district context, qualified and disqualified proxy candidates, ranked candidates, and the top 25 candidates can be toggled through the map layer control.

The map is a client-facing demonstration artifact: it lets a reviewer inspect the pipeline's geography, screening outputs, rankings, and context layers without opening desktop GIS software. Heavier candidate and context layers are available as optional overlays so the initial view stays readable.

Candidate polygons remain analyst-defined grid proxies and are not official parcels. Scores are transparent proxy rankings for portfolio demonstration only. School district context is neutral context only. Opportunity Zones are policy and incentive context only.
