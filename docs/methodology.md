# Methodology

This document summarizes the end-to-end methodology for the Texas Real Estate Sourcing GIS Pipeline & Parcel Screening System.

## 1. Source Verification

The project starts with documented source verification and a download plan. Source notes identify intended providers, source limitations, fallback decisions, and local staging folders. Raw and generated GIS files stay local and are intentionally excluded from git.

Current source families include Census TIGER/Line 2025 boundaries, Census TIGER/Line 2025 Dallas County Area Water for waterbody exclusion QA, HUD Opportunity Zones, and school district context. Texas Capitol / Texas Legislative Council school district data remains documented as an intended source, while Census TIGER/Line 2025 Texas Unified School Districts were used as an official accessible fallback.

## 2. Census Boundary Workflow

The first real-data workflow uses Census TIGER/Line 2025 county, CBSA, and ZCTA layers. It creates the Dallas County boundary, DFW CBSA boundary, and DFW-intersecting ZCTA layer.

Final platform exports use `EPSG:4326`. DFW distance and area calculations use `EPSG:32138`.

## 3. ZCTA Submarket Proxy Creation

The project uses Census ZCTA geography as the base unit for analyst-defined real estate submarket proxy polygons. Each ZCTA is assigned to a deterministic directional sector based on its centroid relative to the DFW CBSA centroid, then dissolved into submarket polygons.

These submarkets are not official commercial, brokerage, county, city, government, zoning, or regulatory boundaries. They are portfolio demonstration proxies for organizing DFW ZCTAs into readable real estate market sectors.

## 4. Layer Validation

Government and public GIS layers often arrive with inconsistent schemas, CRS metadata, invalid geometries, duplicate records, and empty geometries. The reusable validation workflow standardizes layers before they are used in downstream screening, scoring, mapping, or exports.

Validation steps include lowercase snake-case field names, CRS standardization to `EPSG:4326`, invalid geometry repair with Shapely `make_valid` or `buffer(0)`, empty geometry removal, duplicate checks, and area calculation in `EPSG:32138`.

## 5. Context Layer Catalog

The real estate layer catalog packages boundaries, submarkets, Opportunity Zones, and school district context into platform-ready GIS layers. The catalog records source, category, feature count, geometry types, CRS, area, output paths, status, and notes.

School district boundaries are neutral education context overlays only. They are not ranking criteria, demographic targeting inputs, or fair-housing-risk scoring variables.

HUD Opportunity Zones are policy and incentive context only. They are not demographic targeting inputs.

## 6. Candidate Screening Foundation

Official Dallas CAD parcel data is not used yet. Until parcel geometry is acquired and validated, the project uses analyst-defined grid proxy polygons clipped to Dallas County. These polygons are labeled with `candidate_source = analyst_defined_grid_proxy` and `is_official_parcel = False`.

The proxy approach allows the project to develop screening logic, context overlays, output schemas, and audit tables against real geography without inventing parcel ownership or legal parcel boundaries.

Initial screening rules check geometry validity, minimum and maximum area, boundary-edge fragmentation, waterbody overlap, and submarket assignment. Boundary-edge fragments below 60% of a full 1,000m grid cell are disqualified because partial clipped proxy cells are less reliable for candidate screening.

Waterbody exclusion uses U.S. Census TIGER/Line 2025 Dallas County Area Water polygons. Candidate proxy cells fail `rule_waterbody_overlap` when the candidate centroid falls inside a waterbody or when at least 10% of the candidate area overlaps a waterbody. This rule was added after cartographic QA revealed that basemap context could surface obvious waterbody conflicts, but basemap tiles themselves are not used as analysis input.

Each candidate receives failed rule counts, failed rule names, primary disqualification reason, and screening stage.

School district context and Opportunity Zone context are not qualification rules.

## 7. Weighted Scoring And Ranking

The `v2_professional_proxy_screening_limited` model ranks only qualified analyst-defined grid proxy candidates. It is a transparent professional proxy screening score for portfolio demonstration, not legal parcel valuation, entitlement review, engineering assessment, appraisal, underwriting, or development feasibility.

The v2 model removes school district scoring and geometry-validity bonus scoring because those fields are neutral context or QA requirements, not positive site-quality factors. It reduces Opportunity Zone influence to a small policy/incentive factor.

The weighted v2 model uses:

- 30% developable geometry score: usable proxy footprint size and retained grid-cell integrity.
- 25% constraint avoidance score: residual waterbody overlap, distance to Census Area Water, and edge integrity.
- 25% spatial context score: distance to a project-defined Downtown Dallas reference point, local qualified-candidate cluster density, and distance from the Dallas County boundary.
- 15% neutral submarket context score: moderated candidate-supply distribution by analyst-defined ZCTA submarket.
- 5% Opportunity Zone incentive context score: policy/incentive context only.

Road accessibility, FEMA flood constraints, and NCTCOG land-use suitability are not implemented because those source layers are not staged in the current local workflow. The model is therefore marked as limited and includes data-availability warnings. It does not silently replace missing professional variables with constant scores.

School district context remains neutral metadata only. The model does not use school quality, school ratings, demographics, income, race, ethnicity, protected-class variables, or fair-housing-risk variables.

Opportunity Zones are policy/incentive context only.

For this portfolio release, `v2_professional_proxy_screening_limited` is frozen. The scoring weights sum to 100%, candidate ID is used only as a deterministic final tie-breaker after score and component fields, and repeat-run QA checks confirm the same code, data, and model reproduce the same Top 25. The Top 25 differs from earlier v1 outputs because the model was upgraded to include waterbody exclusion, revised spatial/context variables, and reduced coarse proxy variables.

## 8. Platform-Ready Exports

The final export workflow packages key layers as platform-ready GeoJSON files in `EPSG:4326`, a manifest CSV, an export summary CSV, and a GeoPackage.

The manifest records category, input path, output path, feature count, geometry types, CRS, file size, area, status, and notes. GeoPackage delivery keeps related layers together for QGIS or desktop GIS review, while the GeoJSON folder supports upload to web mapping and portfolio platforms.

## 9. Interactive Web Map

The interactive Folium/Leaflet map visualizes the platform-ready GeoJSON package. It includes core boundaries, ZCTA submarket proxies, Opportunity Zones, school district context, qualified and disqualified proxy candidates, ranked candidates, and the top 25 candidates.

The map is a client-facing demonstration artifact for reviewing geography, screening outputs, rankings, and context layers without desktop GIS software.

## 10. Static Map Exports

Static PNG/PDF map exports provide portfolio-ready visuals for website screenshots, case-study figures, PDF inserts, and optional QGIS refinement. They complement the interactive map with fixed views of the study area, screening workflow, and top-ranked proxy sites.

Static maps are plotted in `EPSG:32138` for consistent DFW map geometry and exported to `outputs/maps/`.

## 11. Limitations

No official parcel ownership or legal parcel boundary data is used yet. Candidate polygons are analyst-defined grid proxies, not official parcels.

Scores are proxy rankings for portfolio demonstration, not legal development feasibility, valuation, appraisal, underwriting, zoning, flood, engineering, or entitlement determinations.

Waterbody exclusion is an initial screening QA rule only. Official parcel records, zoning, ownership, floodplain, utilities, road access, engineering constraints, and current site conditions still require parcel-level validation before acquisition analysis.

School district context is neutral context only. Opportunity Zones are policy/incentive context only. This project does not use demographic targeting language or protected-class logic.
