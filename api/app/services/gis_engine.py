"""
GIS Intelligence Engine Service.

Performs geospatial analysis on land parcels:
- Calculates area, perimeter, centroid, bounding box
- Checks spatial proximity against flood plains, forest buffer zones,
  and infrastructure easements
"""

from typing import Optional

from app.schemas.gis import (
    GISAnalyzeRequest,
    GISAnalyzeResponse,
    ParcelMetrics,
    Centroid,
    BoundingBox,
    ProximityAlert,
)
from app.utils.geo_helpers import (
    polygon_area_sq_meters,
    polygon_perimeter_meters,
    polygon_centroid,
    polygon_bounding_box,
    sq_meters_to_hectares,
    sq_meters_to_acres,
    extract_coordinates_from_geojson,
    haversine_distance,
)


# ── Seeded Hazard / Restriction Zones ─────────────────────────────────────
# In production, these would come from ISRO / Survey of India / state GIS feeds.

HAZARD_ZONES = [
    {
        "type": "Flood Plain",
        "name": "Chambal River Flood Plain (Zone A)",
        "centroid_lat": 25.45,
        "centroid_lon": 76.12,
        "radius_m": 8000.0,
        "regulation": "National Disaster Management Authority (NDMA) Flood Zone Regulation 2019",
        "advisory": "Construction within flood plain Zone A requires NDMA clearance and elevated foundation design.",
    },
    {
        "type": "Flood Plain",
        "name": "Luni River Basin Seasonal Flood Zone",
        "centroid_lat": 25.78,
        "centroid_lon": 72.34,
        "radius_m": 5000.0,
        "regulation": "Rajasthan Water Resources Department Notification 2023",
        "advisory": "Seasonal flooding risk during monsoon. Agricultural use permitted; residential development restricted.",
    },
    {
        "type": "Forest Buffer",
        "name": "Sariska Tiger Reserve Buffer Zone",
        "centroid_lat": 27.32,
        "centroid_lon": 76.39,
        "radius_m": 15000.0,
        "regulation": "Wildlife Protection Act 1972, Section 18 & Forest Conservation Act 1980",
        "advisory": "No commercial/industrial development within buffer zone. Eco-tourism permitted with NBWL clearance.",
    },
    {
        "type": "Forest Buffer",
        "name": "Desert National Park Eco-Sensitive Zone",
        "centroid_lat": 26.80,
        "centroid_lon": 70.60,
        "radius_m": 20000.0,
        "regulation": "MoEFCC Eco-Sensitive Zone Notification 2018",
        "advisory": "Restricted development zone. Mining, quarrying, and major construction activities prohibited.",
    },
    {
        "type": "Forest Buffer",
        "name": "Ranthambore National Park Buffer",
        "centroid_lat": 26.02,
        "centroid_lon": 76.50,
        "radius_m": 12000.0,
        "regulation": "National Tiger Conservation Authority (NTCA) Guidelines",
        "advisory": "Tiger corridor protection zone. Land use change requires NTCA and state forest department approval.",
    },
    {
        "type": "Infrastructure Easement",
        "name": "NH-48 National Highway Right of Way",
        "centroid_lat": 26.85,
        "centroid_lon": 75.78,
        "radius_m": 500.0,
        "regulation": "National Highways Act 1956, Section 3A — Right of Way",
        "advisory": "No permanent structures within 60m of National Highway centerline. Temporary structures require NHAI NOC.",
    },
    {
        "type": "Infrastructure Easement",
        "name": "Delhi–Mumbai Industrial Corridor (DMIC) Alignment",
        "centroid_lat": 27.10,
        "centroid_lon": 76.20,
        "radius_m": 3000.0,
        "regulation": "DMIC Development Corporation Acquisition Notification",
        "advisory": "Land within DMIC corridor may be subject to acquisition. Check latest notification before investment.",
    },
    {
        "type": "Infrastructure Easement",
        "name": "220kV High Tension Power Line Corridor",
        "centroid_lat": 26.92,
        "centroid_lon": 75.80,
        "radius_m": 200.0,
        "regulation": "Central Electricity Authority (CEA) Safety Regulations 2010",
        "advisory": "No habitable structures within 18m horizontal clearance of 220kV lines. Safety compliance mandatory.",
    },
]


# ── Sample Survey Plots ──────────────────────────────────────────────────

SAMPLE_SURVEY_PLOTS: dict[str, list[list[float]]] = {
    "KHA-7829-RJ": [
        [75.7800, 26.9100],
        [75.7850, 26.9100],
        [75.7850, 26.9150],
        [75.7800, 26.9150],
        [75.7800, 26.9100],
    ],
    "KHA-3421-RJ": [
        [70.9000, 26.9100],
        [70.9100, 26.9100],
        [70.9100, 26.9200],
        [70.9000, 26.9200],
        [70.9000, 26.9100],
    ],
    "PLT-5510-JP": [
        [75.7600, 26.8800],
        [75.7680, 26.8800],
        [75.7680, 26.8860],
        [75.7600, 26.8860],
        [75.7600, 26.8800],
    ],
}


# ── Analysis Engine ──────────────────────────────────────────────────────

def analyze_parcel(request: GISAnalyzeRequest) -> GISAnalyzeResponse:
    """
    Perform geospatial analysis on a land parcel.

    Accepts GeoJSON, coordinate pairs, or a survey plot ID.
    Returns area, centroid, bounding box, and proximity alerts.
    """
    # 1. Resolve coordinates
    coords = _resolve_coordinates(request)
    if not coords or len(coords) < 3:
        # Return a minimal response with error
        return GISAnalyzeResponse(
            status="ERROR_INSUFFICIENT_COORDINATES",
            parcel_metrics=ParcelMetrics(
                area_sq_meters=0, area_hectares=0, area_acres=0, perimeter_meters=0
            ),
            centroid=Centroid(latitude=0, longitude=0),
            bounding_box=BoundingBox(
                min_latitude=0, min_longitude=0, max_latitude=0, max_longitude=0
            ),
            proximity_alerts=[],
            total_alerts=0,
            risk_summary="Insufficient coordinates provided. At least 3 coordinate pairs required for polygon analysis.",
            survey_plot_id=request.survey_plot_id,
        )

    # 2. Compute metrics
    area_sqm = polygon_area_sq_meters(coords)
    area_ha = sq_meters_to_hectares(area_sqm)
    area_ac = sq_meters_to_acres(area_sqm)
    perimeter = polygon_perimeter_meters(coords)

    centroid_lat, centroid_lon = polygon_centroid(coords)
    bbox = polygon_bounding_box(coords)

    # 3. Proximity checks
    alerts: list[ProximityAlert] = []
    if request.check_proximity:
        alerts = _check_proximity(centroid_lat, centroid_lon)

    # 4. Risk summary
    critical = sum(1 for a in alerts if a.severity in ("CRITICAL", "WARNING"))
    caution = sum(1 for a in alerts if a.severity == "CAUTION")
    if critical > 0:
        risk_summary = f"HIGH RISK: {critical} critical/warning alert(s) detected. Land use restrictions apply."
    elif caution > 0:
        risk_summary = f"MODERATE RISK: {caution} proximity caution(s). Review regulations before proceeding."
    else:
        risk_summary = "LOW RISK: No proximity hazards detected. Standard zoning rules apply."

    return GISAnalyzeResponse(
        status="ANALYSIS_COMPLETE",
        parcel_metrics=ParcelMetrics(
            area_sq_meters=round(area_sqm, 2),
            area_hectares=round(area_ha, 4),
            area_acres=round(area_ac, 4),
            perimeter_meters=round(perimeter, 2),
        ),
        centroid=Centroid(latitude=round(centroid_lat, 6), longitude=round(centroid_lon, 6)),
        bounding_box=BoundingBox(**{k: round(v, 6) for k, v in bbox.items()}),
        proximity_alerts=alerts,
        total_alerts=len(alerts),
        risk_summary=risk_summary,
        survey_plot_id=request.survey_plot_id,
    )


def _resolve_coordinates(request: GISAnalyzeRequest) -> list[list[float]]:
    """Resolve input coordinates from GeoJSON, raw coords, or survey plot ID."""
    # Priority 1: GeoJSON
    if request.geojson:
        return extract_coordinates_from_geojson(request.geojson)

    # Priority 2: Raw coordinates
    if request.coordinates and len(request.coordinates) >= 3:
        return request.coordinates

    # Priority 3: Survey plot lookup
    if request.survey_plot_id and request.survey_plot_id in SAMPLE_SURVEY_PLOTS:
        return SAMPLE_SURVEY_PLOTS[request.survey_plot_id]

    return []


def _check_proximity(lat: float, lon: float) -> list[ProximityAlert]:
    """Check parcel centroid against all known hazard/restriction zones."""
    alerts: list[ProximityAlert] = []

    for zone in HAZARD_ZONES:
        distance = haversine_distance(lat, lon, zone["centroid_lat"], zone["centroid_lon"])

        # Only alert if within 3x the zone radius
        alert_radius = zone["radius_m"] * 3.0

        if distance <= alert_radius:
            if distance <= zone["radius_m"]:
                severity = "CRITICAL"
            elif distance <= zone["radius_m"] * 1.5:
                severity = "WARNING"
            elif distance <= zone["radius_m"] * 2.0:
                severity = "CAUTION"
            else:
                severity = "SAFE"

            alerts.append(ProximityAlert(
                zone_type=zone["type"],
                zone_name=zone["name"],
                distance_meters=round(distance, 1),
                severity=severity,
                regulation_reference=zone["regulation"],
                advisory=zone["advisory"],
            ))

    # Sort by severity (CRITICAL first) then by distance
    severity_order = {"CRITICAL": 0, "WARNING": 1, "CAUTION": 2, "SAFE": 3}
    alerts.sort(key=lambda a: (severity_order.get(a.severity, 4), a.distance_meters))

    return alerts
