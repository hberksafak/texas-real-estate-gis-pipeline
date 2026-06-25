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

- U.S. Census TIGER/Line 2025 county, CBSA, ZCTA, Dallas County Area Water, and Texas Unified School District boundaries
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

Initial screening rules check geometry validity, area range, edge-fragment reliability, waterbody overlap, and submarket assignment. Boundary-edge grid fragments below the configured retained-area threshold are disqualified because they are partial clipped proxy cells and less reliable for candidate screening.

Waterbody exclusion is a screening QA rule based on Census TIGER/Line 2025 Dallas County Area Water. Candidate proxy cells are disqualified when their centroid falls inside a mapped waterbody or when the waterbody overlap ratio is at least 10%. Basemap tiles are used only for visualization and are not analysis inputs.

Each candidate receives an audit trail with qualification status, failed rule count, failed rule names, primary disqualification reason, and screening stage.

## Weighted Scoring Model

Qualified proxy candidates are ranked with `v2_professional_proxy_screening_limited`, a transparent professional proxy screening model.

The weighted score includes:

- 30% developable geometry score
- 25% constraint avoidance score
- 25% neutral spatial context score
- 15% neutral submarket context score
- 5% Opportunity Zone incentive context

Scores are proxy rankings for portfolio demonstration. They are not legal parcel valuation, development feasibility, entitlement, appraisal, engineering, or underwriting determinations.

School district context is retained as metadata only and is not used as a ranking criterion. The model does not use school ratings, school quality, demographics, income, race, ethnicity, protected-class variables, or fair-housing-risk variables.

Opportunity Zones are policy/incentive context only and are not demographic targeting.

Road accessibility, FEMA flood, and NCTCOG land-use suitability are documented as not implemented because those source layers are not staged in the current local workflow. The model does not give candidates default points for missing data.

## Analytical QA Evidence

The portfolio release freezes the v2 scoring model and packages analytical QA evidence in `docs/analytical_qa_summary.md`. The release QA confirms 2,401 total proxy candidates, 2,161 qualified candidates, 240 disqualified candidates, and 25 Top 25 candidates. Waterbody QA disqualifies 200 candidates, while the Top 25 have zero waterbody overlap and zero centroid-inside-water flags. Edge-fragment QA flags 50 candidates, with zero Top 25 edge-fragment failures.

Reproducibility QA confirms the Top 25 IDs and scores are stable for the frozen v2 model, the Top 10 table matches the ranked CSV, and the Top 25 GeoJSON matches the ranked CSV Top 25. Repository QA passes all current checks. These outputs remain proxy screening evidence, not official parcel acquisition recommendations.

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

Additional due diligence would be required before real acquisition work, including official parcel records, zoning, ownership, floodplain, utilities, official road access, title, environmental, entitlement, market, and underwriting review.

## What This Demonstrates For GIS / Real Estate Clients

This project demonstrates the ability to:

- Build a reproducible GIS pipeline from public data.
- Manage CRS strategy for web delivery and local area calculations.
- Validate and package GIS layers for multiple audiences.
- Create transparent screening rules and audit trails.
- Rank candidates with documented scoring assumptions.
- Deliver static, interactive, GeoJSON, CSV, and GeoPackage outputs.
- Communicate limitations clearly for real estate decision workflows.
