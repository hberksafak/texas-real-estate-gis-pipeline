# Data Sources

Draft source inventory for the Texas Real Estate Sourcing GIS Pipeline & Parcel Screening System.

| Source | Planned Use | Expected Format | Notes |
|---|---|---|---|
| U.S. Census TIGER/Line ZCTA boundaries | Build ZCTA-based submarkets and geographic summaries | Shapefile / GeoPackage | Use current or analysis-year TIGER/Line releases. |
| U.S. Census CBSA boundary | Define the DFW metropolitan context | Shapefile / GeoPackage | Used for regional clipping and context maps. |
| NCTCOG regional GIS / land use | Regional planning, land use, and contextual overlays | Shapefile / GeoPackage / GIS service | Confirm available layers, coverage, and license terms. |
| Dallas Central Appraisal District parcel shapefile | Parcel geometry and appraisal attributes for Dallas County screening | Shapefile / GeoPackage | Primary parcel source for Dallas County focus. |
| TxDOT roadways | Highway and roadway access analysis | Shapefile / GeoPackage / GIS service | Used for proximity and accessibility measures. |
| FEMA National Flood Hazard Layer | Flood-zone disqualification and risk context | Shapefile / GeoPackage / GIS service | Used to flag or exclude flood-risk parcels. |
| Texas school district boundaries | School district context and market segmentation | Shapefile / GeoPackage | Use authoritative state or district boundary source. |
| HUD Opportunity Zones | Incentive and investment-zone overlay | Shapefile / GeoPackage / CSV plus geometry | Used as a candidate enrichment and screening field. |
| OpenStreetMap amenities / roads | Amenity, road, and local access enrichment | OSM extract / API-derived GeoDataFrame | Use OSMnx for reproducible extraction where appropriate. |
| Microsoft Global ML Building Footprints | Optional building-footprint enrichment | GeoJSON / CSV / Parquet | Optional source for structure density and developed-site context. |

No data has been downloaded yet.
