"""
GIS Intelligence Engine Router.

Endpoint:
  POST /api/v1/gis/analyze — Geospatial parcel analysis
"""

from fastapi import APIRouter

from app.schemas.gis import GISAnalyzeRequest, GISAnalyzeResponse
from app.services.gis_engine import analyze_parcel

router = APIRouter(prefix="/api/v1/gis", tags=["GIS Intelligence (v1)"])


@router.post("/analyze", response_model=GISAnalyzeResponse)
def gis_analyze_endpoint(req: GISAnalyzeRequest):
    """
    Analyze a land parcel's geospatial properties.

    Accepts input as:
    - GeoJSON polygon geometry
    - List of [longitude, latitude] coordinate pairs
    - A pre-registered survey plot ID

    Returns:
    - Area (sq meters, hectares, acres), perimeter
    - Centroid coordinates and bounding box
    - Proximity alerts against flood plains, forest buffer zones,
      and infrastructure easements
    """
    return analyze_parcel(req)
