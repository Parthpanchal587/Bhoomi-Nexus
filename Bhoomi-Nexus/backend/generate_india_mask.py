import urllib.request
import json
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.ops import unary_union

print("Fetching official Survey of India boundary...")
url = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as resp:
    raw_data = json.loads(resp.read().decode("utf-8"))

geom = shape(raw_data["features"][0]["geometry"])
print(f"Original geometry: {geom.geom_type}, area: {geom.area:.2f}")

# Simplify geometry while strictly preserving official Indian boundary contours
# Tolerance 0.02 degrees (~2 km precision, very sharp at country zoom)
simplified_geom = geom.simplify(0.015, preserve_topology=True)
print(f"Simplified geometry: {simplified_geom.geom_type}, is_valid: {simplified_geom.is_valid}")

# 1. Save Boundary GeoJSON
boundary_geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Republic of India", "type": "National Boundary"},
            "geometry": mapping(simplified_geom)
        }
    ]
}
with open("frontend/india_boundary.json", "w", encoding="utf-8") as f:
    json.dump(boundary_geojson, f)

# 2. Build Inverted World Mask
# Exterior: world box [[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]
world_box = Polygon([
    [-180.0, -90.0],
    [180.0, -90.0],
    [180.0, 90.0],
    [-180.0, 90.0],
    [-180.0, -90.0]
])

# Difference: World minus India
inverted_mask = world_box.difference(simplified_geom)
mask_geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "World Mask (Non-India)"},
            "geometry": mapping(inverted_mask)
        }
    ]
}
with open("frontend/india_mask.json", "w", encoding="utf-8") as f:
    json.dump(mask_geojson, f)

import os
print(f"Done! Boundary size: {os.path.getsize('frontend/india_boundary.json')} bytes")
print(f"Done! Mask size: {os.path.getsize('frontend/india_mask.json')} bytes")
