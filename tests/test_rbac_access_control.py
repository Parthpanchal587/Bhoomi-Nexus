"""
Bhoomi Nexus — Role-Based Access Control (RBAC) & Secure Access Verification Suite.
Validates:
  1. Authentication for all 5 roles:
     - Government Officer (GOVERNMENT_OFFICER)
     - Policymaker (POLICYMAKER)
     - Researcher (RESEARCHER)
     - Legal / Property Verifier (LEGAL_VERIFIER)
     - System Administrator (ADMIN)
  2. Public / Guest access boundaries
  3. Server-side authorization enforcement on protected mutation endpoints
  4. Permission denial (HTTP 403) on unauthorized role attempts
  5. Authentication requirement (HTTP 401) on unauthenticated access attempts
  6. Admin-only audit log protection
"""

import io
import unittest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Bhoomi-Nexus", "backend"))

from app.main import app
from app.services.auth import Role, Permission, auth_service


class TestBhoomiRBACAccessControl(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    # ─────────────────────────────────────────────────────────────
    # 1. AUTHENTICATION OF ALL 5 MANDATED ROLES
    # ─────────────────────────────────────────────────────────────
    def test_login_all_five_roles(self):
        """Test authentication succeeds for all 5 official roles."""
        role_credentials = [
            ("officer", "OfficerGov#2026!", Role.GOVERNMENT_OFFICER),
            ("policymaker", "PolicyMaker#2026!", Role.POLICYMAKER),
            ("researcher", "Researcher#2026!", Role.RESEARCHER),
            ("verifier", "LegalVerifier#2026!", Role.LEGAL_VERIFIER),
            ("admin", "BhoomiAdmin#2026!", Role.ADMIN),
        ]

        for username, password, expected_role in role_credentials:
            res = self.client.post("/api/v1/auth/login", json={
                "username": username,
                "password": password
            })
            self.assertEqual(res.status_code, 200, f"Login failed for {username}")
            data = res.json()
            self.assertEqual(data["role"], expected_role.value)
            self.assertIn("token", data)
            self.assertIsInstance(data["permissions"], list)
            self.assertGreater(len(data["permissions"]), 0)

    # ─────────────────────────────────────────────────────────────
    # 2. ROLE INTROSPECTION ENDPOINT
    # ─────────────────────────────────────────────────────────────
    def test_roles_and_permissions_introspection(self):
        """Verify /api/v1/auth/roles exposes the 5 system roles and descriptions."""
        res = self.client.get("/api/v1/auth/roles")
        self.assertEqual(res.status_code, 200)
        roles_data = res.json()
        self.assertIn("GOVERNMENT_OFFICER", roles_data)
        self.assertIn("POLICYMAKER", roles_data)
        self.assertIn("RESEARCHER", roles_data)
        self.assertIn("LEGAL_VERIFIER", roles_data)
        self.assertIn("ADMIN", roles_data)
        self.assertIn("GUEST", roles_data)

    # ─────────────────────────────────────────────────────────────
    # 3. GUEST BLOCKED FROM DOCUMENT REGISTRATION (HTTP 401)
    # ─────────────────────────────────────────────────────────────
    def test_guest_cannot_register_documents(self):
        """Unauthenticated guest cannot register official documents into ledger."""
        valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        files = {"file": ("deed.pdf", io.BytesIO(valid_pdf), "application/pdf")}
        res = self.client.post("/api/v1/documents/upload", files=files)
        # Must return 401 Unauthorized
        self.assertEqual(res.status_code, 401)
        self.assertIn("Authentication required", res.json()["detail"])

    # ─────────────────────────────────────────────────────────────
    # 4. ROLE-BASED ACCESS DENIAL (HTTP 403)
    # ─────────────────────────────────────────────────────────────
    def test_unauthorized_role_cannot_register_documents(self):
        """Policymaker and Researcher roles cannot register documents (HTTP 403)."""
        # Login as Policymaker (does NOT have REGISTER_DOCUMENT)
        login_res = self.client.post("/api/v1/auth/login", json={
            "username": "policymaker",
            "password": "PolicyMaker#2026!"
        })
        token = login_res.json()["token"]

        valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        files = {"file": ("deed.pdf", io.BytesIO(valid_pdf), "application/pdf")}
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.post("/api/v1/documents/upload", files=files, headers=headers)
        # Must return 403 Forbidden
        self.assertEqual(res.status_code, 403)
        self.assertIn("Access Denied", res.json()["detail"])

    # ─────────────────────────────────────────────────────────────
    # 5. AUTHORIZED ROLES CAN REGISTER DOCUMENTS (HTTP 200)
    # ─────────────────────────────────────────────────────────────
    def test_authorized_role_can_register_documents(self):
        """Government Officer and Legal Verifier can register documents (HTTP 200)."""
        # Login as Legal Verifier
        login_res = self.client.post("/api/v1/auth/login", json={
            "username": "verifier",
            "password": "LegalVerifier#2026!"
        })
        token = login_res.json()["token"]

        valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        files = {"file": ("title_deed_7829.pdf", io.BytesIO(valid_pdf), "application/pdf")}
        data = {
            "owner_name": "Kishan Lal Jat",
            "registration_date": "2026-04-10",
            "stamp_number": "IN-RJ2026-09A",
            "district": "Jaipur",
            "state": "Rajasthan"
        }
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "REGISTERED")

    # ─────────────────────────────────────────────────────────────
    # 6. ADMIN-ONLY RAW AUDIT LOGS ENDPOINT
    # ─────────────────────────────────────────────────────────────
    def test_raw_audit_logs_protection(self):
        """Only ADMIN role can access raw audit logs; others get HTTP 403."""
        # Test 1: Government Officer denied
        officer_login = self.client.post("/api/v1/auth/login", json={
            "username": "officer",
            "password": "OfficerGov#2026!"
        })
        res_officer = self.client.get("/api/v1/auth/audit-logs", headers={
            "Authorization": f"Bearer {officer_login.json()['token']}"
        })
        self.assertEqual(res_officer.status_code, 403)

        # Test 2: Admin granted
        admin_login = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "BhoomiAdmin#2026!"
        })
        res_admin = self.client.get("/api/v1/auth/audit-logs", headers={
            "Authorization": f"Bearer {admin_login.json()['token']}"
        })
        self.assertEqual(res_admin.status_code, 200)
        self.assertIsInstance(res_admin.json(), list)


if __name__ == "__main__":
    unittest.main()
