# Methodology

This document outlines the planned analytical workflow. It will be updated once real data sources, assumptions, and outputs are finalized.

## 1. Source Preparation

Organize downloaded GIS sources by provider, geography, and date. Preserve original files and metadata in `data/raw/` while keeping source data out of version control.

## 2. Cleaning and Validation

Standardize field names, repair invalid geometries, remove empty geometries, confirm CRS metadata, and create consistent processed layers in `data/processed/`.

## 3. ZCTA Submarket Creation

Use Census ZCTA boundaries and regional boundary layers to define DFW / Dallas County submarket geographies for aggregation, filtering, and map presentation.

## 4. Real Estate Layer Factory

Create reusable real estate context layers, including parcels, roads, flood zones, school districts, opportunity zones, amenities, and other investment-relevant overlays.

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
