# QGIS Workspace

Store QGIS project files, layer styling, print layouts, and atlas configuration notes here.

Generated map exports should be written to `outputs/maps/` rather than committed from this folder.

## Optional QGIS Map Refinement

The static map workflow exports portfolio-ready PNG/PDF maps with Python, but the same layers can be refined in QGIS for custom labels, print layouts, or atlas production.

Recommended source packages:

- `data/final/gpkg/export_ready_layers.gpkg`
- `data/final/gpkg/ranked_candidate_sites.gpkg`
- `data/final/gpkg/parcel_screening_foundation.gpkg`
- `outputs/maps/png/`
- `outputs/maps/pdf/`

Suggested layer styling:

- DFW boundary: thin dark gray outline, transparent fill.
- Dallas County boundary: heavier black outline, transparent fill.
- ZCTA submarkets: muted categorical fills with light blue outlines.
- Opportunity Zones: purple transparent fill, optional by default.
- School district context: thin teal or gray outlines, neutral context only.
- Dallas waterbodies: muted blue fill, used as a screening QA constraint layer.
- Ranked candidates: light orange/yellow fill or graduated color by `final_site_score`.
- Top 25 candidates: saturated orange fill with dark outline and optional rank labels.

Generated static map exports:

- `outputs/maps/png/dfw_study_area_overview.png`
- `outputs/maps/pdf/dfw_study_area_overview.pdf`
- `outputs/maps/png/dallas_candidate_screening_map.png`
- `outputs/maps/pdf/dallas_candidate_screening_map.pdf`
- `outputs/maps/png/top_25_candidate_sites_map.png`
- `outputs/maps/pdf/top_25_candidate_sites_map.pdf`

Candidate polygons are analyst-defined grid proxies, not official parcels. Waterbody exclusion is a screening QA rule, not parcel-level due diligence. School districts should remain neutral context overlays only. Opportunity Zones should remain policy/incentive context only.

Before acquisition analysis, validate candidates against official parcel records, zoning, ownership, floodplain, utilities, road access, and legal due diligence sources. Basemaps are for visual context only and should not be treated as analysis data.
