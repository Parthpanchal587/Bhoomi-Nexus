"""
Direct FastAPI endpoint integration test for OSINT Router.
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestOSINTAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_providers_endpoint(self):
        response = self.client.get("/api/v1/osint/providers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["providers"]), 4)

    def test_search_endpoint(self):
        payload = {
            "state": "Rajasthan",
            "district": "Jaipur",
            "tehsil": "Amber",
            "village": "Kukas",
            "khasra_number": "241/1",
        }
        response = self.client.post("/api/v1/osint/search", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("parcel", data)
        self.assertIn("risk_assessment", data)
        self.assertIn("graph", data)
        self.assertIn("timeline", data)
        self.assertIn("report", data)
        self.assertIn("markdown_dossier", data)

    def test_cross_check_endpoint(self):
        payload = {
            "document_text": "DEED OF CONVEYANCE\nState: Rajasthan\nDistrict: Jaipur\nKhasra: 241/1\nArea: 1.0 Ha",
            "filename": "conveyance_deed.txt",
            "declared_khasra": "241/1",
        }
        response = self.client.post("/api/v1/osint/cross-check", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("document_hash_sha256", data)
        self.assertIn("hash_disclaimer", data)

    def test_restrictions_endpoint(self):
        response = self.client.get("/api/v1/osint/restrictions?state=Rajasthan&district=Jaipur")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)

    def test_audit_endpoint(self):
        response = self.client.get("/api/v1/osint/audit")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["audit_logs"], list)


if __name__ == "__main__":
    unittest.main()
