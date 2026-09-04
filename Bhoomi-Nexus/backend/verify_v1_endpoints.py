"""
Test suite for the 5 new v1 module endpoints.
"""

import httpx
import json

BASE_URL = "http://127.0.0.1:8000"


def test_new_modules():
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        print("=" * 60)
        print("BHOOMI-NEXUS V1 MODULE TEST SUITE")
        print("=" * 60)

        # ── 1. GIS Intelligence ───────────────────────────────────
        print("\n[1/5] Testing POST /api/v1/gis/analyze...")
        gis_payload = {
            "coordinates": [
                [75.7800, 26.9100],
                [75.7850, 26.9100],
                [75.7850, 26.9150],
                [75.7800, 26.9150],
                [75.7800, 26.9100],
            ],
            "check_proximity": True,
        }
        res = client.post("/api/v1/gis/analyze", json=gis_payload)
        assert res.status_code == 200, f"GIS failed: {res.status_code} — {res.text}"
        gis = res.json()
        assert gis["status"] == "ANALYSIS_COMPLETE"
        print(f"      Area: {gis['parcel_metrics']['area_hectares']} ha ({gis['parcel_metrics']['area_acres']} ac)")
        print(f"      Centroid: ({gis['centroid']['latitude']}, {gis['centroid']['longitude']})")
        print(f"      Proximity Alerts: {gis['total_alerts']} | Risk: {gis['risk_summary'][:60]}")

        # Also test with survey_plot_id
        res2 = client.post("/api/v1/gis/analyze", json={"survey_plot_id": "KHA-7829-RJ"})
        assert res2.status_code == 200
        print(f"      Survey Plot Test: OK ({res2.json()['parcel_metrics']['area_hectares']} ha)")

        # ── 2. Policy & Zoning Analytics ──────────────────────────
        print("\n[2/5] Testing POST /api/v1/policy/evaluate...")
        policy_payload = {
            "land_type": "Agricultural",
            "proposed_use": "Residential",
            "area_hectares": 5.0,
            "district": "Jaipur",
            "state": "Rajasthan",
            "location_type": "Peri-Urban",
            "proposed_floors": 4,
            "near_highway": True,
        }
        res = client.post("/api/v1/policy/evaluate", json=policy_payload)
        assert res.status_code == 200, f"Policy failed: {res.status_code} — {res.text}"
        pol = res.json()
        print(f"      Compliance: {pol['overall_compliance']} (Score: {pol['compliance_score']})")
        print(f"      Zoning: {pol['zoning']['conversion_feasibility']} — {pol['zoning']['conversion_type']}")
        print(f"      FAR: Allowed={pol['far_analysis']['max_allowed_far']}, Proposed={pol['far_analysis']['proposed_far']}, Within Limit={pol['far_analysis']['is_within_limit']}")
        print(f"      Restrictions: {len(pol['restriction_flags'])} flags")
        print(f"      Timeline: ~{pol['estimated_approval_timeline_days']} days")

        # ── 3. AI Ask (with inline text) ──────────────────────────
        print("\n[3/5] Testing POST /api/v1/ai/ask...")
        ask_payload = {
            "question": "Is there any mortgage clause in this document?",
            "document_text": (
                "SALE DEED\n\n"
                "This deed of sale is executed on 15th March 2024 by Shri Ramesh Kumar "
                "(hereinafter called the Seller) in favour of Smt. Priya Sharma (hereinafter "
                "called the Buyer).\n\n"
                "Property Description: Plot No. 45, Survey No. 123/A, Village Sanganer, "
                "Tehsil Sanganer, District Jaipur, Rajasthan. Total area: 2.5 hectares "
                "(6.17 acres). Bounded on the North by Shri Mohan Lal's land, South by "
                "Government Road, East by Canal, West by Smt. Geeta Devi's land.\n\n"
                "The property is free from all encumbrances, mortgage, lien, and charges. "
                "The seller declares that no court case or litigation is pending.\n\n"
                "Sale consideration: Rs. 50,00,000 (Fifty Lakhs). Stamp Duty paid: Rs. 3,50,000. "
                "Registration Fee: Rs. 50,000. Sub-Registrar: Sanganer, Jaipur.\n\n"
                "Witnesses: 1. Shri Anil Gupta  2. Shri Vijay Singh\n"
            ),
        }
        res = client.post("/api/v1/ai/ask", json=ask_payload)
        assert res.status_code == 200, f"AI Ask failed: {res.status_code} — {res.text}"
        ask = res.json()
        print(f"      Answer: {ask['answer'][:120]}...")
        print(f"      Confidence: {ask['confidence']}%")
        print(f"      Excerpts: {len(ask['relevant_excerpts'])} relevant passages")

        # ── 4. AI Research (with inline text) ─────────────────────
        print("\n[4/5] Testing POST /api/v1/ai/research...")
        research_payload = {
            "document_text": ask_payload["document_text"],
        }
        res = client.post("/api/v1/ai/research", json=research_payload)
        assert res.status_code == 200, f"AI Research failed: {res.status_code} — {res.text}"
        rsr = res.json()
        print(f"      Risk Score: {rsr['legal_risk_score']}/100 | Clarity: {rsr['clarity_score']}/100")
        print(f"      Chain Status: {rsr['chain_continuity_status']} ({len(rsr['title_chain'])} entries)")
        print(f"      Encumbrances: {len(rsr['encumbrances'])} detected")
        print(f"      Missing Elements: {len(rsr['missing_elements'])} items")
        print(f"      Summary: {rsr['executive_summary'][:120]}...")

        # ── 5. Document Upload & Verify ──────────────────────────
        print("\n[5/5] Testing POST /api/v1/documents/upload & /verify...")

        # Create a simple PDF-like content for testing (we'll use raw bytes)
        # Since we can't easily create a real PDF in this test, we'll test with
        # a small binary payload to verify the endpoint works
        import io
        test_content = b"%PDF-1.4 test document binary content for hashing " + b"x" * 100
        files = {"file": ("test_document.pdf", io.BytesIO(test_content), "application/pdf")}
        data = {
            "owner_name": "Shri Ramesh Kumar",
            "registration_date": "2024-03-15",
            "stamp_number": "RJ-JP-2024-45678",
            "district": "Jaipur",
            "state": "Rajasthan",
            "property_type": "Agricultural",
        }
        res = client.post("/api/v1/documents/upload", files=files, data=data)
        assert res.status_code == 200, f"Upload failed: {res.status_code} — {res.text}"
        upload = res.json()
        print(f"      Upload: {upload['status']} (ID: {upload['document_id'][:12]}...)")
        print(f"      Hash: {upload['binary_hash_sha256'][:24]}...")
        print(f"      Fingerprint: {upload['text_fingerprint_sha256'][:24]}...")

        # Verify the SAME document (should be VERIFIED_REAL)
        files2 = {"file": ("test_document.pdf", io.BytesIO(test_content), "application/pdf")}
        res = client.post("/api/v1/documents/verify", files=files2)
        assert res.status_code == 200, f"Verify failed: {res.status_code} — {res.text}"
        verify = res.json()
        assert verify["status"] == "VERIFIED_REAL", f"Expected VERIFIED_REAL, got {verify['status']}"
        print(f"      Verify (same): {verify['status']} [OK] - {verify['match_type']}")
        print(f"      Owner: {verify['owner_name']} | Stamp: {verify['stamp_number']}")

        # Verify a DIFFERENT document (should be VERIFICATION_FAILED)
        tampered_content = b"%PDF-1.4 TAMPERED document with altered content " + b"y" * 100
        files3 = {"file": ("tampered.pdf", io.BytesIO(tampered_content), "application/pdf")}
        res = client.post("/api/v1/documents/verify", files=files3)
        assert res.status_code == 200, f"Tamper verify failed: {res.status_code} - {res.text}"
        tamper = res.json()
        assert tamper["status"] == "VERIFICATION_FAILED", f"Expected VERIFICATION_FAILED, got {tamper['status']}"
        print(f"      Verify (tampered): {tamper['status']} [OK] - Tampering detected!")

        print("\n" + "=" * 60)
        print("ALL 5 NEW V1 MODULES VERIFIED & PASSING WITH 100% SUCCESS!")
        print("=" * 60)


if __name__ == "__main__":
    test_new_modules()
