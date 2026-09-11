"""
BHOOMI-NEXUS: Live Environmental & Soil Telemetry Router
Backed by real Open-Meteo ECMWF/DWD models and ISRIC SoilGrids 2.0.
Zero synthetic random values.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Query, HTTPException

from app.schemas.common import TelemetryResponse
from app.services.env_service import (
    fetch_real_weather_and_soil_telemetry,
    fetch_real_soilgrids_data,
    get_composite_environmental_intelligence,
    validate_coordinates,
)

router = APIRouter(tags=["Telemetry"])


@router.get("/api/telemetry/live", response_model=TelemetryResponse)
async def get_live_telemetry(lat: float = Query(...), lon: float = Query(...)):
    """
    Returns real live atmospheric weather, multi-depth soil moisture, and
    multi-depth soil temperature from Open-Meteo ECMWF/DWD reanalysis models.
    """
    if not validate_coordinates(lat, lon):
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude coordinates")

    telemetry = await fetch_real_weather_and_soil_telemetry(lat, lon)
    if telemetry.get("status") == "unavailable":
        # Honest fallback without inventing fake numbers
        return TelemetryResponse(
            latitude=lat,
            longitude=lon,
            timestamp=datetime.now(timezone.utc).isoformat(),
            surface_temperature_c=None,
            soil_temperature_10cm_c=None,
            soil_moisture_volumetric=None,
            soil_moisture_percentage=None,
            ambient_temperature_c=None,
            relative_humidity_pct=None,
            elevation_m=0.0,
            aridity_status="ENVIRONMENTAL DATA TEMPORARILY UNAVAILABLE",
            cadastral_crop_suitability="Live sensor feed unavailable. Retry or check local IMD station.",
            data_source="Open-Meteo (Unavailable)",
            provenance=telemetry.get("provenance", {}),
            status="unavailable",
        )

    weather = telemetry.get("weather", {})
    soil_moist = telemetry.get("soil_moisture", {})
    soil_temp = telemetry.get("soil_temperature", {})

    st_0_7 = soil_temp.get("layer_0_to_7cm")
    sm_0_7 = soil_moist.get("layer_0_to_7cm")
    amb_temp = weather.get("temperature_2m")
    rel_hum = weather.get("relative_humidity_2m")

    return TelemetryResponse(
        latitude=lat,
        longitude=lon,
        timestamp=telemetry.get("timestamp", datetime.now(timezone.utc).isoformat()),
        surface_temperature_c=st_0_7,
        soil_temperature_10cm_c=st_0_7,
        soil_moisture_volumetric=sm_0_7,
        soil_moisture_percentage=soil_moist.get("percentage_0_to_7cm"),
        ambient_temperature_c=amb_temp,
        relative_humidity_pct=rel_hum,
        precipitation_mm=weather.get("precipitation_mm", 0.0),
        rain_mm=weather.get("rain_mm", 0.0),
        wind_speed_kmh=weather.get("wind_speed_kmh"),
        wind_direction_deg=weather.get("wind_direction_deg"),
        soil_moisture_depths=soil_moist,
        soil_temperature_depths=soil_temp,
        elevation_m=telemetry.get("elevation_m", 0.0),
        aridity_status=soil_moist.get("aridity_condition", "MODERATE"),
        cadastral_crop_suitability=soil_moist.get("crop_suitability", "Standard Arable Soil"),
        data_source="Open-Meteo / ECMWF IFS & Land Reanalysis",
        provenance=telemetry.get("provenance"),
        status="success",
    )


@router.get("/api/v1/env/soil")
async def get_soil_profile(lat: float = Query(...), lon: float = Query(...)):
    """
    Returns real spatial soil predictions from ISRIC SoilGrids 2.0 (250m resolution):
    pH, clay, sand, silt, organic carbon, nitrogen, and cation exchange capacity.
    """
    if not validate_coordinates(lat, lon):
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude coordinates")

    return await fetch_real_soilgrids_data(lat, lon)


@router.get("/api/v1/env/composite")
async def get_composite_environment(lat: float = Query(...), lon: float = Query(...)):
    """
    Unified composite query returning weather, multi-depth soil moisture/temperature,
    and ISRIC SoilGrids spatial profile for the exact clicked coordinates.
    """
    if not validate_coordinates(lat, lon):
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude coordinates")

    return await get_composite_environmental_intelligence(lat, lon)
