# BHOOMI-NEXUS: Map & GIS Viewport Architecture

**Version:** 2.4.0  
**Map Engine:** Leaflet.js 1.9.4  
**Primary Coordinate Reference System:** EPSG:4326 (WGS84)  
**Territorial Policy:** Sovereign India-Only Viewport  

---

## 1. Executive Summary & Root Cause Analysis

### 1.1 The Amer, Jaipur Zoom/Jump Bug — Root Cause & Resolution
- **Observed Defect:** When a user selected `Rajasthan` $\rightarrow$ `Jaipur` $\rightarrow$ `Amer` or performed search actions, the map would occasionally jump/pan to a vast world-scale extent or center over the Himalayas, Tibet, or China.
- **Root Causes Identified:**
  1. **Corrupt Generalization Tolerance:** In `gis_service.js`, administrative layer queries contained `maxAllowableOffset: "500"` and `"1000"`. Because the query requested `outSR=4326` (WGS84 degrees), the ArcGIS server interpreted these offsets in *degrees* (where 1 degree $\approx$ 111 km). This collapsed geometry polygons into degenerated single points or corrupt global extents spanning thousands of kilometers.
  2. **Unbounded `flyToBounds()` Invocations:** Several UI functions called `map.flyToBounds(layer.getBounds())` without validating whether the bounds were degenerate, infinite, or extended outside India.
  3. **Empty Search Button Click:** In `locateSearchedPlace()`, if the text search input was empty and the user clicked "Locate / Search", the function silently aborted rather than navigating to the active dropdown Tehsil/District.
  4. **Search Query Collision:** Unfiltered searches for "Amer" matched "Ambernath" in Maharashtra or other blocks whose generalized polygons triggered global flyouts.
- **Permanent Solution:**
  - Eliminated inappropriate degree-scale `maxAllowableOffset` values from `gis_service.js`.
  - Implemented `safeFlyToBounds(bounds, fallbackCenter, fallbackZoom)` with strict WGS84 bounding box validation (`4.0° N <= Lat <= 38.5° N` and `65.0° E <= Lon <= 100.0° E`).
  - Wired empty-input search button clicks directly into `handleTehsilChange()`, guaranteeing that clicking "Locate / Search" when `Amer` is selected immediately flies to Amer coordinates (`26.9855° N, 75.8507° E`, zoom 13).
  - Enforced `isPointInIndiaLand(lat, lon)` check on all search results, strictly rejecting non-Indian geocoder returns.

---

## 2. Sovereign India-Only Viewport Enforcement

### 2.1 Geographic Extent & Clamping
The map canvas enforces strict India geographic boundaries:
```javascript
const southWest = L.latLng(4.0, 65.0);
const northEast = L.latLng(38.5, 100.0);
const indiaBounds = L.latLngBounds(southWest, northEast);

map = L.map("cadastral-map", {
  center: [currentLat, currentLon],
  zoom: 11,
  minZoom: 4,
  maxZoom: 19,
  maxBounds: indiaBounds,
  maxBoundsViscosity: 1.0,
  zoomControl: false
});
```

### 2.2 Sovereign Inverse Boundary Mask (`applyIndiaOnlyMask()`)
- **Pane:** Dedicated `indiaMaskPane` with `zIndex: 350` (positioned directly above raster tiles, below vector boundaries and UI pins).
- **GeoJSON Structure:** A global bounding box polygon covering `[-90, -180]` to `[90, 180]` with an interior cutout hole formed by India's high-resolution sovereign boundary polygon and 80 island polygons (Andaman & Nicobar, Lakshadweep).
- **Styling:**
  - `fillColor: '#07172B'` (Opaque sovereign dark navy)
  - `fillOpacity: 1.0` (100% opaque — foreign landmasses including Pakistan, China, Nepal, Bangladesh, and open oceans outside Indian territorial waters are completely concealed).
  - `color: '#FF9933'` (Sovereign Tricolor Saffron border line along India's international perimeter).
  - `weight: 2.2`, `interactive: false`.

### 2.3 Ray-Casting Territorial Validation (`window.isPointInIndiaLand`)
Whenever a user clicks anywhere on the map or searches for a place name, the coordinate is verified before any action is executed:
```javascript
if (window.isPointInIndiaLand && !window.isPointInIndiaLand(lat, lon)) {
  showToast("Only Indian sovereign territory is accessible. Surrounding regions and non-Indian waters are masked.");
  return;
}
```

---

## 3. Data Flow Pipeline

```
USER SELECTION (State: Rajasthan, District: Jaipur, Tehsil: Amer)
               │
               ▼
   handleTehsilChange() / locateSearchedPlace()
               │
               ▼
   COORDINATE RESOLUTION: Lat = 26.9855, Lon = 75.8507
               │
               ▼
   TERRITORIAL AUDIT: isPointInIndiaLand(26.9855, 75.8507) -> PASS (100% Inside India)
               │
               ▼
   CAMERA FLIGHT: map.flyTo([26.9855, 75.8507], 13) [STRICTLY CONTROLLED]
               │
               ▼
   INSPECTION MARKER: inspectionMarker.setLatLng([26.9855, 75.8507])
   (Note: LOCATION MARKER ≠ CADASTRAL BOUNDARY. No fake circles drawn.)
               │
               ▼
   PARALLEL DATA RETRIEVAL (Backend + Direct Open Resilient Fallback):
   ├─► Open-Meteo ECMWF IFS: Weather & Multi-Depth Soil Moisture (m³/m³)
   ├─► ISRIC SoilGrids 2.0: pH, Organic Carbon, Clay, Sand (250m Grids)
   └─► NIC Bharat Maps: Administrative Hierarchy (Amer Block, Jaipur District)
               │
               ▼
   DOM & POPUP RENDER: Structured per Part 15 with explicit data provenance.
```

---

## 4. Cadastral Inspection & Zero-Fabrication Doctrine

1. **Location Pin Only:** The map draws only a single, accurate inspection marker pin at the clicked coordinate.
2. **No Fake Polygons:** The system strictly avoids drawing synthetic 200m or 120m circular buffers and claiming they represent "Khasra boundaries" or "Section 90-A areas". If authoritative Bhu-Naksha cadastral geometry is unavailable via public REST, the UI truthfully states:
   `"Authoritative parcel boundary unavailable."`
3. **Popup Structure:** Follows standard Government GIS specifications:
   - Header: `CADASTRAL PARCEL GIS ANALYSIS`
   - Location details with 6-decimal coordinates.
   - Cadastral section with `Parcel ID: Not resolved`, `Khasra: Unavailable`, `Area: Unavailable`.
   - Environment section with air temperature, humidity, rainfall.
   - Soil section with multi-depth moisture ($m^3/m^3$), soil temperature (°C), pH, SOC.
   - Provenance badges: `[CADASTRAL]`, `[MODELLED]`, `[SPATIAL ESTIMATE]`.
