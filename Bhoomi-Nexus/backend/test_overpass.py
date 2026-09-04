import urllib.request
import json

# Rural Jaipur / Sanganer agricultural coordinate
lat, lon = 26.8200, 75.8000
query = f"""[out:json][timeout:8];
(
  way["landuse"="farmland"](around:3000,{lat},{lon});
  way["landuse"="farmyard"](around:3000,{lat},{lon});
  way["landuse"="allotments"](around:3000,{lat},{lon});
  way["landuse"="meadow"](around:3000,{lat},{lon});
  way["landuse"](around:2000,{lat},{lon});
  way["building"](around:1000,{lat},{lon});
);
out geom 20;"""

req = urllib.request.Request(
    'https://overpass-api.de/api/interpreter',
    data=query.encode('utf-8'),
    headers={'User-Agent': 'BhoomiNexus/1.0 (GIS Engine)'}
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        elements = data.get('elements', [])
        print(f"Retrieved {len(elements)} real elements")
        for i, el in enumerate(elements[:6]):
            tags = el.get('tags', {})
            geom = el.get('geometry', [])
            print(f"Element {i+1}: tags={tags}, geom points={len(geom)}")
except Exception as e:
    print("Error:", e)
