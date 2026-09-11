"""
Comprehensive Unit & Integration Test Suite for Ask BHOOMI Land Intelligence Engine.
Validates:
1. 16+ Canonical Intents
2. Multilingual NLU (English, Hindi, Hinglish)
3. Dynamic Parcel Context Source-of-Truth
4. 4-Tier Data States (VERIFIED, PROVISIONAL, NOT_FOUND, UNAVAILABLE)
5. Zero Fake Data Guarantee (Missing != "No")
6. Evidence & Provenance Tracking
7. Multi-Intent Handling
8. Unknown Queries & Guardrails
"""

import unittest
from fastapi.testclient import TestClient
import os
import sys

backend_path = os.path.abspath("Bhoomi-Nexus/backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.services.land_intelligence import LandIntent, DataStatus, LandIntelligenceEngine

class TestLandIntelligenceEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_registered_owner_english(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Who owns this land?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.REGISTERED_OWNER)
        self.assertIn("registered", data["summary"].lower())
        self.assertEqual(data["data_status"], DataStatus.UNAVAILABLE)

    def test_02_registered_owner_hinglish(self):
        res = self.client.post("/api/ai/query", json={
            "query": "kiske naam pe hai?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.REGISTERED_OWNER)

    def test_03_registered_owner_hindi(self):
        res = self.client.post("/api/ai/query", json={
            "query": "इस जमीन का पंजीकृत मालिक कौन है?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.REGISTERED_OWNER)

    def test_04_ownership_classification_public_private(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Is this government land or private?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.LAND_OWNERSHIP_CLASSIFICATION)

    def test_05_ownership_classification_hinglish(self):
        res = self.client.post("/api/ai/query", json={
            "query": "ye zameen govt ki hai ya private?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.LAND_OWNERSHIP_CLASSIFICATION)

    def test_06_tribal_transfer_restriction(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Can OBC or General buy SC/ST tribal land?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.TRIBAL_TRANSFER_RESTRICTION)
        self.assertIn("Section 42", data["summary"])

    def test_07_mortgage_loan(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Any loan on this property?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.MORTGAGE_ENCUMBRANCE)
        # Verify that missing data != "No loan exists"
        self.assertIn("UNAVAILABLE", data["data_status"])

    def test_08_litigation_clear_distinction(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Is there any court case or dispute?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.TITLE_LITIGATION)
        # Ensure clear distinction between NO MATCH FOUND vs NO CASE EXISTS
        self.assertIn("DOES NOT ESTABLISH THAT NO CASE EXISTS", data["summary"])

    def test_09_title_chain_30_year(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Show 30 year ownership history",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.TITLE_CHAIN_30_YEAR)

    def test_10_document_authenticity(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Is this document real and verified?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.DOCUMENT_AUTHENTICITY)
        # Distinction between file integrity vs legal title
        self.assertIn("FILE INTEGRITY", data["summary"])

    def test_11_khasra_identity_area(self):
        res = self.client.post("/api/ai/query", json={
            "query": "What is the khasra number and total area?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.PARCEL_IDENTITY_AREA)

    def test_12_boundaries(self):
        res = self.client.post("/api/ai/query", json={
            "query": "What are the north south east west boundaries?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.BOUNDARIES)
        self.assertIn("Satellite imagery", data["summary"])
        self.assertIn("DO NOT constitute legal boundaries", data["summary"])

    def test_13_land_use_conversion(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Can I build a house here?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.LAND_USE_CONVERSION)
        self.assertIn("Section 90-A", data["summary"])

    def test_14_municipal_rera_approval(self):
        res = self.client.post("/api/ai/query", json={
            "query": "RERA approved hai kya?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.MUNICIPAL_RERA_APPROVAL)

    def test_15_general_due_diligence_summary(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Can I buy this land?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], LandIntent.GENERAL_LAND_QUERY)
        self.assertIn("DUE DILIGENCE", data["summary"])

    def test_16_multi_intent_query(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Who owns this land and is there any mortgage or loan on it?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        intents = data.get("intents", [])
        self.assertIn(LandIntent.REGISTERED_OWNER, intents)
        self.assertIn(LandIntent.MORTGAGE_ENCUMBRANCE, intents)
        # Ensure both parts are answered
        self.assertIn("Registered Owner", data["summary"])
        self.assertIn("Mortgage", data["summary"])

    def test_17_parcel_switching_source_of_truth(self):
        res_amer = self.client.post("/api/ai/query", json={
            "query": "Who is the registered owner?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "tehsil": "Amer", "khasra": "12/4"}
        }).json()

        res_bengaluru = self.client.post("/api/ai/query", json={
            "query": "Who is the registered owner?",
            "parcel": {"latitude": 12.9716, "longitude": 77.5946, "district": "Bengaluru Urban", "tehsil": "Bengaluru North", "khasra": "99"}
        }).json()

        self.assertEqual(res_amer["parcel"]["district"], "Jaipur")
        self.assertEqual(res_amer["parcel"]["khasra"], "12/4")
        self.assertEqual(res_bengaluru["parcel"]["district"], "Bengaluru Urban")
        self.assertEqual(res_bengaluru["parcel"]["khasra"], "99")
        self.assertNotEqual(res_amer["parcel"]["latitude"], res_bengaluru["parcel"]["latitude"])

    def test_18_unknown_query_guardrails(self):
        res = self.client.post("/api/ai/query", json={
            "query": "How many moons does Jupiter have?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        }).json()
        self.assertEqual(res["intent"], LandIntent.UNKNOWN_QUERY)
        self.assertIn("could not confidently determine", res["summary"].lower())

    def test_19_structured_evidence_contract(self):
        res = self.client.post("/api/ai/query", json={
            "query": "Who is the registered legal owner?",
            "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
        }).json()
        evidence = res.get("evidence", [])
        self.assertGreater(len(evidence), 0)
        first_ev = evidence[0]
        self.assertIn("field", first_ev)
        self.assertIn("value", first_ev)
        self.assertIn("status", first_ev)
        self.assertIn("source", first_ev)
        self.assertIn("sourceUrl", first_ev)
        self.assertIn("retrievedAt", first_ev)

    def test_20_all_quick_question_chips(self):
        quick_chips = [
            ("Is this land Public / Government (Hospital/School/Nazul) or Private patta land?", LandIntent.LAND_OWNERSHIP_CLASSIFICATION),
            ("Can an OBC or General buyer purchase SC/ST tribal land without DM permission?", LandIntent.TRIBAL_TRANSFER_RESTRICTION),
            ("Who is the legal registered owner of this property?", LandIntent.REGISTERED_OWNER),
            ("Who sold this property previously according to the deed history?", LandIntent.TITLE_CHAIN_30_YEAR),
            ("Is this property document real and verified?", LandIntent.DOCUMENT_AUTHENTICITY),
            ("Is the title deed clear and free of any disputes or court cases?", LandIntent.TITLE_LITIGATION),
            ("Are there any missing stamps, signatures, or legal clauses?", LandIntent.DOCUMENT_COMPLETENESS),
            ("Give me an overall risk score and 3-bullet summary of this property.", LandIntent.PROPERTY_RISK_SUMMARY),
            ("Are there any mortgages, loans, or encumbrances on this land?", LandIntent.MORTGAGE_ENCUMBRANCE),
            ("Does this document include an Encumbrance Certificate (EC) to prove there are no pending bank loans?", LandIntent.ENCUMBRANCE_CERTIFICATE),
            ("What is the plot survey number and total area?", LandIntent.PARCEL_IDENTITY_AREA),
            ("What are the North, South, East, and West boundary boundaries?", LandIntent.BOUNDARIES),
            ("Does this land fall inside a flood zone or forest buffer area?", LandIntent.SPATIAL_RESTRICTIONS),
            ("Is this land agricultural, residential, or commercial?", LandIntent.LAND_USE_CONVERSION),
            ("Has the layout received official municipal or development authority approval?", LandIntent.MUNICIPAL_RERA_APPROVAL)
        ]

        for chip_text, expected_intent in quick_chips:
            res = self.client.post("/api/ai/query", json={
                "query": chip_text,
                "parcel": {"latitude": 26.9855, "longitude": 75.8507, "district": "Jaipur", "state": "Rajasthan"}
            }).json()
            intents = res.get("intents", [res.get("intent")])
            self.assertTrue(
                expected_intent in intents or res.get("intent") == expected_intent,
                f"Chip '{chip_text}' expected {expected_intent}, got {res.get('intent')} (intents: {intents})"
            )

if __name__ == "__main__":
    unittest.main()
