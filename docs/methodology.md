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

## 6. Disqualification Audit Trail

Maintain explicit audit fields for each disqualification rule so rejected parcels can be reviewed and explained rather than silently removed.

## 7. Weighted Scoring

Score qualified candidates with configurable weighted criteria. Planned scoring categories include access, market context, constraint risk, amenity proximity, and strategic fit.

## 8. GeoJSON Export

Export selected submarkets and candidate sites to `EPSG:4326` GeoJSON for platform compatibility and interactive web mapping.

## 9. QGIS Atlas

Use QGIS layouts and atlas tooling to generate static map packages for shortlisted submarkets and candidate sites.

## 10. Interactive Web Map

Create an interactive web map for portfolio presentation and stakeholder review after real outputs are available.
