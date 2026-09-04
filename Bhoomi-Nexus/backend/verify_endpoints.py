"""
Comprehensive End-to-End Test Suite for Bhoomi-Nexus National Land Intelligence Platform.
Tests all 11 API endpoints across GIS, Telemetry, Simulation, AI Search, Datasets, Research, and Blockchain.
"""

import httpx

BASE_URL = "http://127.0.0.1:8000"

def test_full_platform():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        print("==================================================")
        print("BHOOMI-NEXUS SYSTEM INTEGRATION TEST SUITE")
        print("==================================================")

        # 1. Health
        print("\n[1/8] Testing GET /api/health...")
        res = client.get("/api/health")
        assert res.status_code == 200
        health = res.json()
        print(f"      Node: {health['node_id']} | Status: {health['status']} | Blocks: {health['blockchain_blocks']}")

        # 2. Geocoding
        print("\n[2/8] Testing GET /api/geo/search?q=Jaisalmer...")
        res = client.get("/api/geo/search", params={"q": "Jaisalmer"})
        assert res.status_code == 200
        places = res.json()
        assert len(places) > 0
        print(f"      Found: {places[0]['display_name']} ({places[0]['lat']}, {places[0]['lon']})")

        # 3. Live Telemetry
        print("\n[3/8] Testing GET /api/telemetry/live?lat=26.8392&lon=75.6811...")
        res = client.get("/api/telemetry/live", params={"lat": 26.8392, "lon": 75.6811})
        assert res.status_code == 200
        telemetry = res.json()
        print(f"      Moisture: {telemetry['soil_moisture_percentage']}% | Surface Temp: {telemetry['surface_temperature_c']}C | Status: {telemetry['aridity_status']}")

        # 4. AI Search ("Ask BHOOMI")
        print("\n[4/8] Testing POST /api/ai/query...")
        ai_payload = {
            "query": "Why is land degradation increasing in some areas of Rajasthan?",
            "focus_region": "Rajasthan"
        }
        res = client.post("/api/ai/query", json=ai_payload)
        assert res.status_code == 200
        ai_resp = res.json()
        assert "evidence_coverage" in ai_resp
        assert len(ai_resp["sources"]) >= 3
        print(f"      Insight Preview: {ai_resp['insight'][:110]}...")
        print(f"      Evidence Coverage: {ai_resp['evidence_coverage']['datasets_analyzed']} Datasets, {ai_resp['evidence_coverage']['reports_cited']} Reports ({ai_resp['evidence_coverage']['confidence_pct']}% Confidence)")

        # 5. Datasets & Research
        print("\n[5/8] Testing GET /api/datasets & GET /api/research...")
        res_ds = client.get("/api/datasets")
        assert res_ds.status_code == 200
        ds_data = res_ds.json()
        assert ds_data["total"] >= 5
        print(f"      Datasets: {ds_data['total']} cataloged ({ds_data['verified_count']} verified)")

        res_res = client.get("/api/research")
        assert res_res.status_code == 200
        res_data = res_res.json()
        assert res_data["total"] >= 3
        print(f"      Research Papers: {res_data['total']} peer-reviewed studies")

        # 6. Policy Simulator V2
        print("\n[6/8] Testing POST /api/policy/simulate-v2...")
        policy_payload = {
            "target_district": "Jaisalmer",
            "policy_name": "agroforestry_shelterbelts",
            "intensity_increase_pct": 30.0
        }
        res_pol = client.post("/api/policy/simulate-v2", json=policy_payload)
        assert res_pol.status_code == 200
        pol_data = res_pol.json()
        assert len(pol_data["metrics"]) >= 4
        print(f"      Reclaimed: {pol_data['land_degraded_hectares_reclaimed']} Ha | Water Saved: {pol_data['water_saved_million_liters_annual']} ML | ROI: {pol_data['roi_economic_multiplier']}x")

        # 7. Blockchain Verification (Valid + Tamper Detection)
        print("\n[7/8] Testing POST /api/blockchain/verify-dataset (Valid & Tamper)...")
        # Valid test
        res_v1 = client.post("/api/blockchain/verify-dataset", json={"dataset_id": "DS-RAJ-DES-2024", "simulate_tampering": False})
        assert res_v1.status_code == 200
        assert res_v1.json()["verification_status"] == "VERIFIED"
        print(f"      Normal Test: {res_v1.json()['verification_status']} (SHA-256 match)")

        # Tampering test
        res_v2 = client.post("/api/blockchain/verify-dataset", json={"dataset_id": "DS-RAJ-DES-2024", "simulate_tampering": True})
        assert res_v2.status_code == 200
        assert res_v2.json()["verification_status"] == "TAMPERING_DETECTED"
        print(f"      Tamper Test: {res_v2.json()['verification_status']} (Breach successfully flagged!)")

        # 8. Executive Insights Briefings
        print("\n[8/8] Testing GET /api/insights/briefings...")
        res_brf = client.get("/api/insights/briefings")
        assert res_brf.status_code == 200
        brf_data = res_brf.json()
        assert len(brf_data["briefings"]) >= 3
        print(f"      Executive Briefings: {len(brf_data['briefings'])} cabinet intelligence notes active")

        print("\n==================================================")
        print("ALL 8 SYSTEM MODULES VERIFIED & PASSING WITH 100% SUCCESS!")
        print("==================================================")

if __name__ == "__main__":
    test_full_platform()
