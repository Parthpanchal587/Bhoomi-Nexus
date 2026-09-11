"""
BHOOMI-NEXUS: Soil Data Provider Architecture
Implements official SoilGrids WCS 2.0.1 raster data extraction from maps.isric.org.
Supports pH, SOC, Clay, Sand, Silt, CEC, Nitrogen, and Bulk Density.
"""

import asyncio
import io
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import httpx
from PIL import Image

logger = logging.getLogger("bhoomi.soil_provider")


class BaseSoilProvider:
    """Abstract interface for Soil Data Providers."""
    async def get_soil_properties(self, lat: float, lon: float, depth: str = "0-5cm") -> Dict[str, Any]:
        raise NotImplementedError


class SoilGridsWCSProvider(BaseSoilProvider):
    """
    Primary SoilGrids WCS 2.0.1 Provider.
    Extracts high-resolution 250m raster cells from official maps.isric.org MapServer.
    """
    BASE_URL = "https://maps.isric.org/mapserv"
    CONVERSION_FACTORS = {
        "phh2o": (10.0, "pH", "Soil pH (H2O)"),
        "soc": (10.0, "g/kg", "Soil Organic Carbon"),
        "clay": (10.0, "%", "Clay fraction (<2um)"),
        "sand": (10.0, "%", "Sand fraction (>50um)"),
        "silt": (10.0, "%", "Silt fraction (2-50um)"),
        "cec": (10.0, "mmol(c)/kg", "Cation Exchange Capacity"),
        "nitrogen": (100.0, "g/kg", "Total Nitrogen"),
        "bdod": (100.0, "g/cm³", "Bulk Density of Fine Earth")
    }

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "BhoomiNexus-GIS/1.0 (National Land Intelligence Platform; Contact: admin@bhoomi-nexus.gov.in)"
        }

    async def _fetch_property_coverage(
        self, client: httpx.AsyncClient, prop: str, lat: float, lon: float, depth: str, delta: float = 0.025
    ) -> Optional[float]:
        min_lon = lon - delta
        max_lon = lon + delta
        min_lat = lat - delta
        max_lat = lat + delta
        coverage_id = f"{prop}_{depth}_mean"

        url = (
            f"{self.BASE_URL}?map=/map/{prop}.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"
            f"&COVERAGEID={coverage_id}"
            f"&SUBSET=Long({min_lon:.5f},{max_lon:.5f})"
            f"&SUBSET=Lat({min_lat:.5f},{max_lat:.5f})"
            f"&SUBSETTINGCRS=http://www.opengis.net/def/crs/EPSG/0/4326"
            f"&OUTPUTCRS=http://www.opengis.net/def/crs/EPSG/0/4326"
        )

        try:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                logger.warning("WCS query for %s returned status %d", prop, resp.status_code)
                return None

            img = Image.open(io.BytesIO(resp.content))
            w, h = img.size
            if w <= 0 or h <= 0:
                return None

            px = int(round((lon - min_lon) / (max_lon - min_lon) * (w - 1)))
            py = int(round((max_lat - lat) / (max_lat - min_lat) * (h - 1)))
            px = max(0, min(w - 1, px))
            py = max(0, min(h - 1, py))

            raw_val = img.getpixel((px, py))
            if raw_val == 0:
                # Concentric ring scan for nearest valid soil pixel within ~1 km
                for r in range(1, 5):
                    for dx in range(-r, r + 1):
                        for dy in range(-r, r + 1):
                            nx, ny = px + dx, py + dy
                            if 0 <= nx < w and 0 <= ny < h:
                                v = img.getpixel((nx, ny))
                                if v > 0:
                                    raw_val = v
                                    break
                        if raw_val > 0:
                            break
                    if raw_val > 0:
                        break

            if raw_val > 0:
                factor, _, _ = self.CONVERSION_FACTORS.get(prop, (1.0, "", ""))
                return round(raw_val / factor, 2)
            return None
        except Exception as ex:
            logger.warning("Error fetching WCS property %s for (%f, %f): %s", prop, lat, lon, ex)
            return None

    async def get_soil_properties(self, lat: float, lon: float, depth: str = "0-5cm") -> Dict[str, Any]:
        properties = ["phh2o", "soc", "clay", "sand", "silt", "cec", "nitrogen"]
        limits = httpx.Limits(max_keepalive_connections=8, max_connections=12)

        async with httpx.AsyncClient(timeout=self.timeout, limits=limits) as client:
            tasks = [self._fetch_property_coverage(client, p, lat, lon, depth) for p in properties]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        extracted = {}
        for p, res in zip(properties, results):
            if isinstance(res, (int, float)) and res is not None:
                extracted[p] = res
            else:
                extracted[p] = None

        ph_val = extracted.get("phh2o")
        soc_val = extracted.get("soc")
        clay_val = extracted.get("clay")
        sand_val = extracted.get("sand")
        silt_val = extracted.get("silt")

        if all(v is None for v in [ph_val, soc_val, clay_val, sand_val]):
            return {
                "status": "unavailable",
                "reason": "Location is in an unmapped/sealed soil area (urban core, water surface, or rocky outcrop).",
                "latitude": lat,
                "longitude": lon,
                "provenance": {
                    "provider": "ISRIC SoilGrids 2.0 (WCS)",
                    "badge": "UNMAPPED / WATER",
                    "spatial_resolution": "250 m",
                },
            }

        # Soil Texture Classification
        texture_class = "Loam / Mixed Arable"
        if clay_val is not None and sand_val is not None:
            if sand_val > 70:
                texture_class = "Sandy / Arid Soil"
            elif clay_val > 40:
                texture_class = "Clayey Soil"
            elif sand_val > 45 and clay_val < 20:
                texture_class = "Sandy Loam"
            elif 27 <= clay_val <= 40:
                texture_class = "Clay Loam"
            else:
                texture_class = "Loam / Alluvial"

        # pH Classification
        ph_class = "Neutral / Optimal"
        if ph_val is not None:
            if ph_val < 5.5:
                ph_class = "Strongly Acidic"
            elif ph_val < 6.5:
                ph_class = "Moderately Acidic"
            elif ph_val <= 7.5:
                ph_class = "Neutral / Optimal"
            elif ph_val <= 8.5:
                ph_class = "Moderately Alkaline (Calcareous)"
            else:
                ph_class = "Strongly Alkaline (Saline-Sodic)"

        return {
            "status": "success",
            "latitude": lat,
            "longitude": lon,
            "location": {
                "latitude": lat,
                "longitude": lon,
            },
            "source": {
                "provider": "ISRIC SoilGrids",
                "product": "SoilGrids 250m",
                "method": "WCS 2.0.1 Coverage Extraction",
                "dataType": "spatial_model_estimate",
                "resolution": "250m",
                "depth": depth,
            },
            "soil": {
                "ph": {"value": ph_val, "unit": "pH", "classification": ph_class},
                "soc": {"value": soc_val, "unit": "g/kg"},
                "clay": {"value": clay_val, "unit": "%"},
                "sand": {"value": sand_val, "unit": "%"},
                "silt": {"value": silt_val, "unit": "%"},
                "cec": {"value": extracted.get("cec"), "unit": "mmol(c)/kg"},
                "nitrogen": {"value": extracted.get("nitrogen"), "unit": "g/kg"},
            },
            "summary_0_5cm": {
                "ph": ph_val,
                "soil_organic_carbon_g_per_kg": soc_val,
                "clay_pct": clay_val,
                "sand_pct": sand_val,
                "silt_pct": silt_val,
                "estimated_texture": texture_class,
                "ph_classification": ph_class,
            },
            "ph_h2o_topsoil": ph_val,
            "soc_g_per_kg_topsoil": soc_val,
            "clay_percent_topsoil": clay_val,
            "sand_percent_topsoil": sand_val,
            "silt_percent_topsoil": silt_val,
            "ph_classification": ph_class,
            "provenance": {
                "provider": "ISRIC - World Soil Information (SoilGrids 2020)",
                "product": "SoilGrids 250m (WCS Service)",
                "badge": "SPATIAL ESTIMATE (250m)",
                "spatial_resolution": "250 m",
                "depths": [depth],
                "license": "CC-BY 4.0",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "disclaimer": "Spatial soil estimate from official ISRIC WCS service. Not a substitute for laboratory Soil Health Card testing.",
            },
            "is_cached": False,
        }


class SoilGridsRESTProvider(BaseSoilProvider):
    """
    Secondary/Legacy SoilGrids REST API Provider.
    Used as an optional fallback if the REST API is operational.
    """
    REST_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    async def get_soil_properties(self, lat: float, lon: float, depth: str = "0-5cm") -> Dict[str, Any]:
        params = [
            ("lat", str(lat)),
            ("lon", str(lon)),
            ("property", "phh2o"),
            ("property", "clay"),
            ("property", "sand"),
            ("property", "silt"),
            ("property", "soc"),
            ("property", "nitrogen"),
            ("property", "cec"),
            ("depth", depth),
            ("value", "mean"),
        ]
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(self.REST_URL, params=params, headers={"User-Agent": "BhoomiNexus/1.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    layers = data.get("properties", {}).get("layers", [])
                    parsed = {}
                    for layer in layers:
                        name = layer.get("name")
                        dfactor = layer.get("unit_measure", {}).get("d_factor", 1) or 1
                        for d in layer.get("depths", []):
                            if d.get("label") == depth:
                                m = d.get("values", {}).get("mean")
                                if m is not None:
                                    parsed[name] = round(m / dfactor, 2)

                    if parsed:
                        ph = parsed.get("phh2o")
                        return {
                            "status": "success",
                            "latitude": lat,
                            "longitude": lon,
                            "ph_h2o_topsoil": ph,
                            "soc_g_per_kg_topsoil": parsed.get("soc"),
                            "clay_percent_topsoil": parsed.get("clay"),
                            "sand_percent_topsoil": parsed.get("sand"),
                            "silt_percent_topsoil": parsed.get("silt"),
                            "summary_0_5cm": {
                                "ph": ph,
                                "soil_organic_carbon_g_per_kg": parsed.get("soc"),
                                "clay_pct": parsed.get("clay"),
                                "sand_pct": parsed.get("sand"),
                                "silt_pct": parsed.get("silt"),
                            },
                            "provenance": {
                                "provider": "ISRIC SoilGrids 2.0 (REST)",
                                "badge": "SPATIAL ESTIMATE (250m)",
                            },
                        }
        except Exception as e:
            logger.warning("SoilGrids REST provider error: %s", e)
        return {"status": "unavailable"}


class SoilService:
    """
    Orchestrates soil data providers, diagnostic telemetry, and caching.
    """
    def __init__(self):
        self.wcs_provider = SoilGridsWCSProvider()
        self.rest_provider = SoilGridsRESTProvider()
        self.diagnostics = {
            "provider": "ISRIC SoilGrids 250m",
            "primary_method": "WCS 2.0.1",
            "status": "ONLINE",
            "last_successful_query": None,
            "last_queried_coords": None,
            "total_queries": 0,
            "successful_queries": 0,
        }

    async def get_soil_properties(self, lat: float, lon: float, depth: str = "0-5cm") -> Dict[str, Any]:
        self.diagnostics["total_queries"] += 1
        self.diagnostics["last_queried_coords"] = {"lat": lat, "lon": lon}

        # 1. Primary: Try SoilGrids WCS
        res = await self.wcs_provider.get_soil_properties(lat, lon, depth)
        if res.get("status") == "success":
            self.diagnostics["successful_queries"] += 1
            self.diagnostics["status"] = "ONLINE"
            self.diagnostics["last_successful_query"] = datetime.now(timezone.utc).isoformat()
            return res

        # 2. Secondary: If WCS was unmapped or failed, try REST
        rest_res = await self.rest_provider.get_soil_properties(lat, lon, depth)
        if rest_res.get("status") == "success":
            self.diagnostics["successful_queries"] += 1
            self.diagnostics["status"] = "DEGRADED (REST_FALLBACK)"
            self.diagnostics["last_successful_query"] = datetime.now(timezone.utc).isoformat()
            return rest_res

        # 3. If neither provider has data for this pixel
        if res.get("status") == "unavailable":
            return res

        self.diagnostics["status"] = "UNAVAILABLE"
        return {
            "status": "unavailable",
            "error": "ISRIC SoilGrids spatial soil data temporarily unavailable.",
            "latitude": lat,
            "longitude": lon,
            "provenance": {
                "provider": "ISRIC SoilGrids",
                "badge": "UNAVAILABLE",
                "last_attempt": datetime.now(timezone.utc).isoformat(),
            },
        }

    def get_health_status(self) -> Dict[str, Any]:
        return {
            "status": self.diagnostics["status"],
            "provider": self.diagnostics["provider"],
            "method": self.diagnostics["primary_method"],
            "endpoints": {
                "wcs_service": "https://maps.isric.org/mapserv",
                "rest_service": "https://rest.isric.org/soilgrids/v2.0/properties/query",
            },
            "metrics": {
                "total_queries": self.diagnostics["total_queries"],
                "successful_queries": self.diagnostics["successful_queries"],
                "last_successful_query": self.diagnostics["last_successful_query"],
                "last_queried_coords": self.diagnostics["last_queried_coords"],
            },
            "properties_supported": [
                "phh2o (pH)",
                "soc (Soil Organic Carbon)",
                "clay (%)",
                "sand (%)",
                "silt (%)",
                "cec (mmol(c)/kg)",
                "nitrogen (g/kg)",
            ],
            "depth": "0-5cm (Topsoil standard)",
        }


# Global SoilService instance
soil_service = SoilService()
