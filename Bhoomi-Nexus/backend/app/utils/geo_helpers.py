"""
Geospatial helper utilities.

Coordinate math, GeoJSON validation, and unit conversion helpers
used by the GIS Intelligence Engine.
"""

import math
from typing import Optional


# ── Constants ─────────────────────────────────────────────────────────────

EARTH_RADIUS_M = 6_371_000.0  # Mean Earth radius in meters
SQ_METERS_PER_HECTARE = 10_000.0
SQ_METERS_PER_ACRE = 4_046.8564224


# ── Coordinate Helpers ────────────────────────────────────────────────────

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points in meters.

    Uses the Haversine formula.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def shoelace_area_sq_degrees(coords: list[list[float]]) -> float:
    """
    Compute the signed area of a polygon using the Shoelace formula.
    Coordinates are [lon, lat] pairs.
    Returns absolute area in square degrees.
    """
    n = len(coords)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += coords[i][0] * coords[j][1]
        area -= coords[j][0] * coords[i][1]
    return abs(area) / 2.0


def polygon_area_sq_meters(coords: list[list[float]], reference_lat: Optional[float] = None) -> float:
    """
    Approximate area of a polygon in square meters.

    Uses the Shoelace formula with degree-to-meter scaling at the centroid latitude.
    This is accurate enough for cadastral parcel scales (< 100 km²).

    Args:
        coords: List of [longitude, latitude] pairs.
        reference_lat: Latitude for scaling; defaults to centroid.
    """
    if not coords or len(coords) < 3:
        return 0.0

    if reference_lat is None:
        reference_lat = sum(c[1] for c in coords) / len(coords)

    # Degrees to meters at the reference latitude
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lon = 111_320.0 * math.cos(math.radians(reference_lat))

    # Convert coords to meters relative to first point
    ref_lon, ref_lat = coords[0]
    metric_coords = [
        [
            (c[0] - ref_lon) * meters_per_deg_lon,
            (c[1] - ref_lat) * meters_per_deg_lat,
        ]
        for c in coords
    ]

    return shoelace_area_sq_degrees(metric_coords)


def polygon_perimeter_meters(coords: list[list[float]]) -> float:
    """Calculate the perimeter of a polygon in meters using Haversine."""
    if not coords or len(coords) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coords)):
        j = (i + 1) % len(coords)
        total += haversine_distance(coords[i][1], coords[i][0], coords[j][1], coords[j][0])
    return total


def polygon_centroid(coords: list[list[float]]) -> tuple[float, float]:
    """
    Calculate centroid of a polygon.

    Args:
        coords: List of [longitude, latitude] pairs.

    Returns:
        (latitude, longitude) of the centroid.
    """
    if not coords:
        return (0.0, 0.0)
    avg_lon = sum(c[0] for c in coords) / len(coords)
    avg_lat = sum(c[1] for c in coords) / len(coords)
    return (avg_lat, avg_lon)


def polygon_bounding_box(coords: list[list[float]]) -> dict[str, float]:
    """
    Calculate axis-aligned bounding box.

    Args:
        coords: List of [longitude, latitude] pairs.

    Returns:
        Dict with min_latitude, min_longitude, max_latitude, max_longitude.
    """
    if not coords:
        return {"min_latitude": 0, "min_longitude": 0, "max_latitude": 0, "max_longitude": 0}
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return {
        "min_latitude": min(lats),
        "min_longitude": min(lons),
        "max_latitude": max(lats),
        "max_longitude": max(lons),
    }


# ── Unit Conversion ──────────────────────────────────────────────────────

def sq_meters_to_hectares(area_sqm: float) -> float:
    return area_sqm / SQ_METERS_PER_HECTARE


def sq_meters_to_acres(area_sqm: float) -> float:
    return area_sqm / SQ_METERS_PER_ACRE


# ── GeoJSON Validation ───────────────────────────────────────────────────

def extract_coordinates_from_geojson(geojson: dict) -> list[list[float]]:
    """
    Extract the exterior ring coordinates from a GeoJSON geometry.

    Supports Polygon and MultiPolygon (uses the first polygon).
    Returns list of [longitude, latitude] pairs.
    """
    geom_type = geojson.get("type", "")

    if geom_type == "Polygon":
        rings = geojson.get("coordinates", [])
        if rings and len(rings) > 0:
            return rings[0]  # Exterior ring

    elif geom_type == "MultiPolygon":
        polygons = geojson.get("coordinates", [])
        if polygons and len(polygons) > 0 and len(polygons[0]) > 0:
            return polygons[0][0]  # First polygon, exterior ring

    elif geom_type == "Feature":
        geometry = geojson.get("geometry", {})
        return extract_coordinates_from_geojson(geometry)

    elif geom_type == "FeatureCollection":
        features = geojson.get("features", [])
        if features:
            return extract_coordinates_from_geojson(features[0])

    return []
