"""
Unit and integration tests for the ISRIC SoilGrids 250m WCS pipeline.
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


class TestSoilGridsPipeline(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_soil_health_check_endpoint(self):
        """Verify the /api/v1/env/soil/health endpoint returns 200 and online status."""
        resp = self.client.get("/api/v1/env/soil/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertEqual(data["provider"], "ISRIC SoilGrids 250m")
        self.assertEqual(data["method"], "WCS 2.0.1")
        self.assertIn("properties_supported", data)
        self.assertIn("phh2o (pH)", data["properties_supported"])

    def test_invalid_coordinates_rejected(self):
        """Verify invalid coordinates return 400 Bad Request."""
        resp = self.client.get("/api/v1/env/soil?lat=999.0&lon=999.0")
        self.assertEqual(resp.status_code, 400)

    def test_soilgrids_conversion_factors(self):
        """Verify official conversion factors (phh2o / 10, soc / 10, clay / 10, sand / 10)."""
        provider = SoilGridsWCSProvider()
        self.assertEqual(provider.CONVERSION_FACTORS["phh2o"][0], 10.0)
        self.assertEqual(provider.CONVERSION_FACTORS["soc"][0], 10.0)
        self.assertEqual(provider.CONVERSION_FACTORS["clay"][0], 10.0)
        self.assertEqual(provider.CONVERSION_FACTORS["sand"][0], 10.0)

    def test_mocked_wcs_response_structure(self):
        """Verify that a successful provider call produces the expected structured JSON."""
        mock_result = {
            "status": "success",
            "latitude": 26.9855,
            "longitude": 75.8587,
            "location": {"latitude": 26.9855, "longitude": 75.8587},
            "source": {
                "provider": "ISRIC SoilGrids",
                "product": "SoilGrids 250m",
                "method": "WCS 2.0.1 Coverage Extraction",
                "dataType": "spatial_model_estimate",
                "resolution": "250m",
                "depth": "0-5cm"
            },
            "soil": {
                "ph": {"value": 7.5, "unit": "pH", "classification": "Neutral / Optimal"},
                "soc": {"value": 14.8, "unit": "g/kg"},
                "clay": {"value": 24.2, "unit": "%"},
                "sand": {"value": 52.7, "unit": "%"}
            },
            "summary_0_5cm": {
                "ph": 7.5,
                "soil_organic_carbon_g_per_kg": 14.8,
                "clay_pct": 24.2,
                "sand_pct": 52.7,
                "estimated_texture": "Loam / Alluvial"
            },
            "ph_h2o_topsoil": 7.5,
            "soc_g_per_kg_topsoil": 14.8,
            "clay_percent_topsoil": 24.2,
            "sand_percent_topsoil": 52.7
        }

        with patch.object(soil_service, 'get_soil_properties', return_value=mock_result):
            resp = self.client.get("/api/v1/env/soil?lat=26.9855&lon=75.8587")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["ph_h2o_topsoil"], 7.5)
            self.assertEqual(data["soc_g_per_kg_topsoil"], 14.8)
            self.assertEqual(data["clay_percent_topsoil"], 24.2)
            self.assertEqual(data["sand_percent_topsoil"], 52.7)


if __name__ == '__main__':
    unittest.main()
