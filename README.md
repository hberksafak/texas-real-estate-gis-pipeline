# Texas Real Estate Sourcing GIS Pipeline & Parcel Screening System

## Portfolio Description

A portfolio-grade Python/QGIS GIS pipeline skeleton for sourcing and screening real estate opportunities in the Dallas-Fort Worth market, with an initial focus on Dallas County and surrounding DFW submarkets.

The planned system will prepare public GIS sources, create analysis-ready real estate layers, screen parcel or candidate-site opportunities, rank locations using transparent scoring rules, and export web/platform-ready geospatial deliverables.

## Business Question

Where in the DFW / Dallas County market are the strongest real estate sourcing opportunities after accounting for location fundamentals, parcel constraints, flood risk, transportation access, amenities, school district context, and other investment screening criteria?

## Target Client Type

This project is designed for real estate investors, acquisition teams, site-selection consultants, developers, and portfolio managers who need repeatable GIS-driven sourcing workflows rather than one-off map exhibits.

## Geographic Focus

The first implementation target is DFW, with Dallas County as the primary county-level focus. The repository is structured so additional North Texas counties and regional datasets can be added later without changing the core workflow design.

## Planned Data Sources

Planned sources include:

- U.S. Census TIGER/Line ZCTA boundaries
- U.S. Census CBSA boundaries
- NCTCOG regional GIS and land-use layers
- Dallas Central Appraisal District parcel shapefiles
- TxDOT roadway layers
- FEMA National Flood Hazard Layer
- Texas school district boundaries
- HUD Opportunity Zones
- OpenStreetMap roads and amenities
- Microsoft Global ML Building Footprints as an optional enrichment source

No raw GIS data is committed to this repository.

## Planned Workflow

1. Configure project paths and coordinate reference systems.
2. Prepare raw source files into a consistent project structure.
3. Clean and validate GIS layers.
4. Build ZCTA-based real estate submarkets.
5. Create reusable real estate analysis layers.
6. Apply parcel and candidate-site screening rules.
7. Score and rank qualified candidates.
8. Export platform-ready GeoJSON, CSV, and GeoPackage deliverables.
9. Build QGIS maps, atlas exports, and an interactive web map.

## CRS Strategy

- `EPSG:4326` is the project CRS for platform GeoJSON exports and web mapping compatibility.
- `EPSG:32138` is the analysis CRS for DFW distance and area calculations.

All distance, buffer, and area calculations should be performed in `EPSG:32138`. Final platform exports should be transformed back to `EPSG:4326`.

## Expected Deliverables

Expected project deliverables include:

- Cleaned GIS layers for submarkets, parcels, constraints, and amenities
- Ranked candidate-site tables
- Platform-ready GeoJSON exports
- CSV exports for business review
- GeoPackage exports for desktop GIS workflows
- QGIS map layouts and atlas exports
- Static PNG/PDF maps
- Interactive web map output
- Portfolio case study and methodology documentation

## Documentation

- [Data sources](docs/data_sources.md)
- [Download plan](docs/download_plan.md)
- [Methodology](docs/methodology.md)
- [Data dictionary](docs/data_dictionary.md)
- [Portfolio case study](docs/portfolio_case_study.md)

## Current Status

Milestone 6 in progress: platform-ready real estate layer catalog workflow added.

## Limitations

This repository does not commit raw GIS data, processed GIS data, final generated datasets, exported maps, or web map outputs. Source datasets must be downloaded separately according to their respective licenses and usage terms.
