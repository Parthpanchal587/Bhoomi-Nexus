"""
Live telemetry endpoint (Open-Meteo soil & weather data).
Extracted from original main.py — logic identical.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Query

import httpx

from app.config import settings
from app.schemas.common import TelemetryResponse

router = APIRouter(tags=["Telemetry"])


@router.get("/api/telemetry/live", response_model=TelemetryResponse)
async def get_live_telemetry(lat: float = Query(...), lon: float = Query(...)):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,surface_temperature,soil_temperature_0_to_10cm,soil_moisture_0_to_1cm",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(settings.OPEN_METEO_BASE_URL, params=params)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                surface_temp = float(current.get("surface_temperature", 28.0))
                soil_temp = float(current.get("soil_temperature_0_to_10cm", 27.5))
                soil_moisture = float(current.get("soil_moisture_0_to_1cm", 0.22))
                ambient_temp = float(current.get("temperature_2m", 29.0))
                rel_humidity = float(current.get("relative_humidity_2m", 65.0))
                elevation = float(data.get("elevation", 350.0))
                time_iso = current.get("time", datetime.now(timezone.utc).isoformat())
                moisture_pct = round(soil_moisture * 100.0, 1)

                if soil_moisture < 0.12:
                    aridity = "ARID / CRITICAL SOIL MOISTURE DEFICIT"
                    suitability = "Drought-Hardy Millets, Desert Shelterbelts, Sub-surface Drip Required"
                elif soil_moisture < 0.22:
                    aridity = "SEMI-ARID / MODERATE MOISTURE"
                    suitability = "Suitable for Mustard, Pulses, Cluster Bean (Guar)"
                elif soil_moisture < 0.38:
                    aridity = "OPTIMAL / ARABLE LOAM"
                    suitability = "High Productivity Dual-Crop Zone: Wheat, Barley, Mustard"
                else:
                    aridity = "SATURATED / WETLAND TRACT"
                    suitability = "Canal Command Hydrated Zone"

                return TelemetryResponse(
                    latitude=lat,
                    longitude=lon,
                    timestamp=time_iso,
                    surface_temperature_c=surface_temp,
                    soil_temperature_10cm_c=soil_temp,
                    soil_moisture_volumetric=soil_moisture,
                    soil_moisture_percentage=moisture_pct,
                    ambient_temperature_c=ambient_temp,
                    relative_humidity_pct=rel_humidity,
                    elevation_m=elevation,
                    aridity_status=aridity,
                    cadastral_crop_suitability=suitability,
                    data_source="Open-Meteo Land Surface Telemetry",
                )
    except Exception:
        pass

    moisture = 0.245
    return TelemetryResponse(
        latitude=lat,
        longitude=lon,
        timestamp=datetime.now(timezone.utc).isoformat(),
        surface_temperature_c=29.4,
        soil_temperature_10cm_c=28.1,
        soil_moisture_volumetric=moisture,
        soil_moisture_percentage=round(moisture * 100.0, 1),
        ambient_temperature_c=30.2,
        relative_humidity_pct=60.0,
        elevation_m=380.0,
        aridity_status="SEMI-ARID / MODERATE MOISTURE",
        cadastral_crop_suitability="Arable Loam: Dual-crop Mustard & Pulses",
        data_source="Bhoomi Synthetic Cadastral Telemetry (Offline Fallback)",
    )
