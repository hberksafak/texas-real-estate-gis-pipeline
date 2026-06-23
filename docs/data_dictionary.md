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
| `area_acres` | Candidate polygon area in acres, calculated from `area_sq_m`. |
| `qualified` | Boolean result of the initial proxy screening rules. |
| `failed_rule_count` | Count of failed screening rules for the candidate. |
| `failed_rules` | Semicolon-delimited rule names failed by the candidate. |
| `primary_disqualification_reason` | First failed rule, used as the primary audit reason. |
| `screening_stage` | Screening stage label, such as `passed_initial_proxy_screening` or `failed_initial_proxy_screening`. |
| `rule_edge_fragment` | Screening rule requiring candidates to retain at least 60% of a full 1,000m grid cell after clipping to Dallas County. |
| `edge_fragment_candidate_count` | Summary count of candidates disqualified or flagged by the edge-fragment area-ratio rule. |
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

## Scoring Fields

| Field | Description |
|---|---|
| `size_score` | 0-100 proxy score for candidate size suitability relative to the 25-120 acre ideal range. |
| `grid_completeness_score` | 0-100 score based on how much of the full 1,000m grid cell remains after clipping. |
| `submarket_score` | Neutral 0-100 score based on moderated candidate supply distribution by analyst-defined submarket. Does not imply demand or performance. |
| `opportunity_score` | 0-100 policy/incentive context score based on Opportunity Zone overlap. Not demographic targeting. |
| `school_context_score` | 0-100 neutral context completeness score based only on whether a clean school district assignment exists. |
| `geometry_score` | 0-100 geometry reliability score based on geometry validity. |
| `final_site_score` | Weighted final proxy sourcing score. |
| `candidate_rank` | Deterministic rank among qualified proxy candidates, with 1 as the highest score. |
| `scoring_model_version` | Scoring model version identifier. Current value: `v1_proxy_candidate_scoring`. |
| `scoring_note` | Limitation note stating that the score is a transparent proxy ranking for portfolio demonstration and not legal parcel valuation or development feasibility. |
| `score_total` | Final weighted score. |
| `score_access` | Transportation and access score. |
| `score_market` | Market or submarket context score. |
| `score_constraints` | Constraint and risk score. |
| `score_amenities` | Amenity proximity score. |
| `score_strategy` | Strategic fit score. |
| `rank_overall` | Overall rank among qualified candidates. |
| `score_notes` | Notes explaining scoring exceptions or manual review flags. |

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
