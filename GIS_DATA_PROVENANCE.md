# BHOOMI-NEXUS: GIS Data Provenance & Source Attribution

**System Version:** 2.4.0 (SIH Production Finishing Release)  
**Standard Coordinate Reference System (CRS):** WGS84 / EPSG:4326  
**National Territory Boundary Extent:** South-West [4.0° N, 65.0° E] to North-East [38.5° N, 100.0° E]  

---

## 1. Overview of Data Provenance Architecture

In mission-critical geospatial and land-governance applications, every piece of telemetry, vector geometry, and administrative boundary displayed to users or decision-makers must carry verifiable data provenance. Bhoomi-Nexus strictly classifies and badges all information according to its authoritative origin.

Under the core operational doctrine:
> **"No data is better than fake data."**
> If an authoritative source cannot provide the requested record via an open, legally compliant service, the platform renders `"Unavailable from authoritative source"` rather than synthesizing values.

---

## 2. Dynamic Provenance Badging System (`<DataSourceBadge />`)

Every visual metric and attribute in Bhoomi-Nexus displays one of the following standardized provenance classifications:

| Badge | Data Type Classification | Description & Examples |
|---|---|---|
| `[CADASTRAL]` | Official Land Records | State Revenue Department / BhuNaksha / NIC cadastral parcel registries. |
| `[OBSERVED]` | In-Situ Telemetry | Physical ground sensors, AWS (Automated Weather Stations), lab soil health cards. |
| `[MODELLED]` | Mathematical Simulation | ECMWF IFS atmospheric model, GFS, WRF short-range weather forecasts. |
| `[REANALYSIS]` | Multi-Decadal Historical | ECMWF ERA5-Land, Copernicus Climate Change Service assimilation. |
| `[SPATIAL ESTIMATE]` | Machine Learning Grids | ISRIC SoilGrids 2.0 (250m resolution random forest spatial predictions). |
| `[REMOTE SENSING]` | Satellite Multi-Spectral | ISRO Cartosat / ResourceSat, ESA Copernicus Sentinel-2 (L2A surface reflectance). |
| `[UNAVAILABLE]` | Authoritative Absence | Data not published via open APIs or requires institutional intranet credentials. |
| `[DEMO]` | Isolated Simulation | Clearly marked test mocks strictly isolated behind explicit Demo Mode toggle. |

> **Note:** The label `[LIVE]` is never used unless an uninterrupted real-time telemetry stream is actively confirmed.

---

## 3. Detailed Data Provenance by Layer & Domain

### 3.1 Administrative Boundaries (States, Districts, Blocks, Gram Panchayats)
- **Authoritative Provider:** National Informatics Centre (NIC), Ministry of Electronics & Information Technology (MeitY), Government of India.
- **Service Endpoint:** `https://mapservice.gov.in/mapserviceserv176/rest/services/Panchayat/AdminGPHierarchy/MapServer`
- **Layers:**
  - Layer 0: State (`STNAME`, `STCODE11`, `State_LGD`)
  - Layer 1: District (`D_Pan_Name`, `stname`, `dtcode11`, `Dist_LGD`)
  - Layer 2: Block / Sub-District (`B_Pan_Name`, `block_name`, `D_Pan_Name`, `block_lgd`)
  - Layer 3: Gram Panchayat (`GPNAME`, `VILNAME11`, `SDTNAME`, `DTNAME`, `GPCODE`)
- **CRS:** EPSG:4326 (WGS84).
- **Attribution:** *"Administrative boundaries © NIC Bharat Maps, Survey of India (Census 2011 codification)"*.
- **Classification:** `[CADASTRAL] / [OFFICIAL NIC]`

### 3.2 Atmospheric Weather & Meteorological Telemetry
- **Provider:** Open-Meteo Integration Engine backed by ECMWF Integrated Forecasting System (IFS) and DWD ICON.
- **Service Endpoint:** `https://api.open-meteo.com/v1/forecast`
- **Parameters:**
  - Ambient Air Temperature (2m, °C)
  - Relative Humidity (2m, %)
  - Apparent / Perceived Surface Temperature (°C)
  - Precipitation Rate (mm/h) & Accumulated Rain (mm)
  - Wind Speed (10m, km/h) & Direction (degrees)
- **Spatial Resolution:** ~11 km grid (ECMWF IFS 0.1°).
- **Temporal Resolution:** Hourly updates, timestamped to IST (Asia/Kolkata).
- **Classification:** `[MODELLED / REANALYSIS]`

### 3.3 Multi-Depth Soil Moisture & Subsurface Thermal Gradients
- **Provider:** ECMWF Land-Surface Assimilation Model (Open-Meteo Reanalysis).
- **Depth Deposition:**
  - Layer 1: 0 – 7 cm (Seedbed & evaporative boundary)
  - Layer 2: 7 – 28 cm (Root-zone active layer)
  - Layer 3: 28 – 100 cm (Subsoil capillary horizon)
  - Layer 4: 100 – 255 cm (Deep hydrological reservoir)
- **Physical Units:**
  - Volumetric Soil Water Content: $m^3/m^3$ (cubic meters of water per cubic meter of soil).
  - Soil Temperature: Degrees Celsius (°C).
- **Classification:** `[MODELLED / REANALYSIS]`

### 3.4 Pedological Soil Chemistry & Physical Properties
- **Provider:** ISRIC — World Soil Information (SoilGrids 2.0).
- **Service Endpoint:** `https://rest.isric.org/soilgrids/v2.0/properties/query`
- **Parameters:**
  - Soil pH (pH in $H_2O$ extract at 0–5 cm and 5–15 cm)
  - Soil Organic Carbon (SOC, g/kg)
  - Clay content (g/100g, %)
  - Sand content (g/100g, %)
  - Silt content (g/100g, %)
  - Cation Exchange Capacity (CEC, $cmol_c/kg$)
  - Nitrogen content ($cg/kg$)
- **Spatial Resolution:** 250 m pixel grid.
- **Methodology:** Ensemble Machine Learning (Random Forests & Gradient Boosting) calibrated against ~240,000 ground soil profiles worldwide.
- **Crucial Provenance Distinction:** SoilGrids is a spatial estimate model. It is NOT a laboratory chemical Soil Health Card test. The system explicitly displays:
  *"SoilGrids predictions represent spatial estimates (250m). Not a substitute for laboratory Soil Health Card testing."*
- **Classification:** `[SPATIAL ESTIMATE (250m)]`

### 3.5 Cadastral Survey & Parcel Boundaries (Khasra & Area)
- **Authoritative Provider:** State Land Records Departments / BhuNaksha Portal (e.g., Rajasthan Bhu-Naksha, Apna Khata).
- **Current Legal/Technical Status:** State cadastral databases require authenticated department credentials, captcha verification, or local intranet access. There is no open, unrestricted public REST/WFS cadastral boundary service.
- **Reporting Standard:**
  - Parcel ID: `Not resolved`
  - Khasra Number: `Unavailable from authoritative cadastral source`
  - Area: `Unavailable`
  - Boundary Geometry: `Authoritative parcel boundary unavailable`
  - Marker Distinction: `LOCATION MARKER ≠ CADASTRAL BOUNDARY` (The pin marks the user click point; no arbitrary circles or polygons are fabricated).
- **Classification:** `[CADASTRAL UNAVAILABLE]`

### 3.6 Remote Sensing / Satellite Vegetation (NDVI)
- **Status:** ESA Copernicus Sentinel-2 Level-2A surface reflectance data is currently unavailable in the live demonstration environment without high-throughput cloud storage backends.
- **Reporting Standard:**
  - `"Satellite-derived vegetation data unavailable"`
  - No synthetic or fabricated NDVI vegetation scores are generated.
- **Classification:** `[REMOTE SENSING UNAVAILABLE]`

---

## 4. Reverse Geocoding & Pan-India Validation
- **Provider:** Bhoomi-Nexus Geo-Resolution Node with OpenStreetMap Nominatim fallback.
- **Territorial Filter:** Strict rejection of any non-Indian coordinate or maritime zone via `window.isPointInIndiaLand()` ray-casting against sovereign borders.
- **Coordinates:** Explicit WGS84 coordinates formatted as `XX.XXXX° N, XX.XXXX° E`.

---

## 5. Summary Table

| Domain | Attribute | Primary Source | Badge | Reporting Standard |
|---|---|---|---|---|
| Admin Hierarchy | State, District, Block, GP | NIC Bharat Maps | `[CADASTRAL]` | Census 2011 Codified |
| Meteorology | Temp, Humidity, Rain, Wind | Open-Meteo ECMWF IFS | `[MODELLED]` | Exact IST Timestamp |
| Soil Moisture | Multi-depth $m^3/m^3$ | ECMWF Land Model | `[REANALYSIS]` | Volumetric $m^3/m^3$ |
| Soil Chemistry | pH, SOC, Clay, Sand | ISRIC SoilGrids 2.0 | `[SPATIAL ESTIMATE]` | 250m Prediction Disclaimer |
| Cadastral Parcel | Khasra, Area, Boundary | State Bhu-Naksha | `[UNAVAILABLE]` | Honest "Unavailable" |
| Vegetation | NDVI, Sentinel-2 | Copernicus Open Access | `[UNAVAILABLE]` | Honest "Unavailable" |
