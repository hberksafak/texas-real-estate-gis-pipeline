# Data Dictionary

Draft planned fields for future pipeline outputs. Field names may change after real data is reviewed.

## Submarkets

| Field | Description |
|---|---|
| `submarket_id` | Stable identifier for each submarket. |
| `zcta` | ZCTA code where applicable. |
| `submarket_name` | Human-readable submarket label. |
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
