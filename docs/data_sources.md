# Data Sources

Verified source plan for the Texas Real Estate Sourcing GIS Pipeline & Parcel Screening System.

No data has been downloaded yet. This document records the intended source systems, planned use, and source-specific limitations before the first real-data milestone.

| Priority | Source | Planned Use | Decision | Notes |
|---:|---|---|---|---|
| 1 | U.S. Census TIGER/Line 2025 | Counties, CBSA / MSA boundary, and ZCTA boundaries if available / appropriate | Use as core boundary source. | Platform workflow will clip the DFW / Dallas County study area from Census boundaries. TIGER/Line 2025 includes county, CBSA, and ZCTA520 downloads. |
| 2 | NCTCOG Regional Data Center / Open Data | Regional GIS context, land use / land cover proxy, and DFW regional context layers | Use as official regional source. | 2020 Land Use is a useful zoning/land-use style proxy. Treat as context/proxy, not legal zoning. |
| 3 | TxDOT Roadway Inventory / TxDOT GIS Open Data | Road access proximity and accessibility metrics | Use for transportation context and proximity calculations. | Prefer TxDOT GIS Open Data and Roadway Inventory layers for authoritative roadway context. |
| 4 | FEMA National Flood Hazard Layer | Flood constraint overlay and flood disqualification or penalty metric | Use current effective flood hazard data only. | Prefer county/state shapefile or service download. Treat as a screening layer, not an engineering, insurance, or legal flood determination. |
| 5 | Texas School District Boundaries | School district context overlay | Use as neutral context only. | Prefer Texas Legislative Council / Texas Capitol Data Portal 2025-2026 School Year Districts shapefile if accessible. Do not use for discriminatory or fair-housing-risk ranking. Keep analysis language neutral and descriptive. If a stable direct download URL is not confirmed, place the official file manually under `data/raw/texas_school_districts/`. |
| 6 | HUD Opportunity Zones | Incentive/context overlay | Use as business and incentive context. | Use HUD Open Data / ArcGIS Hub source. Do not use demographic targeting language. Use the tract overlay only as a policy/incentive geography. If a stable direct download URL is not confirmed, place the official file manually under `data/raw/hud_opportunity_zones/`. |
| 7 | Dallas Central Appraisal District GIS data products | Dallas County parcel screening pilot if parcel shapefile is downloadable and suitable | Use for parcel pilot only after size, schema, license, and suitability checks. | 2026 parcel geometry zip may be named `PARCEL_GEOM.zip`. Document DCAD limitations and disclaimer. Do not claim survey, engineering, or legal accuracy. If blocked or too large, use a candidate polygon proxy instead. |
| 8 | OpenStreetMap via OSMnx | Amenities, services, and road/service access support layer | Use as supporting accessibility source only. | Attribute OpenStreetMap contributors. Treat OSM as supplemental rather than authoritative parcel, zoning, or regulatory data. |
| 9 | Microsoft Global ML Building Footprints | Optional building density proxy | Optional enrichment source. | Use only if local quality is acceptable after visual QA against Dallas County context. |

## Source Links

| Source | Official Link |
|---|---|
| U.S. Census TIGER/Line Shapefiles | <https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html> |
| U.S. Census TIGER/Line 2025 FTP archive | <https://www2.census.gov/geo/tiger/TIGER2025/> |
| NCTCOG Regional Data Center / Open Data | <https://data-nctcoggis.opendata.arcgis.com/> |
| Dallas CAD GIS Data Products | <https://www.dallascad.org/GISDataProducts.aspx> |
| Dallas CAD Data Products | <https://www.dallascad.org/DataProducts.aspx> |
| TxDOT GIS Open Data Portal | <https://gis-txdot.opendata.arcgis.com/> |
| FEMA Flood Map Service Center | <https://msc.fema.gov/portal/advanceSearch> |
| FEMA NFHL ArcGIS REST service | <https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer> |
| Texas Education Agency School District Locator | <https://tea.texas.gov/families-and-students/school-district-locator/school-district-locator> |
| Texas Capitol Data Portal | <https://data.capitol.texas.gov/> |
| HUD Opportunity Zones Open Data | <https://hudgis-hud.opendata.arcgis.com/datasets/HUD::opportunity-zones/about> |
| OSMnx documentation | <https://osmnx.readthedocs.io/> |
| OpenStreetMap copyright and attribution | <https://www.openstreetmap.org/copyright> |
| Microsoft Global ML Building Footprints | <https://github.com/microsoft/GlobalMLBuildingFootprints> |

## Current Source Decisions

- Use Census TIGER/Line 2025 as the authoritative starting point for administrative and statistical boundaries.
- Use Census boundaries to define and clip the DFW / Dallas County study area before downloading or processing heavier thematic layers.
- Use NCTCOG regional layers for market context and land-use-style interpretation, while clearly labeling land use as a proxy rather than legal zoning.
- Use Dallas CAD parcel geometry only after confirming that the downloadable parcel shapefile is usable for the pilot workflow.
- Keep flood, school district, and Opportunity Zone layers as screening/context overlays with careful limitation language.
- For Milestone 6, use manual raw-file fallback detection for HUD Opportunity Zones and Texas school districts unless stable official direct download URLs are confirmed.
- Use OSMnx and Microsoft building footprints as optional/supporting enrichment sources, not as replacements for official public sources.
