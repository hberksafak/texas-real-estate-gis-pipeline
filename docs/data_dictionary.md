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
