# Expected Generated Outputs

This file documents the local outputs expected after running:

```bash
python3 scripts/check_required_sources.py
python3 scripts/run_full_pipeline.py
```

Generated raw data, intermediate files, final GIS outputs, maps, tables, and the
web map are intentionally ignored by git. They are regenerated locally so a
portfolio reviewer can verify the pipeline without committing large GIS files.

Exact current release outputs assume the documented HUD Opportunity Zone and
Texas school district context source files have been staged locally under
`data/raw/hud_opportunity_zones/` and `data/raw/texas_school_districts/`.
Census TIGER/Line source ZIPs are downloaded or reused automatically.
The source preflight stops the full runner before output generation when these
manual context files are missing.

## `data/final/geojson/`

Core generated GeoJSON outputs include:

- `dallas_county_boundary.geojson`
- `dfw_cbsa_boundary.geojson`
- `dfw_zctas.geojson`
- `dfw_zcta_submarkets.geojson`
- `dfw_opportunity_zones.geojson`
- `dfw_school_districts.geojson`
- `dallas_waterbodies.geojson`
- `parcel_screening_candidates.geojson`
- `qualified_candidate_sites.geojson`
- `disqualified_candidate_sites.geojson`
- `ranked_site_candidates.geojson`
- `top_25_candidate_sites.geojson`
- `platform_export/`

## `data/final/csv/`

Key generated CSV outputs include:

- `study_area_summary.csv`
- `submarket_summary.csv`
- `layer_validation_report.csv`
- `real_estate_layer_catalog.csv`
- `disqualification_audit.csv`
- `candidate_summary.csv`
- `ranked_site_candidates.csv`
- `candidate_score_components.csv`
- `platform_layers_manifest.csv`
- `platform_export_summary.csv`

## `data/final/gpkg/`

Key generated GeoPackage outputs include:

- `census_study_area.gpkg`
- `dfw_submarkets.gpkg`
- `validated_real_estate_layers.gpkg`
- `real_estate_layer_catalog.gpkg`
- `parcel_screening_foundation.gpkg`
- `ranked_candidate_sites.gpkg`
- `export_ready_layers.gpkg`

## `outputs/maps/png/`

Static PNG portfolio maps:

- `dfw_study_area_overview.png`
- `dallas_candidate_screening_map.png`
- `top_25_candidate_sites_map.png`

## `outputs/maps/pdf/`

Static PDF portfolio maps:

- `dfw_study_area_overview.pdf`
- `dallas_candidate_screening_map.pdf`
- `top_25_candidate_sites_map.pdf`

## `outputs/tables/`

Generated QA and reporting tables include:

- `webmap_layer_summary.csv`
- `static_map_export_summary.csv`
- `repository_qa_report.csv`
- `top25_quality_audit.csv`
- `top25_rank_stability_audit.csv`
- `top25_scoring_audit.csv`
- `scoring_model_manifest.csv`
- `scoring_component_variance_audit.csv`

## `outputs/webmap/`

Interactive web map output:

- `texas_real_estate_sourcing_webmap.html`

## Notes

- Candidate geometries are analyst-defined grid proxies, not official parcels.
- Scores are proxy rankings for portfolio demonstration only.
- Opportunity Zones are policy/incentive context only.
- School districts are neutral context overlays only.
- The frozen v2 scoring model does not include road accessibility, FEMA flood,
  or NCTCOG land-use suitability because those source layers are not staged in
  this local release workflow.
