"""
Pydantic schemas for the GIS Intelligence Engine.

Endpoint served:
  POST /api/v1/gis/analyze
"""

from typing import Optional
from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────────

class GISAnalyzeRequest(BaseModel):
    """
    Accepts a land parcel in one of three forms:
    1. GeoJSON polygon geometry
    2. List of coordinate pairs [[lon, lat], ...]
    3. A named survey plot ID for lookup
    """
    geojson: Optional[dict] = Field(
        None,
        description="GeoJSON geometry object (Polygon or MultiPolygon)"
    )
    coordinates: Optional[list[list[float]]] = Field(
        None,
        description="List of [longitude, latitude] pairs forming the parcel boundary"
    )
    survey_plot_id: Optional[str] = Field(
        None,
        description="Named survey plot identifier for pre-registered parcels"
    )
    check_proximity: bool = Field(
        default=True,
        description="Whether to check proximity against flood plains, forest zones, and easements"
    )


# ── Response components ──────────────────────────────────────────────────

class ParcelMetrics(BaseModel):
    """Computed geometric metrics for the land parcel."""
    area_sq_meters: float
    area_hectares: float
    area_acres: float
    perimeter_meters: float


class Centroid(BaseModel):
    latitude: float
    longitude: float


class BoundingBox(BaseModel):
    min_latitude: float
    min_longitude: float
    max_latitude: float
    max_longitude: float


class ProximityAlert(BaseModel):
    """Alert when the parcel is near a restricted or hazard zone."""
    zone_type: str = Field(..., description="e.g., 'Flood Plain', 'Forest Buffer', 'Infrastructure Easement'")
    zone_name: str
    distance_meters: float
    severity: str = Field(..., description="SAFE / CAUTION / WARNING / CRITICAL")
    regulation_reference: Optional[str] = None
    advisory: str


class GISAnalyzeResponse(BaseModel):
    """Full geospatial analysis result for a land parcel."""
    status: str = "ANALYSIS_COMPLETE"
    parcel_metrics: ParcelMetrics
    centroid: Centroid
    bounding_box: BoundingBox
    coordinate_system: str = "EPSG:4326 (WGS 84)"
    proximity_alerts: list[ProximityAlert]
    total_alerts: int
    risk_summary: str
    survey_plot_id: Optional[str] = None
