/**
 * =============================================================
 * BHOOMI-NEXUS — GIS Service Layer
 * =============================================================
 * ArcGIS REST client for NIC Bharat Maps AdminGPHierarchy service.
 * Provides real administrative boundary GeoJSON data for:
 *   - States (Layer 0)
 *   - Districts (Layer 1)
 *   - Blocks/Tehsils (Layer 2)
 *   - Gram Panchayats (Layer 3)
 *
 * Data Source: National Informatics Centre (NIC)
 * Service: https://mapservice.gov.in/mapserviceserv176/rest/services/Panchayat/AdminGPHierarchy/MapServer
 * Coordinate System: WGS84 (EPSG:4326)
 * Attribution: "Administrative boundaries © NIC Bharat Maps, Survey of India (Census 2011 codification)"
 * =============================================================
 */

(function () {
  "use strict";

  const BASE_URL =
    "https://mapservice.gov.in/mapserviceserv176/rest/services/Panchayat/AdminGPHierarchy/MapServer";

  // Layer IDs in the NIC AdminGPHierarchy MapServer
  const LAYERS = {
    STATE: 0,
    DISTRICT: 1,
    BLOCK: 2,
    GRAM_PANCHAYAT: 3,
  };

  // ---- In-memory cache ----
  const _cache = new Map();

  // ---- Active AbortControllers keyed by layer ----
  const _controllers = new Map();

  // ---- Attribution text ----
  const ATTRIBUTION =
    "Administrative boundaries © NIC Bharat Maps | Survey of India (Census 2011 codification)";

  // ---- Data provenance metadata per layer ----
  const PROVENANCE = {
    [LAYERS.STATE]: {
      source: "National Informatics Centre (NIC)",
      serviceUrl: BASE_URL + "/" + LAYERS.STATE,
      layerName: "State",
      layerId: LAYERS.STATE,
      dataType: "Administrative Boundary (Polygon)",
      lastKnownUpdate: "October 2017 (service description)",
      official: true,
      attribution: ATTRIBUTION,
    },
    [LAYERS.DISTRICT]: {
      source: "National Informatics Centre (NIC)",
      serviceUrl: BASE_URL + "/" + LAYERS.DISTRICT,
      layerName: "District",
      layerId: LAYERS.DISTRICT,
      dataType: "Administrative Boundary (Polygon)",
      lastKnownUpdate: "Census 2011 codification, supplemented post-2011 (700+ codes)",
      official: true,
      attribution: ATTRIBUTION,
    },
    [LAYERS.BLOCK]: {
      source: "National Informatics Centre (NIC)",
      serviceUrl: BASE_URL + "/" + LAYERS.BLOCK,
      layerName: "Block / Sub-District",
      layerId: LAYERS.BLOCK,
      dataType: "Administrative Boundary (Polygon)",
      lastKnownUpdate: "Census 2011 codification",
      official: true,
      attribution: ATTRIBUTION,
    },
    [LAYERS.GRAM_PANCHAYAT]: {
      source: "National Informatics Centre (NIC)",
      serviceUrl: BASE_URL + "/" + LAYERS.GRAM_PANCHAYAT,
      layerName: "Gram Panchayat",
      layerId: LAYERS.GRAM_PANCHAYAT,
      dataType: "Administrative Boundary (Polygon)",
      lastKnownUpdate: "Census 2011 codification",
      official: true,
      attribution: ATTRIBUTION,
    },
  };

  /**
   * Build an ArcGIS REST query URL.
   * @param {number} layerId - Layer index (0-3)
   * @param {object} params - Query parameters
   * @returns {string} Full query URL
   */
  function buildQueryUrl(layerId, params) {
    const defaults = {
      outSR: "4326",
      f: "geojson",
      returnGeometry: "true",
    };
    const merged = Object.assign({}, defaults, params);
    const qs = Object.entries(merged)
      .map(
        ([k, v]) => encodeURIComponent(k) + "=" + encodeURIComponent(v)
      )
      .join("&");
    return BASE_URL + "/" + layerId + "/query?" + qs;
  }

  /**
   * Fetch GeoJSON from the ArcGIS REST service with caching and cancellation.
   * @param {number} layerId
   * @param {object} queryParams
   * @param {string} cacheKey - Unique cache key for this query
   * @returns {Promise<object|null>} GeoJSON FeatureCollection or null on error
   */
  async function fetchGeoJSON(layerId, queryParams, cacheKey) {
    // Return cached result if available
    if (_cache.has(cacheKey)) {
      return _cache.get(cacheKey);
    }

    // Cancel any previous in-flight request for this layer
    const controllerKey = "layer_" + layerId + "_" + cacheKey;
    if (_controllers.has(controllerKey)) {
      _controllers.get(controllerKey).abort();
    }
    const controller = new AbortController();
    _controllers.set(controllerKey, controller);

    const url = buildQueryUrl(layerId, queryParams);

    try {
      const response = await fetch(url, {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });

      if (!response.ok) {
        console.warn(
          "[BhoomiGIS] HTTP " + response.status + " from " + url
        );
        return null;
      }

      const data = await response.json();

      // Validate GeoJSON structure
      if (
        !data ||
        data.type !== "FeatureCollection" ||
        !Array.isArray(data.features)
      ) {
        // ArcGIS sometimes returns esri JSON instead of GeoJSON — try to handle
        if (data && data.error) {
          console.warn("[BhoomiGIS] Service error:", data.error.message);
          return null;
        }
        console.warn("[BhoomiGIS] Unexpected response format from", url);
        return null;
      }

      // Attach provenance metadata
      data._provenance = PROVENANCE[layerId] || {};
      data._fetchedAt = new Date().toISOString();

      // Cache the result
      _cache.set(cacheKey, data);
      return data;
    } catch (err) {
      if (err.name === "AbortError") {
        // Request was intentionally cancelled
        return null;
      }
      console.warn("[BhoomiGIS] Network error:", err.message);
      return null;
    } finally {
      _controllers.delete(controllerKey);
    }
  }

  // ========================================================
  // PUBLIC API
  // ========================================================

  /**
   * Fetch all state boundaries (simplified).
   * @returns {Promise<object|null>} GeoJSON FeatureCollection
   */
  async function fetchStates() {
    return fetchGeoJSON(
      LAYERS.STATE,
      {
        where: "1=1",
        outFields: "STNAME,STCODE11,State_LGD",
        returnGeometry: "true",
        
      },
      "states_all"
    );
  }

  /**
   * Fetch district boundaries for a given state.
   * @param {string} stateName - State name (uppercase, e.g. "RAJASTHAN")
   * @returns {Promise<object|null>} GeoJSON FeatureCollection
   */
  async function fetchDistricts(stateName) {
    const name = (stateName || "").toUpperCase().trim();
    if (!name) return null;

    return fetchGeoJSON(
      LAYERS.DISTRICT,
      {
        where: "stname='" + name.replace(/'/g, "''") + "'",
        outFields: "D_Pan_Name,stname,dtcode11,Dist_LGD,D_Pan_Code",
        returnGeometry: "true",
      },
      "districts_" + name
    );
  }

  /**
   * Fetch block/tehsil boundaries for a given district within a state.
   * @param {string} districtName - District name (uppercase)
   * @param {string} stateName - State name (uppercase)
   * @returns {Promise<object|null>} GeoJSON FeatureCollection
   */
  async function fetchBlocks(districtName, stateName) {
    const dist = (districtName || "").toUpperCase().trim();
    const st = (stateName || "").toUpperCase().trim();
    if (!dist || !st) return null;

    return fetchGeoJSON(
      LAYERS.BLOCK,
      {
        where:
          "D_Pan_Name='" +
          dist.replace(/'/g, "''") +
          "' AND state='" +
          st.replace(/'/g, "''") +
          "'",
        outFields:
          "B_Pan_Name,block_name,D_Pan_Name,district,state,block_lgd,B_Pan_Code",
        returnGeometry: "true",
      },
      "blocks_" + st + "_" + dist
    );
  }

  /**
   * Fetch Gram Panchayat boundaries for a given block, district, and state.
   * @param {string} blockName - Block name (uppercase)
   * @param {string} districtName - District name (uppercase)
   * @param {string} stateName - State name (uppercase)
   * @returns {Promise<object|null>} GeoJSON FeatureCollection
   */
  async function fetchGramPanchayats(blockName, districtName, stateName) {
    const blk = (blockName || "").toUpperCase().trim();
    const dist = (districtName || "").toUpperCase().trim();
    const st = (stateName || "").toUpperCase().trim();
    if (!blk || !dist || !st) return null;

    return fetchGeoJSON(
      LAYERS.GRAM_PANCHAYAT,
      {
        where:
          "blkname='" +
          blk.replace(/'/g, "''") +
          "' AND DTNAME='" +
          dist.replace(/'/g, "''") +
          "' AND STNAME='" +
          st.replace(/'/g, "''") +
          "'",
        outFields:
          "GPNAME,GPCODE,STNAME,DTNAME,SDTNAME,blkname,VILNAME11,VILCODE11,DT_LGD,SDT_LGD,ST_LGD",
        returnGeometry: "true",
      },
      "gp_" + st + "_" + dist + "_" + blk
    );
  }

  /**
   * Identify which administrative features contain a given lat/lon point.
   * Uses ArcGIS REST geometry intersection query.
   * @param {number} lat
   * @param {number} lon
   * @returns {Promise<object>} { state, district, block, gp } with feature properties
   */
  async function identifyLocation(lat, lon) {
    const result = { state: null, district: null, block: null, gp: null };
    const point = JSON.stringify({
      x: lon,
      y: lat,
      spatialReference: { wkid: 4326 },
    });

    // Query each layer for the point
    const layerConfigs = [
      {
        key: "state",
        layerId: LAYERS.STATE,
        outFields: "STNAME,STCODE11,State_LGD",
      },
      {
        key: "district",
        layerId: LAYERS.DISTRICT,
        outFields: "D_Pan_Name,stname,dtcode11,Dist_LGD",
      },
      {
        key: "block",
        layerId: LAYERS.BLOCK,
        outFields: "B_Pan_Name,block_name,D_Pan_Name,state,block_lgd",
      },
    ];

    const promises = layerConfigs.map(async (cfg) => {
      const cacheKey = "identify_" + cfg.key + "_" + lat.toFixed(4) + "_" + lon.toFixed(4);
      const data = await fetchGeoJSON(
        cfg.layerId,
        {
          geometry: point,
          geometryType: "esriGeometryPoint",
          spatialRel: "esriSpatialRelIntersects",
          outFields: cfg.outFields,
          returnGeometry: "false",
          f: "geojson",
        },
        cacheKey
      );

      if (data && data.features && data.features.length > 0) {
        result[cfg.key] = data.features[0].properties || {};
      }
    });

    await Promise.allSettled(promises);
    return result;
  }

  /**
   * Search for geographic features by name.
   * Searches states and districts with LIKE query.
   * @param {string} query - Search term
   * @returns {Promise<Array>} Array of { name, type, layerId, properties, bounds }
   */
  async function searchByName(query) {
    const q = (query || "").trim().toUpperCase();
    if (q.length < 2) return [];

    const results = [];
    const escapedQ = q.replace(/'/g, "''");

    // Search states
    const stateData = await fetchGeoJSON(
      LAYERS.STATE,
      {
        where: "STNAME LIKE '%" + escapedQ + "%'",
        outFields: "STNAME,STCODE11,State_LGD",
        returnGeometry: "true",
        },
      "search_state_" + q
    );

    if (stateData && stateData.features) {
      stateData.features.forEach(function (feat) {
        results.push({
          name: feat.properties.STNAME,
          type: "State",
          layerId: LAYERS.STATE,
          properties: feat.properties,
          geometry: feat.geometry,
        });
      });
    }

    // Search districts
    const distData = await fetchGeoJSON(
      LAYERS.DISTRICT,
      {
        where: "D_Pan_Name LIKE '%" + escapedQ + "%'",
        outFields: "D_Pan_Name,stname,dtcode11,Dist_LGD",
        returnGeometry: "true",
        resultRecordCount: "20",
      },
      "search_district_" + q
    );

    if (distData && distData.features) {
      distData.features.forEach(function (feat) {
        results.push({
          name: feat.properties.D_Pan_Name + ", " + feat.properties.stname,
          type: "District",
          layerId: LAYERS.DISTRICT,
          properties: feat.properties,
          geometry: feat.geometry,
        });
      });
    }

    // Search blocks
    const blockData = await fetchGeoJSON(
      LAYERS.BLOCK,
      {
        where: "B_Pan_Name LIKE '%" + escapedQ + "%'",
        outFields: "B_Pan_Name,D_Pan_Name,state,block_lgd",
        returnGeometry: "true",
        resultRecordCount: "15",
      },
      "search_block_" + q
    );

    if (blockData && blockData.features) {
      blockData.features.forEach(function (feat) {
        results.push({
          name:
            feat.properties.B_Pan_Name +
            " Block, " +
            feat.properties.D_Pan_Name +
            ", " +
            feat.properties.state,
          type: "Block",
          layerId: LAYERS.BLOCK,
          properties: feat.properties,
          geometry: feat.geometry,
        });
      });
    }

    return results;
  }

  /**
   * Clear all cached data.
   */
  function clearCache() {
    _cache.clear();
  }

  /**
   * Get provenance metadata for a given layer.
   * @param {number} layerId
   * @returns {object}
   */
  function getProvenance(layerId) {
    return PROVENANCE[layerId] || {};
  }

  // ---- Export to window ----
  window.BhoomiGIS = {
    BASE_URL: BASE_URL,
    LAYERS: LAYERS,
    ATTRIBUTION: ATTRIBUTION,
    fetchStates: fetchStates,
    fetchDistricts: fetchDistricts,
    fetchBlocks: fetchBlocks,
    fetchGramPanchayats: fetchGramPanchayats,
    identifyLocation: identifyLocation,
    searchByName: searchByName,
    clearCache: clearCache,
    getProvenance: getProvenance,
  };
})();
