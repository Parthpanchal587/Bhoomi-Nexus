# SoilGrids 250m Real-Data Integration Architecture

## 1. Overview & Upstream Context
BHOOMI-NEXUS incorporates high-resolution spatial soil intelligence directly from **ISRIC — World Soil Information (SoilGrids 2.0)** at 250-meter spatial resolution.

### Upstream Service Status
- **REST API (`https://rest.isric.org/soilgrids/v2.0/properties/query`)**: ISRIC temporarily paused / disabled the public REST query service (frequent HTTP 503 / 500 timeouts).
- **Official OGC WCS Service (`https://maps.isric.org/mapserv`)**: The official, fully supported Web Coverage Service (WCS 2.0.1) MapServer endpoints are active and operational worldwide.
- **BHOOMI-NEXUS Implementation**: Built on `SoilGridsWCSProvider` as the primary engine with automatic sub-raster pixel extraction and unit conversion.

---

## 2. Supported Soil Properties & Conversions

All properties default to the standard topsoil horizon: **`0–5 cm`**.

| Property | SoilGrids Layer Name | Raw Data Encoding | Conversion Factor | Target Unit | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Soil pH (H₂O)** | `phh2o` | Integer (pH × 10) | `raw / 10.0` | **pH** | Soil reaction in water suspension |
| **Soil Organic Carbon (SOC)** | `soc` | Integer (dg/kg) | `raw / 10.0` | **g/kg** | Organic carbon content of fine earth |
| **Clay Content** | `clay` | Integer (g/kg × 10) | `raw / 10.0` | **%** | Clay fraction (<2 μm) |
| **Sand Content** | `sand` | Integer (g/kg × 10) | `raw / 10.0` | **%** | Sand fraction (>50 μm) |
| **Silt Content** | `silt` | Integer (g/kg × 10) | `raw / 10.0` | **%** | Silt fraction (2–50 μm) |
| **Cation Exchange Capacity** | `cec` | Integer (mmol(c)/kg × 10) | `raw / 10.0` | **mmol(c)/kg** | Soil nutrient retention capacity |
| **Total Nitrogen** | `nitrogen` | Integer (cg/kg) | `raw / 100.0` | **g/kg** | Total nitrogen content |
| **Bulk Density** | `bdod` | Integer (cg/cm³) | `raw / 100.0` | **g/cm³** | Dry bulk density of fine earth fraction |

---

## 3. Data Extraction Pipeline (WCS 2.0.1)

```
MAP POINTER (User Click)
         │
         ▼
Exact WGS84 Coordinate (lat, lon)
         │
         ▼
Bounding Box Buffer: [lon - 0.025, lat - 0.025] to [lon + 0.025, lat + 0.025]
         │
         ▼
WCS 2.0.1 GetCoverage Request (SUBSETTINGCRS=EPSG:4326, OUTPUTCRS=EPSG:4326)
         │
         ▼
GeoTIFF Raster Stream (maps.isric.org MapServer)
         │
         ▼
Pixel Index Transformation:
  px = round((lon - min_lon) / (max_lon - min_lon) * (width - 1))
  py = round((max_lat - lat) / (max_lat - min_lat) * (height - 1))
         │
         ▼
Concentric Sampling Fallback (if exact pixel is 0 / nodata boundary)
         │
         ▼
Unit Conversion & Soil Texture Classification
         │
         ▼
Normalized GeoJSON / REST Response
         │
         ▼
UI Presentation (Card & Map Inspection Marker Popup)
```

---

## 4. Endpoints & API Contracts

### A. Core Soil Endpoint
`GET /api/v1/env/soil?lat={latitude}&lon={longitude}`

**Response Payload:**
```json
{
  "status": "success",
  "latitude": 26.9855,
  "longitude": 75.8587,
  "location": {
    "latitude": 26.9855,
    "longitude": 75.8587
  },
  "source": {
    "provider": "ISRIC SoilGrids",
    "product": "SoilGrids 250m",
    "method": "WCS 2.0.1 Coverage Extraction",
    "dataType": "spatial_model_estimate",
    "resolution": "250m",
    "depth": "0-5cm"
  },
  "soil": {
    "ph": { "value": 7.5, "unit": "pH", "classification": "Neutral / Optimal" },
    "soc": { "value": 14.8, "unit": "g/kg" },
    "clay": { "value": 24.2, "unit": "%" },
    "sand": { "value": 52.7, "unit": "%" },
    "silt": { "value": 23.1, "unit": "%" },
    "cec": { "value": 25.9, "unit": "mmol(c)/kg" },
    "nitrogen": { "value": 1.43, "unit": "g/kg" }
  },
  "summary_0_5cm": {
    "ph": 7.5,
    "soil_organic_carbon_g_per_kg": 14.8,
    "clay_pct": 24.2,
    "sand_pct": 52.7,
    "silt_pct": 23.1,
    "estimated_texture": "Loam / Alluvial"
  },
  "ph_h2o_topsoil": 7.5,
  "soc_g_per_kg_topsoil": 14.8,
  "clay_percent_topsoil": 24.2,
  "sand_percent_topsoil": 52.7,
  "provenance": {
    "provider": "ISRIC - World Soil Information (SoilGrids 2020)",
    "badge": "SPATIAL ESTIMATE (250m)",
    "spatial_resolution": "250 m",
    "depths": ["0-5cm"],
    "license": "CC-BY 4.0",
    "disclaimer": "Spatial soil estimate from official ISRIC WCS service. Not a substitute for laboratory Soil Health Card testing."
  }
}
```

### B. Health Check & Diagnostic Endpoint
`GET /api/v1/env/soil/health`

**Response Payload:**
```json
{
  "status": "ONLINE",
  "provider": "ISRIC SoilGrids 250m",
  "method": "WCS 2.0.1",
  "endpoints": {
    "wcs_service": "https://maps.isric.org/mapserv",
    "rest_service": "https://rest.isric.org/soilgrids/v2.0/properties/query"
  },
  "properties_supported": [
    "phh2o (pH)",
    "soc (Soil Organic Carbon)",
    "clay (%)",
    "sand (%)",
    "silt (%)",
    "cec (mmol(c)/kg)",
    "nitrogen (g/kg)"
  ],
  "depth": "0-5cm (Topsoil standard)"
}
```

---

## 5. Separation from Dynamic Environmental Telemetry

BHOOMI-NEXUS strictly maintains architectural separation between static spatial pedological datasets and dynamic atmospheric telemetry:

1. **ISRIC SoilGrids 2.0 (250m Resolution)**:
   - Evaluated properties: Soil pH, SOC, Clay, Sand, Silt, CEC, Nitrogen.
   - Classification: Spatial model prediction from machine learning pedotransfer functions.
   - Temporal dimension: Static / decadal pedological baseline.
2. **Open-Meteo / ECMWF IFS & DWD Reanalysis**:
   - Evaluated properties: Soil Temperature (0–7cm, 7–28cm, 28–100cm, 100–255cm), Volumetric Soil Moisture (0–7cm, etc.), Ambient Air Temperature, Relative Humidity, Precipitation, Wind Speed/Direction.
   - Classification: Hourly meteorological and land-surface model simulation.
   - Temporal dimension: Real-time dynamic telemetry.

---

## 6. How to Test

Run the automated test suite:
```bash
python -m unittest discover tests
```

Execute multi-location live extraction:
```bash
python scratch/test_live_server_soil.py
```
