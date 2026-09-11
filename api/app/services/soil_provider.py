"""
BHOOMI-NEXUS: Soil Data Provider Architecture
Implements official SoilGrids WCS 2.0.1 raster data extraction from maps.isric.org.
Supports topsoil (0-5cm) median (Q0.5) extractions:
pH (H2O), Soil Organic Carbon (SOC), Clay, Sand, Silt, CEC, and Nitrogen.
Enforces coordinate precision, normalized contract, explicit NoData reporting,
and development debug logging.
"""

import asyncio
import io
import logging
import math
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import httpx
from PIL import Image

logger = logging.getLogger("bhoomi.soil_provider")


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lon coordinates."""
    r = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


class BaseSoilProvider:
    """Abstract interface for Soil Data Providers."""
    async def get_soil_properties(self, lat: float, lon: float, depth: str = "0-5cm", request_id: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError


class SoilGridsWCSProvider(BaseSoilProvider):
    """
    Primary SoilGrids WCS 2.0.1 Provider.
    Extracts high-resolution 250m raster cells from official maps.isric.org MapServer.
    Uses median (Q0.5) coverages with fallback to mean.
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

    def __init__(self, timeout: float = 14.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "BhoomiNexus-GIS/1.0 (National Land Intelligence Platform; Contact: admin@bhoomi-nexus.gov.in)"
        }

    async def _fetch_property_coverage(
        self, client: httpx.AsyncClient, prop: str, lat: float, lon: float, depth: str, delta: float = 0.025
    ) -> Dict[str, Any]:
        """
        Queries official WCS 2.0.1 coverage for a single soil property.
        Logs development debug metrics matching Section 7 requirements.
        Returns dict with raw pixel, converted value, and sampled coordinates.
        """
        min_lon = lon - delta
        max_lon = lon + delta
        min_lat = lat - delta
        max_lat = lat + delta
        coverage_id = f"{prop}_{depth}_Q0.5"

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
            # If Q0.5 returned 404/500, attempt mean coverage fallback
            if resp.status_code != 200:
                fallback_cov = f"{prop}_{depth}_mean"
                fallback_url = (
                    f"{self.BASE_URL}?map=/map/{prop}.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"
                    f"&COVERAGEID={fallback_cov}"
                    f"&SUBSET=Long({min_lon:.5f},{max_lon:.5f})"
                    f"&SUBSET=Lat({min_lat:.5f},{max_lat:.5f})"
                    f"&SUBSETTINGCRS=http://www.opengis.net/def/crs/EPSG/0/4326"
                    f"&OUTPUTCRS=http://www.opengis.net/def/crs/EPSG/0/4326"
                )
                resp = await client.get(fallback_url, headers=self.headers)
                if resp.status_code == 200:
                    coverage_id = fallback_cov
                    url = fallback_url

            if resp.status_code != 200:
                logger.warning("[SOILGRIDS DEBUG] WCS query for %s returned status %d", prop, resp.status_code)
                return {
                    "property": prop,
                    "coverage_id": coverage_id,
                    "http_status": resp.status_code,
                    "raw_pixel": None,
                    "converted_value": None,
                    "is_no_data": True,
                    "distance_m": None
                }

            content = resp.content
            ctype = resp.headers.get("Content-Type", "image/tiff")
            img = Image.open(io.BytesIO(content))
            w, h = img.size
            if w <= 0 or h <= 0:
                return {
                    "property": prop,
                    "coverage_id": coverage_id,
                    "http_status": resp.status_code,
                    "raw_pixel": None,
                    "converted_value": None,
                    "is_no_data": True,
                    "distance_m": None
                }

            px = int(round((lon - min_lon) / (max_lon - min_lon) * (w - 1)))
            py = int(round((max_lat - lat) / (max_lat - min_lat) * (h - 1)))
            px = max(0, min(w - 1, px))
            py = max(0, min(h - 1, py))

            center_val = img.getpixel((px, py))
            raw_val = center_val
            sampled_lat, sampled_lon = lat, lon
            distance_m = 0.0
            is_nearest = False

            if raw_val == 0:
                # Target coordinate is water or urban sealed surface.
                # Find nearest valid soil pixel in retrieved raster and record exact distance.
                min_dist = float("inf")
                found_val = None
                best_coord = (lat, lon)
                for y in range(h):
                    for x in range(w):
                        v = img.getpixel((x, y))
                        if v > 0:
                            c_lon = min_lon + (x / (w - 1)) * (max_lon - min_lon)
                            c_lat = max_lat - (y / (h - 1)) * (max_lat - min_lat)
                            dist = haversine_distance_meters(lat, lon, c_lat, c_lon)
                            if dist < min_dist:
                                min_dist = dist
                                found_val = v
                                best_coord = (c_lat, c_lon)

                if found_val is not None and found_val > 0:
                    raw_val = found_val
                    distance_m = min_dist
                    sampled_lat, sampled_lon = best_coord
                    is_nearest = True

            factor, unit, _ = self.CONVERSION_FACTORS.get(prop, (10.0, "", ""))
            converted_val = round(raw_val / factor, 2) if (raw_val and raw_val > 0) else None

            # [SOILGRIDS DEBUG] Log required development telemetry
            if prop in ["phh2o", "soc", "clay", "sand"]:
                print(
                    f"\n[SOILGRIDS DEBUG]\n"
                    f"Requested latitude: {lat:.5f}\n"
                    f"Requested longitude: {lon:.5f}\n"
                    f"Input CRS: EPSG:4326\n"
                    f"WCS CRS: EPSG:4326\n"
                    f"Property: {prop}\n"
                    f"Depth: {depth}\n"
                    f"Quantile: Q0.5\n"
                    f"WCS URL: {url}\n"
                    f"HTTP status: {resp.status_code}\n"
                    f"Content-Type: {ctype}\n"
                    f"Response size: {len(content)} bytes\n"
                    f"Raster dimensions: {w}x{h}\n"
                    f"NoData value: 0\n"
                    f"Raw pixel: {raw_val}\n"
                    f"Converted value: {converted_val} {unit}\n"
                    f"Sampled Distance: {distance_m:.1f} m\n"
                )

            return {
                "property": prop,
                "coverage_id": coverage_id,
                "http_status": resp.status_code,
                "raw_pixel": raw_val if raw_val > 0 else 0,
                "converted_value": converted_val,
                "unit": unit,
                "is_no_data": converted_val is None,
                "sampled_lat": sampled_lat,
                "sampled_lon": sampled_lon,
                "distance_m": distance_m,
                "is_nearest": is_nearest,
            }

        except Exception as ex:
            logger.warning("[SOILGRIDS DEBUG] Error fetching WCS property %s: %s", prop, ex)
            return {
                "property": prop,
                "coverage_id": coverage_id,
                "http_status": 0,
                "raw_pixel": None,
                "converted_value": None,
                "is_no_data": True,
                "distance_m": None,
                "error": str(ex)
            }

    async def get_soil_properties(self, lat: float, lon: float, depth: str = "0-5cm", request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Full multi-property SoilGrids extraction returning the normalized contract.
        """
        properties = ["phh2o", "soc", "clay", "sand", "silt", "cec", "nitrogen"]
        limits = httpx.Limits(max_keepalive_connections=8, max_connections=12)

        async with httpx.AsyncClient(timeout=self.timeout, limits=limits) as client:
            tasks = [self._fetch_property_coverage(client, p, lat, lon, depth) for p in properties]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        extracted: Dict[str, Dict[str, Any]] = {}
        for p, res in zip(properties, results):
            if isinstance(res, dict):
                extracted[p] = res
            else:
                extracted[p] = {
                    "property": p,
                    "converted_value": None,
                    "is_no_data": True,
                    "raw_pixel": None,
                    "distance_m": 0.0
                }

        ph_res = extracted.get("phh2o", {})
        soc_res = extracted.get("soc", {})
        clay_res = extracted.get("clay", {})
        sand_res = extracted.get("sand", {})
        silt_res = extracted.get("silt", {})
        cec_res = extracted.get("cec", {})
        nitrogen_res = extracted.get("nitrogen", {})

        ph_val = ph_res.get("converted_value")
        soc_val = soc_res.get("converted_value")
        clay_val = clay_res.get("converted_value")
        sand_val = sand_res.get("converted_value")
        silt_val = silt_res.get("converted_value")

        # Determine sampling metadata from primary property (phh2o or first available)
        primary_res = ph_res if ph_res.get("converted_value") is not None else soc_res
        sampled_lat = primary_res.get("sampled_lat", lat)
        sampled_lon = primary_res.get("sampled_lon", lon)
        sampling_distance = primary_res.get("distance_m", 0.0) or 0.0
        is_nearest = primary_res.get("is_nearest", False)

        all_none = all(v is None for v in [ph_val, soc_val, clay_val, sand_val])
        if all_none:
            return {
                "location": {
                    "latitude": lat,
                    "longitude": lon,
                    "sampledLatitude": lat,
                    "sampledLongitude": lon,
                    "distanceMeters": 0.0,
                    "isNearestValidPixel": False
                },
                "source": {
                    "provider": "ISRIC SoilGrids",
                    "version": "SoilGrids 2.0",
                    "resolution": "250m",
                    "depth": depth,
                    "dataType": "spatial_model_estimate"
                },
                "properties": {
                    "ph": {"value": None, "unit": "pH", "status": "no_data", "reason": "SoilGrids pixel contains NoData"},
                    "soc": {"value": None, "unit": "g/kg", "status": "no_data", "reason": "SoilGrids pixel contains NoData"},
                    "clay": {"value": None, "unit": "%", "status": "no_data", "reason": "SoilGrids pixel contains NoData"},
                    "sand": {"value": None, "unit": "%", "status": "no_data", "reason": "SoilGrids pixel contains NoData"}
                },
                "retrievedAt": datetime.now(timezone.utc).isoformat(),
                "status": "no_data",
                "reason": "SoilGrids pixel contains NoData (unmodeled water or sealed bedrock surface)",
                "requestId": request_id or f"soil-{int(datetime.now().timestamp()*1000)}",
                # Backward-compatibility aliases
                "ph_h2o_topsoil": None,
                "soc_g_per_kg_topsoil": None,
                "clay_percent_topsoil": None,
                "sand_percent_topsoil": None,
                "summary_0_5cm": None,
                "provenance": {
                    "provider": "ISRIC SoilGrids 2.0 (WCS)",
                    "badge": "UNMAPPED / NODATA",
                    "spatial_resolution": "250 m"
                }
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
                ph_class = "Moderately Alkaline"
            else:
                ph_class = "Strongly Alkaline"

        retrieved_iso = datetime.now(timezone.utc).isoformat()
        req_id = request_id or f"soil-{int(datetime.now().timestamp()*1000)}"

        return {
            # ── SECTION 12 NORMALIZED CONTRACT ──────────────────────────
            "location": {
                "latitude": lat,
                "longitude": lon,
                "sampledLatitude": round(sampled_lat, 5),
                "sampledLongitude": round(sampled_lon, 5),
                "distanceMeters": round(sampling_distance, 1),
                "isNearestValidPixel": bool(is_nearest and sampling_distance > 0)
            },
            "source": {
                "provider": "ISRIC SoilGrids",
                "version": "SoilGrids 2.0",
                "resolution": "250m",
                "depth": depth,
                "dataType": "spatial_model_estimate"
            },
            "properties": {
                "ph": {
                    "value": ph_val,
                    "unit": "pH",
                    "status": "success" if ph_val is not None else "no_data",
                    "classification": ph_class
                },
                "soc": {
                    "value": soc_val,
                    "unit": "g/kg",
                    "status": "success" if soc_val is not None else "no_data"
                },
                "clay": {
                    "value": clay_val,
                    "unit": "%",
                    "status": "success" if clay_val is not None else "no_data"
                },
                "sand": {
                    "value": sand_val,
                    "unit": "%",
                    "status": "success" if sand_val is not None else "no_data"
                }
            },
            "retrievedAt": retrieved_iso,
            "requestId": req_id,
            "status": "success",

            # ── BACKWARD-COMPATIBLE FRONTEND ALIASES ────────────────────
            "latitude": lat,
            "longitude": lon,
            "ph_h2o_topsoil": ph_val,
            "soc_g_per_kg_topsoil": soc_val,
            "clay_percent_topsoil": clay_val,
            "sand_percent_topsoil": sand_val,
            "silt_percent_topsoil": silt_val,
            "ph_classification": ph_class,
            "soil": {
                "ph": {"value": ph_val, "unit": "pH", "classification": ph_class},
                "soc": {"value": soc_val, "unit": "g/kg"},
                "clay": {"value": clay_val, "unit": "%"},
                "sand": {"value": sand_val, "unit": "%"},
                "silt": {"value": silt_val, "unit": "%"},
                "cec": {"value": cec_res.get("converted_value"), "unit": "mmol(c)/kg"},
                "nitrogen": {"value": nitrogen_res.get("converted_value"), "unit": "g/kg"}
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
            "provenance": {
                "provider": "ISRIC - World Soil Information (SoilGrids 2020)",
                "product": "SoilGrids 250m (WCS Service)",
                "badge": "SPATIAL ESTIMATE (250m)",
                "spatial_resolution": "250 m",
                "depths": [depth],
                "license": "CC-BY 4.0",
                "retrieved_at": retrieved_iso,
                "disclaimer": "Spatial soil estimate from official ISRIC WCS service. Not a substitute for laboratory Soil Health Card testing."
            },
            "is_cached": False,
            "raw_extracted": {
                "phh2o": ph_res.get("raw_pixel"),
                "soc": soc_res.get("raw_pixel"),
                "clay": clay_res.get("raw_pixel"),
                "sand": sand_res.get("raw_pixel")
            }
        }


class SoilGridsRESTProvider(BaseSoilProvider):
    """
    Secondary/Legacy SoilGrids REST API Provider.
    Used only as an optional auxiliary path if WCS is degraded.
    """
    REST_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    async def get_soil_properties(self, lat: float, lon: float, depth: str = "0-5cm", request_id: Optional[str] = None) -> Dict[str, Any]:
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
                        soc = parsed.get("soc")
                        clay = parsed.get("clay")
                        sand = parsed.get("sand")
                        return {
                            "location": {"latitude": lat, "longitude": lon, "sampledLatitude": lat, "sampledLongitude": lon, "distanceMeters": 0.0, "isNearestValidPixel": False},
                            "source": {"provider": "ISRIC SoilGrids", "version": "SoilGrids 2.0", "resolution": "250m", "depth": depth, "dataType": "spatial_model_estimate"},
                            "properties": {
                                "ph": {"value": ph, "unit": "pH", "status": "success"},
                                "soc": {"value": soc, "unit": "g/kg", "status": "success"},
                                "clay": {"value": clay, "unit": "%", "status": "success"},
                                "sand": {"value": sand, "unit": "%", "status": "success"}
                            },
                            "status": "success",
                            "latitude": lat,
                            "longitude": lon,
                            "ph_h2o_topsoil": ph,
                            "soc_g_per_kg_topsoil": soc,
                            "clay_percent_topsoil": clay,
                            "sand_percent_topsoil": sand,
                            "summary_0_5cm": {"ph": ph, "soil_organic_carbon_g_per_kg": soc, "clay_pct": clay, "sand_pct": sand},
                            "provenance": {"provider": "ISRIC SoilGrids 2.0 (REST)", "badge": "SPATIAL ESTIMATE (250m)"}
                        }
        except Exception as e:
            logger.warning("SoilGrids REST provider error: %s", e)
        return {"status": "unavailable"}


class SoilService:
    """
    Orchestrates SoilGrids WCS extraction, diagnostics, and health monitoring.
    """
    def __init__(self):
        self.wcs_provider = SoilGridsWCSProvider()
        self.rest_provider = SoilGridsRESTProvider()
        self.diagnostics = {
            "provider": "ISRIC SoilGrids",
            "primary_method": "WCS",
            "status": "healthy",
            "last_successful_query": None,
            "last_error": None,
            "total_queries": 0,
            "successful_queries": 0,
        }

    async def get_soil_properties(self, lat: float, lon: float, depth: str = "0-5cm", request_id: Optional[str] = None) -> Dict[str, Any]:
        self.diagnostics["total_queries"] += 1

        try:
            # 1. Primary: SoilGrids WCS
            res = await self.wcs_provider.get_soil_properties(lat, lon, depth, request_id)
            if res.get("status") == "success":
                self.diagnostics["successful_queries"] += 1
                self.diagnostics["status"] = "healthy"
                self.diagnostics["last_successful_query"] = datetime.now(timezone.utc).isoformat()
                self.diagnostics["last_error"] = None
                return res

            # 2. Secondary: REST fallback if WCS reported no data or unavailable
            if res.get("status") in ["no_data", "unavailable"]:
                rest_res = await self.rest_provider.get_soil_properties(lat, lon, depth, request_id)
                if rest_res.get("status") == "success":
                    self.diagnostics["successful_queries"] += 1
                    self.diagnostics["last_successful_query"] = datetime.now(timezone.utc).isoformat()
                    return rest_res
                return res

        except Exception as ex:
            logger.error("SoilService query error for (%f, %f): %s", lat, lon, ex)
            self.diagnostics["last_error"] = str(ex)
            self.diagnostics["status"] = "degraded"

        return {
            "location": {"latitude": lat, "longitude": lon},
            "source": {"provider": "ISRIC SoilGrids", "version": "SoilGrids 2.0", "resolution": "250m", "depth": depth, "dataType": "spatial_model_estimate"},
            "properties": {
                "ph": {"value": None, "unit": "pH", "status": "unavailable"},
                "soc": {"value": None, "unit": "g/kg", "status": "unavailable"},
                "clay": {"value": None, "unit": "%", "status": "unavailable"},
                "sand": {"value": None, "unit": "%", "status": "unavailable"}
            },
            "status": "unavailable",
            "reason": self.diagnostics.get("last_error") or "ISRIC SoilGrids WCS unavailable",
            "ph_h2o_topsoil": None,
            "soc_g_per_kg_topsoil": None,
            "clay_percent_topsoil": None,
            "sand_percent_topsoil": None
        }

    def get_health_status(self) -> Dict[str, Any]:
        """
        Implements internal health check matching Section 18.
        """
        is_healthy = self.diagnostics["status"] == "healthy" or self.diagnostics["successful_queries"] > 0
        return {
            "provider": "ISRIC SoilGrids",
            "method": "WCS",
            "status": "healthy" if is_healthy else "degraded",
            "lastSuccessfulQuery": self.diagnostics["last_successful_query"],
            "lastError": self.diagnostics["last_error"]
        }

    async def get_diagnostic_info(self, lat: float, lon: float, depth: str = "0-5cm") -> Dict[str, Any]:
        """
        Implements development diagnostic endpoint matching Section 19.
        """
        res = await self.wcs_provider.get_soil_properties(lat, lon, depth)
        raw_vals = res.get("raw_extracted", {})
        props = res.get("properties", {})
        converted = {k: v.get("value") for k, v in props.items()}

        return {
            "requestedCoordinate": {"latitude": lat, "longitude": lon},
            "transformedCoordinate": {"latitude": lat, "longitude": lon, "crs": "EPSG:4326"},
            "wcsCoverageIds": [
                f"phh2o_{depth}_Q0.5",
                f"soc_{depth}_Q0.5",
                f"clay_{depth}_Q0.5",
                f"sand_{depth}_Q0.5"
            ],
            "httpStatus": 200 if res.get("status") == "success" else 503,
            "rawExtractedValues": raw_vals,
            "convertedValues": converted,
            "noDataStatus": res.get("status") == "no_data",
            "source": "ISRIC SoilGrids 2.0 (WCS 2.0.1)",
            "sampledCoordinate": {
                "latitude": res.get("location", {}).get("sampledLatitude"),
                "longitude": res.get("location", {}).get("sampledLongitude"),
                "distanceMeters": res.get("location", {}).get("distanceMeters"),
                "isNearestValidPixel": res.get("location", {}).get("isNearestValidPixel")
            },
            "retrievedAt": res.get("retrievedAt")
        }


# Global SoilService instance
soil_service = SoilService()
