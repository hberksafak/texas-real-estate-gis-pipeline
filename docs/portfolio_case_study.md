# Portfolio Case Study

Draft - portfolio case study for the Texas Real Estate Sourcing GIS Pipeline & Parcel Screening System.

## Project Overview

This project demonstrates a reproducible GIS pipeline for real estate sourcing in the Dallas-Fort Worth market, with a Dallas County candidate-screening focus. It converts public boundary and context layers into platform-ready GIS deliverables, candidate-screening outputs, ranked proxy sites, static maps, and an interactive web map.

The project is designed as a client-style portfolio artifact for real estate investors, acquisition teams, site-selection consultants, and GIS analysts who need repeatable sourcing workflows rather than one-off map exhibits.

## Business Problem

Real estate sourcing often starts with fragmented public GIS data, inconsistent coordinate systems, unclear screening assumptions, and hard-to-repeat manual map work. A useful sourcing workflow needs to answer:

- What is the study area?
- Which context layers are available and suitable?
- Which candidate areas pass transparent screening rules?
- Which candidates should be reviewed first?
- What outputs can be delivered to business users, GIS users, and portfolio reviewers?

This project builds the foundation for those answers in DFW / Dallas County.

## Data Sources

Primary and staged sources include:

- U.S. Census TIGER/Line 2025 county, CBSA, ZCTA, and Texas Unified School District boundaries
- HUD Opportunity Zones
- Analyst-defined ZCTA sector proxy submarkets
- Analyst-defined candidate-site grid proxy polygons

Texas Capitol / Texas Legislative Council school district data remains documented as an intended official source, but access was blocked during local staging. Census TIGER/Line 2025 Texas Unified School Districts were used as an official accessible fallback.

## Methodology

The workflow follows these stages:

1. Verify source systems and document download decisions.
2. Build DFW and Dallas County study area boundaries from Census TIGER/Line 2025.
3. Create analyst-defined ZCTA-based submarket proxy polygons.
4. Validate GIS layers with a reusable cleaning factory.
5. Build a real estate layer catalog with boundaries, submarkets, Opportunity Zones, and school district context.
6. Create candidate-site grid proxy polygons inside Dallas County.
7. Apply screening rules and generate a disqualification audit trail.
8. Score and rank qualified candidates.
9. Package platform-ready GeoJSON and GeoPackage outputs.
10. Create interactive and static map deliverables.

## Candidate Screening Logic

Official Dallas CAD parcel data is not used yet. Instead, the project creates analyst-defined grid proxy polygons inside Dallas County. These candidates are clearly labeled:

- `candidate_source = analyst_defined_grid_proxy`
- `is_official_parcel = False`

Initial screening rules check geometry validity, area range, edge-fragment reliability, and submarket assignment. Boundary-edge grid fragments below the configured retained-area threshold are disqualified because they are partial clipped proxy cells and less reliable for candidate screening.

Each candidate receives an audit trail with qualification status, failed rule count, failed rule names, primary disqualification reason, and screening stage.

## Weighted Scoring Model

Qualified proxy candidates are ranked with `v1_proxy_candidate_scoring`, a transparent portfolio demonstration model.

The weighted score includes:

- 25% size suitability
- 20% grid completeness / shape reliability
- 20% neutral submarket candidate-supply context
- 15% Opportunity Zone incentive context
- 10% school district context completeness
- 10% geometry reliability

Scores are proxy rankings for portfolio demonstration. They are not legal parcel valuation, development feasibility, entitlement, appraisal, engineering, or underwriting determinations.

School district context rewards only whether a clean district assignment exists. It does not use school ratings, school quality, demographics, income, race, ethnicity, protected-class variables, or fair-housing-risk variables.

Opportunity Zones are policy/incentive context only and are not demographic targeting.

## Deliverables

Final deliverables include:

- Platform-ready GeoJSON package
- GeoPackage exports
- Real estate layer catalog
- Candidate screening audit trail
- Qualified and disqualified candidate layers
- Weighted ranked candidate table
- Top 25 candidate sites layer
- Repository QA report

## Visual Deliverables

Draft - to be updated as portfolio screenshots are selected.

Generated visual deliverables include:

- DFW study area overview
- Dallas candidate screening and ranked sites map
- Top 25 ranked candidate sites close-up map
- Interactive Folium web map
- Platform-ready GeoJSON package for web/GIS upload

## Limitations

No official parcel ownership or legal parcel boundaries were used. Candidate polygons are analyst-defined grid proxies, not official parcels.

Scores are proxy rankings for portfolio demonstration, not legal development feasibility or valuation.

School district context is neutral context only. Opportunity Zones are policy/incentive context only. The project does not use demographic targeting language or protected-class logic.

Additional due diligence would be required before real acquisition work, including parcel records, zoning, flood, road access, utilities, title, environmental, entitlement, market, and underwriting review.

## What This Demonstrates For GIS / Real Estate Clients

This project demonstrates the ability to:

- Build a reproducible GIS pipeline from public data.
- Manage CRS strategy for web delivery and local area calculations.
- Validate and package GIS layers for multiple audiences.
- Create transparent screening rules and audit trails.
- Rank candidates with documented scoring assumptions.
- Deliver static, interactive, GeoJSON, CSV, and GeoPackage outputs.
- Communicate limitations clearly for real estate decision workflows.
