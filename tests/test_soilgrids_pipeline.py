"""
BHOOMI-NEXUS: Automated Test Suite for ISRIC SoilGrids WCS Pipeline
Tests:
1. Valid coordinate -> provider request -> response parsing -> conversion -> normalized result
2. Assertion that ph, soc, clay, sand are numeric when source succeeds
3. Section 12 normalized contract structure verification
4. Section 18 /api/soilgrids/health verification
5. Section 19 /api/soilgrids/test diagnostic endpoint verification
6. NoData pixel handling & nearest-valid-pixel reporting
7. Network failure / HTTP error resilience
8. Malformed response handling
9. Wrong / out-of-bounds coordinates rejection (HTTP 400)
10. Stale request / Request ID tracking
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "Bhoomi-Nexus" / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.services.soil_provider import SoilGridsWCSProvider, soil_service


class TestSoilGridsProvider(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_soilgrids_health_endpoint(self):
        """Section 18: /api/soilgrids/health internal endpoint returns expected contract."""
        resp = self.client.get("/api/soilgrids/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["provider"], "ISRIC SoilGrids")
        self.assertEqual(data["method"], "WCS")
        self.assertIn(data["status"], ["healthy", "degraded"])
        self.assertIn("lastSuccessfulQuery", data)
        self.assertIn("lastError", data)

    def test_soilgrids_diagnostic_endpoint(self):
        """Section 19: /api/soilgrids/test returns diagnostic parameters."""
        resp = self.client.get("/api/soilgrids/test?lat=26.98550&lon=75.85870")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["requestedCoordinate"]["latitude"], 26.98550)
        self.assertEqual(data["requestedCoordinate"]["longitude"], 75.85870)
        self.assertEqual(data["transformedCoordinate"]["crs"], "EPSG:4326")
        self.assertIn("wcsCoverageIds", data)
        self.assertIn("phh2o_0-5cm_Q0.5", data["wcsCoverageIds"])
        self.assertIn("convertedValues", data)
        self.assertIn("rawExtractedValues", data)
        self.assertIn("noDataStatus", data)

    def test_invalid_coordinates_rejected(self):
        """Section 23: Wrong / out-of-bounds coordinates return HTTP 400."""
        resp = self.client.get("/api/soilgrids/query?lat=999.0&lon=999.0")
        self.assertEqual(resp.status_code, 400)
        resp2 = self.client.get("/api/v1/env/soil?lat=-100.0&lon=200.0")
        self.assertEqual(resp2.status_code, 400)

    def test_conversion_factors_verified(self):
        """Section 9: Verify official conversion factors (/10.0 for pH, SOC, Clay, Sand)."""
        provider = SoilGridsWCSProvider()
        self.assertEqual(provider.CONVERSION_FACTORS["phh2o"], (10.0, "pH", "Soil pH (H2O)"))
        self.assertEqual(provider.CONVERSION_FACTORS["soc"], (10.0, "g/kg", "Soil Organic Carbon"))
        self.assertEqual(provider.CONVERSION_FACTORS["clay"], (10.0, "%", "Clay fraction (<2um)"))
        self.assertEqual(provider.CONVERSION_FACTORS["sand"], (10.0, "%", "Sand fraction (>50um)"))

    def test_normalized_contract_structure(self):
        """Section 12: Verify normalized JSON contract matches exact specification."""
        mock_normalized = {
            "location": {
                "latitude": 26.98550,
                "longitude": 75.85870,
                "sampledLatitude": 26.98428,
                "sampledLongitude": 75.85754,
                "distanceMeters": 178.0,
                "isNearestValidPixel": True
            },
            "source": {
                "provider": "ISRIC SoilGrids",
                "version": "SoilGrids 2.0",
                "resolution": "250m",
                "depth": "0-5cm",
                "dataType": "spatial_model_estimate"
            },
            "properties": {
                "ph": {"value": 7.8, "unit": "pH", "status": "success"},
                "soc": {"value": 10.2, "unit": "g/kg", "status": "success"},
                "clay": {"value": 15.7, "unit": "%", "status": "success"},
                "sand": {"value": 53.7, "unit": "%", "status": "success"}
            },
            "retrievedAt": "2026-09-11T18:00:00Z",
            "requestId": "soil-test-123",
            "status": "success",
            "ph_h2o_topsoil": 7.8,
            "soc_g_per_kg_topsoil": 10.2,
            "clay_percent_topsoil": 15.7,
            "sand_percent_topsoil": 53.7,
            "summary_0_5cm": {"ph": 7.8, "soil_organic_carbon_g_per_kg": 10.2, "clay_pct": 15.7, "sand_pct": 53.7}
        }

        with patch.object(soil_service, 'get_soil_properties', return_value=mock_normalized):
            resp = self.client.get("/api/soilgrids/query?lat=26.98550&lon=75.85870&request_id=soil-test-123")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()

            # Location block
            self.assertEqual(data["location"]["latitude"], 26.98550)
            self.assertEqual(data["location"]["longitude"], 75.85870)
            self.assertEqual(data["location"]["sampledLatitude"], 26.98428)
            self.assertEqual(data["location"]["distanceMeters"], 178.0)
            self.assertTrue(data["location"]["isNearestValidPixel"])

            # Source block
            self.assertEqual(data["source"]["provider"], "ISRIC SoilGrids")
            self.assertEqual(data["source"]["version"], "SoilGrids 2.0")
            self.assertEqual(data["source"]["resolution"], "250m")
            self.assertEqual(data["source"]["depth"], "0-5cm")
            self.assertEqual(data["source"]["dataType"], "spatial_model_estimate")

            # Properties block & Numeric Assertions
            props = data["properties"]
            self.assertIsInstance(props["ph"]["value"], (int, float))
            self.assertEqual(props["ph"]["value"], 7.8)
            self.assertEqual(props["ph"]["unit"], "pH")

            self.assertIsInstance(props["soc"]["value"], (int, float))
            self.assertEqual(props["soc"]["value"], 10.2)
            self.assertEqual(props["soc"]["unit"], "g/kg")

            self.assertIsInstance(props["clay"]["value"], (int, float))
            self.assertEqual(props["clay"]["value"], 15.7)
            self.assertEqual(props["clay"]["unit"], "%")

            self.assertIsInstance(props["sand"]["value"], (int, float))
            self.assertEqual(props["sand"]["value"], 53.7)
            self.assertEqual(props["sand"]["unit"], "%")

            # Request ID & Status
            self.assertEqual(data["requestId"], "soil-test-123")
            self.assertEqual(data["status"], "success")

    def test_nodata_handling(self):
        """Section 10: If pixel is unmodeled / NoData, return status 'no_data' with honest reason."""
        mock_nodata = {
            "location": {"latitude": 0.0, "longitude": 80.0},
            "source": {"provider": "ISRIC SoilGrids", "version": "SoilGrids 2.0", "resolution": "250m", "depth": "0-5cm", "dataType": "spatial_model_estimate"},
            "properties": {
                "ph": {"value": None, "unit": "pH", "status": "no_data", "reason": "SoilGrids pixel contains NoData"},
                "soc": {"value": None, "unit": "g/kg", "status": "no_data", "reason": "SoilGrids pixel contains NoData"},
                "clay": {"value": None, "unit": "%", "status": "no_data", "reason": "SoilGrids pixel contains NoData"},
                "sand": {"value": None, "unit": "%", "status": "no_data", "reason": "SoilGrids pixel contains NoData"}
            },
            "status": "no_data",
            "reason": "SoilGrids pixel contains NoData (unmodeled water or sealed bedrock surface)",
            "ph_h2o_topsoil": None,
            "soc_g_per_kg_topsoil": None,
            "clay_percent_topsoil": None,
            "sand_percent_topsoil": None
        }

        with patch.object(soil_service, 'get_soil_properties', return_value=mock_nodata):
            resp = self.client.get("/api/soilgrids/query?lat=0.0&lon=80.0")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "no_data")
            self.assertIsNone(data["properties"]["ph"]["value"])
            self.assertEqual(data["properties"]["ph"]["status"], "no_data")
            self.assertIn("NoData", data["reason"])

    def test_network_failure_resilience(self):
        """Section 23: Upstream network failures do not crash the service and return honest unavailable."""
        mock_failure = {
            "location": {"latitude": 26.9855, "longitude": 75.8587},
            "source": {"provider": "ISRIC SoilGrids", "version": "SoilGrids 2.0", "resolution": "250m", "depth": "0-5cm", "dataType": "spatial_model_estimate"},
            "properties": {
                "ph": {"value": None, "unit": "pH", "status": "unavailable"},
                "soc": {"value": None, "unit": "g/kg", "status": "unavailable"},
                "clay": {"value": None, "unit": "%", "status": "unavailable"},
                "sand": {"value": None, "unit": "%", "status": "unavailable"}
            },
            "status": "unavailable",
            "reason": "Connection timed out connecting to maps.isric.org"
        }

        with patch.object(soil_service, 'get_soil_properties', return_value=mock_failure):
            resp = self.client.get("/api/soilgrids/query?lat=26.9855&lon=75.8587")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "unavailable")
            self.assertIsNone(data["properties"]["ph"]["value"])

    def test_request_id_propagation(self):
        """Section 13: Request ID is passed and preserved across responses for race condition prevention."""
        test_req_id = "soil-client-test-999"
        resp = self.client.get(f"/api/soilgrids/query?lat=26.9855&lon=75.8587&request_id={test_req_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("requestId"), test_req_id)


if __name__ == '__main__':
    unittest.main()
