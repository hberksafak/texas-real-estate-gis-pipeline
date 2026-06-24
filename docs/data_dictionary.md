# Data Dictionary

Draft planned fields for future pipeline outputs. Field names may change after real data is reviewed.

## Submarkets

| Field | Description |
|---|---|
| `submarket_id` | Stable identifier for each submarket. |
| `zcta` | Standardized five-character Census ZCTA code used for assignment. |
| `submarket_name` | Human-readable submarket label. |
| `zcta_count` | Count of ZCTAs assigned to the dissolved submarket polygon. |
| `zcta_list` | Semicolon-delimited list of ZCTAs included in the submarket. |
| `total_area_sq_km` | Dissolved submarket area in square kilometers, calculated in the analysis CRS. |
| `definition_method` | Method used to assign ZCTAs to submarkets. Current value: `centroid_direction_sector_proxy`. |
| `is_official_submarket` | Boolean flag indicating whether the boundary is official. Current analyst-defined proxy value is `False`. |
| `source_note` | Limitation note explaining that the grouping is an analyst-defined ZCTA sector proxy for portfolio demonstration and not an official commercial submarket boundary. |
| `county_name` | County name associated with the submarket. |
| `cbsa_name` | Metropolitan area name. |
| `area_sq_mi` | Submarket area in square miles, calculated in the analysis CRS. |
| `geometry` | Submarket geometry. |

## Candidate Sites

| Field | Description |
|---|---|
| `candidate_id` | Stable identifier for each candidate site. |
| `candidate_source` | Source classification for the candidate geometry. Current proxy value: `analyst_defined_grid_proxy`. |
| `is_official_parcel` | Boolean flag indicating whether the candidate is an official parcel. Current proxy value is `False`. |
| `area_sq_m` | Candidate polygon area in square meters, calculated in `EPSG:32138`. |
| `full_grid_area_sq_m` | Full unclipped grid-cell area in square meters. With the current 1,000m grid this is `1000000`. |
| `area_ratio_to_full_grid` | Candidate area divided by the full grid-cell area, used to identify clipped boundary fragments. |
| `water_overlap_sq_m` | Candidate area overlapping Census TIGER/Line Dallas County Area Water polygons, calculated in square meters. |
| `water_overlap_ratio` | Candidate water overlap area divided by candidate area. A ratio of `0.10` or greater fails the waterbody screening rule. |
| `centroid_inside_water` | Boolean flag indicating whether the candidate centroid falls inside a Census Area Water polygon. |
| `rule_waterbody_overlap` | Boolean screening rule failure flag. `True` means the candidate centroid is inside water or its water overlap ratio is at least `0.10`. Safe/qualified candidates should have `False`. |
| `area_acres` | Candidate polygon area in acres, calculated from `area_sq_m`. |
| `qualified` | Boolean result of the initial proxy screening rules. |
| `failed_rule_count` | Count of failed screening rules for the candidate. |
| `failed_rules` | Semicolon-delimited rule names failed by the candidate. |
| `primary_disqualification_reason` | First failed rule, used as the primary audit reason. |
| `screening_stage` | Screening stage label, such as `passed_initial_proxy_screening` or `failed_initial_proxy_screening`. |
| `rule_edge_fragment` | Screening rule requiring candidates to retain at least 60% of a full 1,000m grid cell after clipping to Dallas County. |
| `edge_fragment_candidate_count` | Summary count of candidates disqualified or flagged by the edge-fragment area-ratio rule. |
| `waterbody_disqualified_candidate_count` | Summary count of candidates failing `rule_waterbody_overlap`. |
| `centroid_inside_water_count` | Summary count of candidates whose centroids fall inside Census Area Water polygons. |
| `water_overlap_candidate_count` | Summary count of candidates with any positive waterbody overlap area. |
| `water_overlap_threshold` | Water overlap ratio threshold used by the screening workflow. Current value: `0.10`. |
| `max_water_overlap_ratio` | Maximum water overlap ratio observed among candidate proxy polygons. |
| `opportunity_zone_context` | Boolean flag indicating whether the candidate overlaps an Opportunity Zone. Incentive context only. |
| `school_district_context` | Boolean flag indicating whether school district context was assigned. Neutral context only. |
| `school_district_name` | School district name or fallback identifier assigned by largest overlap. |
| `parcel_id` | Source parcel identifier where available. |
| `site_name` | Optional display name for the candidate. |
| `county_name` | County name. |
| `zcta` | ZCTA code. |
| `land_area_sqft` | Parcel or site land area in square feet. |
| `land_area_acres` | Parcel or site land area in acres. |
| `owner_name` | Owner name where source data permits use. |
| `property_address` | Site address where available. |
| `geometry` | Candidate geometry. |

## Screening Audit Fields

| Field | Description |
|---|---|
| `screen_status` | Overall screening result, such as qualified or disqualified. |
| `disqualified` | Boolean flag for candidate disqualification. |
| `disqualification_reasons` | Concatenated explanation of failed screening rules. |
| `min_area_pass` | Whether the site passes minimum area criteria. |
| `flood_zone_flag` | Whether the site intersects mapped flood risk. |
| `road_access_pass` | Whether the site passes road access criteria. |
| `land_use_pass` | Whether the site passes planned land-use criteria. |
| `geometry_valid` | Whether the geometry is valid after cleaning. |
| `rule_waterbody_overlap` | Whether the candidate fails the waterbody exclusion QA rule. |

## Scoring Fields

| Field | Description |
|---|---|
| `developable_geometry_score` | V2 0-100 score combining usable proxy footprint size and retained grid-cell integrity. |
| `constraint_avoidance_score` | V2 0-100 score penalizing residual waterbody overlap, proximity to Census Area Water, and edge-fragment risk. |
| `spatial_context_score` | V2 0-100 neutral spatial score using Downtown Dallas reference distance, local candidate cluster density, and Dallas County boundary distance. |
| `submarket_context_score` | V2 0-100 neutral score based on moderated candidate supply distribution by analyst-defined submarket. Does not imply demand or performance. |
| `opportunity_incentive_score` | V2 0-100 policy/incentive context score based on Opportunity Zone overlap. Not demographic targeting. |
| `developable_geometry_contribution` | Weighted contribution of `developable_geometry_score` to `final_site_score`. |
| `constraint_avoidance_contribution` | Weighted contribution of `constraint_avoidance_score` to `final_site_score`. |
| `spatial_context_contribution` | Weighted contribution of `spatial_context_score` to `final_site_score`. |
| `submarket_context_contribution` | Weighted contribution of `submarket_context_score` to `final_site_score`. |
| `opportunity_incentive_contribution` | Weighted contribution of `opportunity_incentive_score` to `final_site_score`. |
| `usable_area_score` | Footprint-size score adapted to analyst-defined 1,000m proxy cells. |
| `area_integrity_score` | Score derived from `area_ratio_to_full_grid`. |
| `edge_integrity_score` | Edge reliability score used in constraint scoring. |
| `water_avoidance_score` | Score penalizing water overlap below the disqualification threshold. |
| `distance_to_waterbody_m` | Candidate centroid distance to staged Census Area Water geometry in meters. |
| `waterbody_distance_score` | Score derived from `distance_to_waterbody_m`. |
| `distance_to_dallas_cbd_km` | Candidate centroid distance to the project-defined Downtown Dallas reference point in kilometers. |
| `distance_to_dallas_cbd_score` | Score derived from `distance_to_dallas_cbd_km`. |
| `local_candidate_count_5km` | Count of qualified proxy candidate centroids within 5 km, excluding the candidate itself. |
| `candidate_cluster_score` | Score derived from local candidate cluster density. |
| `distance_to_county_boundary_m` | Candidate centroid distance to Dallas County boundary in meters. |
| `county_edge_score` | Score derived from `distance_to_county_boundary_m`. |
| `road_accessibility_score` | Not implemented in v2 limited because TxDOT/OSM roads are not staged. |
| `flood_constraint_score` | Not implemented in v2 limited because FEMA NFHL is not staged. |
| `land_use_context_score` | Not implemented in v2 limited because NCTCOG land-use data is not staged. |
| `model_data_completeness_score` | Model-level data completeness indicator for implemented versus missing recommended scoring factors. |
| `model_data_completeness_note` | Text description of implemented and missing v2 scoring data families. |
| `data_availability_warning` | Warning that roads, FEMA flood, and land-use suitability are not implemented in the current local workflow. |
| `final_site_score` | Weighted final professional proxy screening score. |
| `candidate_rank` | Deterministic rank among qualified proxy candidates, with 1 as the highest score. |
| `scoring_model_version` | Scoring model version identifier. Current value: `v2_professional_proxy_screening_limited`. |
| `scoring_note` | Limitation note stating that the score is a transparent proxy ranking for portfolio demonstration and not parcel acquisition due diligence. |

Legacy v1 fields such as `school_context_score` and `geometry_score` were removed from the final weighted score because school district context is neutral metadata and geometry validity is a QA requirement rather than a positive site-quality factor.

## Scoring Model Manifest

Fields written to `outputs/tables/scoring_model_manifest.csv`.

| Field | Description |
|---|---|
| `model_version` | Frozen scoring model version for the portfolio release. |
| `scoring_weights` | JSON-encoded component weights used by the v2 scoring model. |
| `weights_sum` | Sum of scoring weights; expected value is `1.0`. |
| `waterbody_threshold` | Water overlap ratio threshold used by the screening workflow. |
| `edge_fragment_threshold` | Minimum retained area ratio for clipped 1,000m proxy grid cells. |
| `missing_professional_variables` | Recommended professional variables not implemented because source layers are not staged. |
| `deterministic_sort` | Ranking sort order, including candidate ID as the final deterministic tie-breaker only. |
| `generated_at` | Timestamp when the manifest was generated. |

## Layer Validation Report

Fields written to `data/final/csv/layer_validation_report.csv`.

| Field | Description |
|---|---|
| `layer_name` | Logical layer name used by the validation workflow. |
| `input_path` | Source file path read by the validation workflow. |
| `feature_count_before` | Feature count immediately after reading the input layer. |
| `feature_count_after` | Feature count after CRS standardization, geometry cleaning, empty-geometry removal, and duplicate checks. |
| `crs_before` | CRS reported by the input layer. |
| `crs_after` | CRS after validation, expected to be `EPSG:4326`. |
| `geometry_types` | Semicolon-delimited geometry types present after validation. |
| `invalid_geometries_before` | Count of invalid non-empty geometries before repair. |
| `invalid_geometries_after` | Count of invalid non-empty geometries after repair. |
| `empty_geometries_before` | Count of null or empty geometries before cleaning. |
| `empty_geometries_after` | Count of null or empty geometries after cleaning. |
| `duplicate_rows_removed` | Number of exact duplicate records removed. |
| `total_area_sq_km` | Total layer area in square kilometers, calculated in `EPSG:32138`. |
| `status` | Validation status, such as `passed`, `warning`, or `failed`. |
| `notes` | Human-readable validation notes and repair actions. |

## Real Estate Layer Catalog

Fields written to `data/final/csv/real_estate_layer_catalog.csv`.

| Field | Description |
|---|---|
| `layer_name` | Logical layer name used in GeoJSON, GeoPackage, and catalog outputs. |
| `category` | Layer category, such as `boundary`, `submarket`, `incentive_context`, or `education_context`. |
| `source` | Human-readable source or derivation description. |
| `source_type` | Source handling type, such as existing validated layer or manually placed public source file. |
| `feature_count` | Number of features available in the layer. |
| `geometry_types` | Semicolon-delimited geometry types present in the layer. |
| `crs` | Final layer CRS, expected to be `EPSG:4326` for available platform layers. |
| `total_area_sq_km` | Total area in square kilometers, calculated in `EPSG:32138`. |
| `output_geojson` | Platform-ready GeoJSON path for the layer when available or expected. |
| `gpkg_layer_name` | GeoPackage layer name when exported. |
| `status` | Availability status, such as `available` or `missing`. |
| `notes` | Source limitations, optional-layer fallback notes, and neutral-use warnings. |

## Platform Layers Manifest

Fields written to `data/final/csv/platform_layers_manifest.csv`.

| Field | Description |
|---|---|
| `layer_name` | Platform export layer name. |
| `category` | Layer category, such as `boundary`, `submarket`, `incentive_context`, `education_context`, `candidate_screening`, or `candidate_ranking`. |
| `input_path` | Source GeoJSON path used for the platform export. |
| `output_geojson_path` | Platform-ready GeoJSON export path. |
| `gpkg_layer_name` | Matching layer name in `export_ready_layers.gpkg`. |
| `feature_count` | Number of features exported. |
| `geometry_types` | Semicolon-delimited geometry types present after export cleaning. |
| `crs` | Export CRS, expected to be `EPSG:4326`. |
| `total_area_sq_km` | Total layer area in square kilometers, calculated in `EPSG:32138`. |
| `file_size_mb` | GeoJSON file size in megabytes. |
| `status` | Export status for the layer. |
| `notes` | Delivery notes and context-use limitations. |

## Platform Export Summary

Fields written to `data/final/csv/platform_export_summary.csv`.

| Field | Description |
|---|---|
| `total_layers_expected` | Count of expected platform export layers. |
| `total_layers_exported` | Count of layers successfully exported. |
| `total_layers_missing` | Count of expected layers that were not present at export time. |
| `total_features_exported` | Total features across exported layers. |
| `total_geojson_size_mb` | Combined GeoJSON export size in megabytes. |
| `export_crs` | CRS used for platform GeoJSON exports, expected to be `EPSG:4326`. |
| `export_package_status` | Overall package status, such as `complete` or `partial`. |
| `export_note` | Package-level delivery notes and context-use limitations. |

## Web Map Layer Summary

Fields written to `outputs/tables/webmap_layer_summary.csv`.

| Field | Description |
|---|---|
| `layer_name` | Layer identifier used by the web map script. |
| `input_path` | Platform-ready GeoJSON input path used for the web map. |
| `feature_count` | Number of features in the input layer. |
| `added_to_map` | Boolean flag indicating whether the layer was added to the map. |
| `default_visible` | Boolean flag indicating whether the layer is visible when the map first opens. |
| `notes` | Layer-specific display notes and context-use limitations. |

## Static Map Export Summary

Fields written to `outputs/tables/static_map_export_summary.csv`.

| Field | Description |
|---|---|
| `map_name` | Static map export identifier. |
| `png_path` | PNG output path. |
| `pdf_path` | PDF output path. |
| `layers_used` | Semicolon-delimited list of layers used in the map. |
| `output_purpose` | Portfolio or case-study use for the map. |
| `status` | Export status for the map. |
| `notes` | Map-level limitations and source notes. |

## Scoring Component Variance Audit

Fields written to `outputs/tables/scoring_component_variance_audit.csv`.

| Field | Description |
|---|---|
| `component_name` | Scoring component audited. Includes legacy v1 components and v2 implemented/missing components. |
| `weight` | Component weight in the relevant model. Missing recommended components have `0.0`. |
| `min` | Minimum component value. |
| `max` | Maximum component value. |
| `mean` | Mean component value. |
| `std` | Population standard deviation. |
| `unique_value_count` | Count of unique non-missing component values. |
| `percent_missing` | Percent of candidates with missing values for the component. |
| `percent_default_value` | Percent of candidates equal to the designated default value, where applicable. |
| `recommendation` | Audit recommendation, such as `keep`, `reduce_weight`, `remove`, `replace`, or not-implemented source status. |

## Top 25 Scoring Audit

Fields written to `outputs/tables/top25_scoring_audit.csv`.

| Field | Description |
|---|---|
| `candidate_rank` | Candidate rank after v2 scoring. |
| `candidate_id` | Candidate identifier. |
| `final_site_score` | Final v2 weighted score. |
| `developable_geometry_score` | V2 geometry component score. |
| `constraint_avoidance_score` | V2 constraint component score. |
| `spatial_context_score` | V2 neutral spatial context score. |
| `submarket_context_score` | V2 neutral submarket context score. |
| `opportunity_incentive_score` | V2 Opportunity Zone policy/incentive score. |
| `*_contribution` | Weighted contribution fields for each v2 component. |
| `distance_to_waterbody_m` | Distance to Census Area Water in meters. |
| `distance_to_county_boundary_m` | Distance to Dallas County boundary in meters. |
| `distance_to_dallas_cbd_km` | Distance to project-defined Downtown Dallas reference in kilometers. |
| `local_candidate_count_5km` | Local qualified-candidate count within 5 km. |
| `road_accessibility_score` | Missing in v2 limited because road source is not staged. |
| `flood_constraint_score` | Missing in v2 limited because FEMA source is not staged. |
| `land_use_context_score` | Missing in v2 limited because land-use source is not staged. |
| `water_overlap_ratio` | Candidate water overlap ratio. |
| `centroid_inside_water` | Waterbody centroid QA flag. |
| `rule_waterbody_overlap` | Waterbody rule failure flag. |
| `rule_edge_fragment` | Edge-fragment rule failure flag. |
| `failed_rule_count` | Count of failed screening rules. Top 25 candidates should have `0`. |
| `ranking_notes` | Short explanation of the candidate's high-ranking factors. |

## Repository QA Report

Fields written to `outputs/tables/repository_qa_report.csv`.

| Field | Description |
|---|---|
| `check_name` | Human-readable QA check name. |
| `path` | File path checked by the QA script. |
| `exists` | Boolean flag indicating whether the path exists locally. |
| `status` | Check result, such as `passed` or `failed`. |
| `notes` | Notes explaining whether the file is tracked documentation, a script, or an ignored generated output. |

## Top 25 Rank Stability Audit

Fields written to `outputs/tables/top25_rank_stability_audit.csv`.

| Field | Description |
|---|---|
| `candidate_rank` | Compared rank position from the repeat-run stability test. |
| `candidate_id_run_1` | Candidate ID at this rank in the first pipeline run. |
| `candidate_id_run_2` | Candidate ID at this rank in the second pipeline run. |
| `score_run_1` | Final site score at this rank in the first pipeline run. |
| `score_run_2` | Final site score at this rank in the second pipeline run. |
| `rank_match` | Boolean flag confirming the rank number matches across runs. |
| `id_match` | Boolean flag confirming the candidate ID matches across runs. |
| `score_match` | Boolean flag confirming the final score matches across runs. |
| `notes` | Stability audit notes for the compared rank. |

## Top 25 Quality Audit

Fields written to `outputs/tables/top25_quality_audit.csv`.

| Field | Description |
|---|---|
| `candidate_rank` | Rank from the weighted candidate scoring workflow. |
| `candidate_id` | Candidate identifier. |
| `final_site_score` | Final weighted proxy score. |
| `qualified` | Screening qualification flag. |
| `is_official_parcel` | Boolean flag confirming the candidate is not an official parcel in the current proxy workflow. |
| `candidate_source` | Candidate geometry source, currently `analyst_defined_grid_proxy`. |
| `submarket` | Assigned ZCTA-based submarket proxy. |
| `opportunity_zone_flag` | Opportunity Zone policy/incentive context flag. |
| `school_district_context` | Neutral school district context assignment flag. |
| `school_district_name` | Assigned school district context name, where available. |
| `area_ratio_to_full_grid` | Candidate area divided by a full 1,000m grid cell. |
| `water_overlap_ratio` | Candidate water overlap ratio from Census Area Water. |
| `centroid_inside_water` | Whether the candidate centroid falls inside a Census Area Water polygon. |
| `rule_waterbody_overlap` | Waterbody rule failure flag. Top 25 candidates should have `False`. |
| `failed_rule_count` | Count of failed screening rules. Top 25 candidates should have `0`. |
| `failed_rules` | Semicolon-delimited failed rule names, if any. |
| `primary_disqualification_reason` | First failed rule for disqualified candidates, blank for qualified Top 25 candidates. |
