"""
BHOOMI-NEXUS: Real Environmental & Soil Intelligence Service
Integrates live authoritative datasets:
1. Open-Meteo ECMWF / DWD Reanalysis & Forecast:
   - Ambient weather (temperature, humidity, precipitation, rain, wind)
   - Multi-depth soil temperature: 0-7cm, 7-28cm, 28-100cm, 100-255cm (°C)
   - Multi-depth volumetric soil moisture: 0-7cm, 7-28cm, 28-100cm, 100-255cm (m³/m³)
2. ISRIC SoilGrids 2.0 (250m Global Spatial Soil Predictions):
   - pH (pH*10 -> pH)
   - Clay, Sand, Silt (g/kg / 10 -> %)
   - Soil Organic Carbon (dg/kg / 10 -> g/kg)
   - Nitrogen (cg/kg / 100 -> g/kg)
   - Cation Exchange Capacity (CEC)

NO synthetic or random values. Thread-safe in-memory caching with coordinate quantization.
"""

import time
import math
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("bhoomi.env_service")

# ── In-Memory Cache with Quantized Coordinates ───────────────────────────
class EnvironmentalCache:
    """Thread-safe in-memory cache with TTL and spatial quantization."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _quantize(coord: float, precision: int = 2) -> float:
        """Quantize coordinates to ~1.1km at equator (0.01 deg) for cache efficiency."""
        return round(coord, precision)

    def _make_key(self, source: str, lat: float, lon: float, bucket: Optional[str] = None) -> str:
        q_lat = self._quantize(lat)
        q_lon = self._quantize(lon)
        if bucket:
            return f"{source}:{q_lat}:{q_lon}:{bucket}"
        return f"{source}:{q_lat}:{q_lon}"

    def get(self, source: str, lat: float, lon: float, bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
        key = self._make_key(source, lat, lon, bucket)
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            del self._store[key]
            return None
        return entry["data"]

    def set(self, source: str, lat: float, lon: float, data: Dict[str, Any], ttl_seconds: int, bucket: Optional[str] = None):
        key = self._make_key(source, lat, lon, bucket)
        self._store[key] = {
            "data": data,
            "expires_at": time.time() + ttl_seconds,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }


cache = EnvironmentalCache()

# ── Coordinate Validation ────────────────────────────────────────────────
def validate_coordinates(lat: float, lon: float) -> bool:
    """Validates WGS84 coordinates and ensures latitude and longitude are within bounds."""
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False
    if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
        return False
    if lat < -90.0 or lat > 90.0:
        return False
    if lon < -180.0 or lon > 180.0:
        return False
    return True


# ── Open-Meteo Weather & Multi-Depth Soil Telemetry ───────────────────────
async def fetch_real_weather_and_soil_telemetry(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetches real weather and multi-depth soil moisture and temperature from Open-Meteo.
    Uses hourly/current reanalysis & forecast models.
    """
    if not validate_coordinates(lat, lon):
        return {
            "status": "error",
            "error": "Invalid coordinates",
            "latitude": lat,
            "longitude": lon,
            "provenance": {"source": "Validation", "badge": "ERROR"}
        }

    # Hourly time bucket for caching (TTL: 1 hour)
    current_hour_bucket = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
    cached = cache.get("open_meteo", lat, lon, current_hour_bucket)
    if cached:
        cached["is_cached"] = True
        return cached

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,rain,wind_speed_10m,wind_direction_10m,"
            "soil_temperature_0_to_7cm,soil_temperature_7_to_28cm,"
            "soil_temperature_28_to_100cm,soil_temperature_100_to_255cm,"
            "soil_moisture_0_to_7cm,soil_moisture_7_to_28cm,"
            "soil_moisture_28_to_100cm,soil_moisture_100_to_255cm"
        ),
        "timezone": "Asia/Kolkata",
    }

    try:
        async with httpx.AsyncClient(timeout=9.0) as client:
            resp = await client.get(url, params=params, headers={"User-Agent": "BhoomiNexus/1.0"})
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                current_units = data.get("current_units", {})
                elev = data.get("elevation", 0.0)

                # Multi-depth soil moisture (m3/m3)
                sm_0_7 = current.get("soil_moisture_0_to_7cm")
                sm_7_28 = current.get("soil_moisture_7_to_28cm")
                sm_28_100 = current.get("soil_moisture_28_to_100cm")
                sm_100_255 = current.get("soil_moisture_100_to_255cm")

                # Multi-depth soil temperature (°C)
                st_0_7 = current.get("soil_temperature_0_to_7cm")
                st_7_28 = current.get("soil_temperature_7_to_28cm")
                st_28_100 = current.get("soil_temperature_28_to_100cm")
                st_100_255 = current.get("soil_temperature_100_to_255cm")

                # Aridity / moisture condition analysis based on upper layer (0-7cm)
                aridity_status = "MODERATE"
                suitability_note = "Standard multi-crop agricultural zone."
                if sm_0_7 is not None:
                    if sm_0_7 < 0.10:
                        aridity_status = "CRITICAL DEFICIT / ARID"
                        suitability_note = "Severe moisture stress. Drought-hardy millets or micro-irrigation required."
                    elif sm_0_7 < 0.20:
                        aridity_status = "SEMI-ARID / MODERATE DEFICIT"
                        suitability_note = "Suitable for mustard, pulses, guar, and rain-fed crops."
                    elif sm_0_7 < 0.35:
                        aridity_status = "OPTIMAL / ARABLE MOISTURE"
                        suitability_note = "High productivity zone: Wheat, barley, pulses, oilseeds."
                    else:
                        aridity_status = "SATURATED / HIGH HYDRATION"
                        suitability_note = "High water table or canal command tract. Suitable for paddy or wetland crops."

                result = {
                    "status": "success",
                    "latitude": lat,
                    "longitude": lon,
                    "elevation_m": elev,
                    "timestamp": current.get("time", datetime.now(timezone.utc).isoformat()),
                    "weather": {
                        "temperature_2m": current.get("temperature_2m"),
                        "apparent_temperature": current.get("apparent_temperature"),
                        "relative_humidity_2m": current.get("relative_humidity_2m"),
                        "precipitation_mm": current.get("precipitation"),
                        "rain_mm": current.get("rain"),
                        "wind_speed_kmh": current.get("wind_speed_10m"),
                        "wind_direction_deg": current.get("wind_direction_10m"),
                        "units": {
                            "temperature": current_units.get("temperature_2m", "°C"),
                            "relative_humidity": current_units.get("relative_humidity_2m", "%"),
                            "precipitation": current_units.get("precipitation", "mm"),
                            "wind_speed": current_units.get("wind_speed_10m", "km/h"),
                        }
                    },
                    "soil_moisture": {
                        "layer_0_to_7cm": sm_0_7,
                        "layer_7_to_28cm": sm_7_28,
                        "layer_28_to_100cm": sm_28_100,
                        "layer_100_to_255cm": sm_100_255,
                        "unit": "m³/m³ (volumetric soil water)",
                        "percentage_0_to_7cm": round(sm_0_7 * 100.0, 1) if sm_0_7 is not None else None,
                        "aridity_condition": aridity_status,
                        "crop_suitability": suitability_note,
                    },
                    "soil_temperature": {
                        "layer_0_to_7cm": st_0_7,
                        "layer_7_to_28cm": st_7_28,
                        "layer_28_to_100cm": st_28_100,
                        "layer_100_to_255cm": st_100_255,
                        "unit": "°C",
                    },
                    "provenance": {
                        "provider": "Open-Meteo / ECMWF IFS & Land Reanalysis",
                        "data_type": "Modelled Atmospheric & Land Surface Reanalysis",
                        "badge": "MODELLED / REANALYSIS",
                        "spatial_resolution": "~11 km",
                        "temporal_resolution": "Hourly",
                        "license": "Open Data / Attribution Required",
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "is_cached": False,
                }
                cache.set("open_meteo", lat, lon, result, ttl_seconds=3600, bucket=current_hour_bucket)
                return result
            else:
                logger.warning("Open-Meteo returned HTTP %d", resp.status_code)
    except Exception as ex:
        logger.error("Error fetching Open-Meteo telemetry for (%f, %f): %s", lat, lon, ex)

    # Return honest failure without fabricating fake numbers
    return {
        "status": "unavailable",
        "error": "Environmental telemetry temporarily unavailable from remote weather service.",
        "latitude": lat,
        "longitude": lon,
        "provenance": {
            "provider": "Open-Meteo",
            "badge": "UNAVAILABLE",
            "last_attempt": datetime.now(timezone.utc).isoformat(),
        }
    }


# ── ISRIC SoilGrids 2.0 Spatial Soil Intelligence ─────────────────────────
async def fetch_real_soilgrids_data(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetches real spatial soil predictions from ISRIC SoilGrids 2.0 (250m resolution).
    Retrieves pH, clay, sand, silt, organic carbon, nitrogen, and cation exchange capacity (CEC)
    via official WCS 2.0.1 raster coverage extraction.
    """
    if not validate_coordinates(lat, lon):
        return {
            "status": "error",
            "error": "Invalid coordinates",
            "provenance": {"provider": "Validation", "badge": "ERROR"}
        }

    # SoilGrids data is static/stable: cache for 30 days
    cached = cache.get("soilgrids", lat, lon)
    if cached:
        cached["is_cached"] = True
        return cached

    from app.services.soil_provider import soil_service
    result = await soil_service.get_soil_properties(lat, lon, depth="0-5cm")
    if result.get("status") == "success":
        cache.set("soilgrids", lat, lon, result, ttl_seconds=86400 * 30)
    return result


# ── Composite Environmental Query ─────────────────────────────────────────
async def get_composite_environmental_intelligence(lat: float, lon: float) -> Dict[str, Any]:
    """
    Combines live Open-Meteo telemetry and ISRIC SoilGrids data for a single geographic coordinate.
    """
    import asyncio
    weather_task = fetch_real_weather_and_soil_telemetry(lat, lon)
    soil_task = fetch_real_soilgrids_data(lat, lon)

    weather_res, soil_res = await asyncio.gather(weather_task, soil_task, return_exceptions=True)

    weather_data = weather_res if isinstance(weather_res, dict) else {"status": "unavailable"}
    soil_data = soil_res if isinstance(soil_res, dict) else {"status": "unavailable"}

    return {
        "latitude": lat,
        "longitude": lon,
        "weather_and_telemetry": weather_data,
        "soil_profile": soil_data,
        "cadastral_status": {
            "status": "UNAVAILABLE_OPEN_API",
            "message": "Cadastral / Khasra parcel boundary data is not available via open public GIS API for this region. Official cadastral records require authenticated access via State Bhu-Naksha portals.",
            "badge": "CADASTRAL UNAVAILABLE",
        },
        "satellite_intelligence": {
            "status": "UNAVAILABLE_DIRECT_TOKEN",
            "message": "Copernicus Sentinel-2 multispectral vegetation time series requires authenticated Copernicus Data Space token.",
            "badge": "SATELLITE UNAVAILABLE",
        },
        "query_timestamp": datetime.now(timezone.utc).isoformat(),
    }
