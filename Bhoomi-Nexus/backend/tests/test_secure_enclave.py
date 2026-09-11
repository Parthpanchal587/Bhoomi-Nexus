"""
Comprehensive Security & TEE Architecture Test Suite for Bhoomi-Nexus.

Tests:
1. Provider initialization & security status disclosures
2. Software integrity attestation quotes & tampering detection
3. Secure Secret Vault (AES-256-GCM, HKDF, context-binding, tampering detection)
4. Deny-by-Default Policy Engine (RBAC, unmapped operations, payload bounds, rate limits)
5. Isolated Sandbox (timeouts, execution bounds, environment scrubbing)
6. Authenticated IPC & Anti-Replay protection (HMAC, nonces, timestamp drift)
7. Tamper-Evident Audit Logging (hash-chaining, tamper detection, secret scrubbing)
8. FastAPI Enclave Router endpoints & negative attack vectors
"""

import base64
import os
import secrets
import sys
import time
import unittest
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.secure_enclave.schemas import (
    EnclaveRole,
    IsolationLevel,
    OperationPermission,
    SecureExecutionRequest,
)
from app.secure_enclave.vault import SecureSecretVault, zeroize
from app.secure_enclave.policy import PolicyEngine
from app.secure_enclave.attestation import AttestationService
from app.secure_enclave.audit import TamperEvidentAuditLog, sanitize_audit_metadata
from app.secure_enclave.sandbox import IsolatedSandbox, SandboxTimeoutError
from app.secure_enclave.ipc import SecureIPCChannel
from app.secure_enclave.service import EnclaveService, enclave_gateway


class TestSecureEnclaveProvider(unittest.TestCase):
    """Test core provider functionality and security disclosures."""

    def setUp(self):
        self.gateway = EnclaveService()

    def test_security_status_disclosure(self):
        status = self.gateway.get_security_status()
        self.assertEqual(status.isolation_level, IsolationLevel.SOFTWARE_PROCESS_ISOLATED)
        self.assertFalse(status.hardware_backed)
        self.assertIn("SoftwareSecureExecutionProvider", status.provider_name)
        self.assertTrue(status.audit_chain_valid)
        self.assertGreaterEqual(status.audit_chain_length, 1)

    def test_attestation_report_and_verification(self):
        nonce = secrets.token_hex(16)
        report = self.gateway.get_attestation(nonce=nonce)
        self.assertEqual(report.caller_nonce, nonce)
        self.assertFalse(report.hardware_backed)
        self.assertEqual(report.attestation_type, "SOFTWARE_INTEGRITY_MEASURED")
        self.assertEqual(len(report.measurements.code_hash_sha256), 64)
        self.assertEqual(len(report.measurements.policy_hash_sha256), 64)

        # Verification must succeed for authentic report
        is_valid = self.gateway.attestation.verify_attestation_report(report, expected_nonce=nonce)
        self.assertTrue(is_valid)

        # Verification must fail if nonce or data is tampered with
        is_valid_wrong_nonce = self.gateway.attestation.verify_attestation_report(report, expected_nonce="tampered-nonce")
        self.assertFalse(is_valid_wrong_nonce)


class TestSecureSecretVault(unittest.TestCase):
    """Test cryptographic sealing, unsealing, key derivation, and buffer zeroization."""

    def setUp(self):
        self.vault = SecureSecretVault()

    def test_seal_and_unseal_roundtrip(self):
        secret = "super_sensitive_gemini_api_key_12345"
        context = "service.ai_due_diligence"

        sealed_blob = self.vault.seal(secret, context_binding=context)
        self.assertIsInstance(sealed_blob, str)
        self.assertNotIn(secret, sealed_blob)  # Ensure ciphertext does not leak plaintext

        unsealed_bytes = self.vault.unseal(sealed_blob, expected_context=context)
        self.assertEqual(unsealed_bytes.decode("utf-8"), secret)

    def test_unseal_fails_on_context_mismatch(self):
        secret = "confidential_cadastral_key"
        sealed_blob = self.vault.seal(secret, context_binding="context_A")

        with self.assertRaises(PermissionError):
            self.vault.unseal(sealed_blob, expected_context="context_B")

    def test_unseal_fails_on_ciphertext_tampering(self):
        secret = "confidential_payload"
        sealed_blob = self.vault.seal(secret)

        # Tamper with the base64-encoded envelope
        raw_json = base64.b64decode(sealed_blob.encode()).decode()
        tampered_json = raw_json.replace("AES-256-GCM", "TAMPERED-CIPHER")
        tampered_blob = base64.b64encode(tampered_json.encode()).decode()

        with self.assertRaises(Exception):
            self.vault.unseal(tampered_blob)

    def test_buffer_zeroization(self):
        buf = bytearray(b"highly_secret_key_material_to_wipe")
        self.assertTrue(any(b != 0 for b in buf))
        zeroize(buf)
        self.assertTrue(all(b == 0 for b in buf))


class TestPolicyEngine(unittest.TestCase):
    """Test deny-by-default, RBAC, timeouts, and resource bound enforcement."""

    def setUp(self):
        self.policy = PolicyEngine()

    def test_deny_by_default_unmapped_operation(self):
        res = self.policy.evaluate(
            operation="unregistered.arbitrary_command",
            caller_id="attacker",
            caller_role=EnclaveRole.SYSTEM,
        )
        self.assertEqual(res.verdict, OperationPermission.DENY)
        self.assertIn("not recognized", res.reason)

    def test_permit_authorized_operation(self):
        res = self.policy.evaluate(
            operation="document.verify_integrity",
            caller_id="public_user",
            caller_role=EnclaveRole.UNTRUSTED_CLIENT,
            payload_size_bytes=1024,
        )
        self.assertEqual(res.verdict, OperationPermission.PERMIT)

    def test_deny_insufficient_role(self):
        # crypto.seal_secret requires SYSTEM role
        res = self.policy.evaluate(
            operation="crypto.seal_secret",
            caller_id="regular_user",
            caller_role=EnclaveRole.UNTRUSTED_CLIENT,
        )
        self.assertEqual(res.verdict, OperationPermission.DENY)
        self.assertIn("Insufficient permissions", res.reason)

    def test_deny_excessive_payload_size(self):
        # policy.evaluate_zoning allows up to 256 KB
        res = self.policy.evaluate(
            operation="policy.evaluate_zoning",
            caller_id="caller",
            caller_role=EnclaveRole.UNTRUSTED_CLIENT,
            payload_size_bytes=10 * 1024 * 1024,  # 10 MB payload
        )
        self.assertEqual(res.verdict, OperationPermission.DENY)
        self.assertIn("exceeds limit", res.reason)

    def test_rate_limiting_enforcement(self):
        caller = "rate_limit_test_user"
        op = "document.verify_integrity"  # limit: 120 / min

        # Rapidly exhaust rate limit threshold
        policy_obj = self.policy.get_policy(op)
        limit = policy_obj.rate_limit_per_minute

        for _ in range(limit):
            verdict = self.policy.evaluate(op, caller, EnclaveRole.UNTRUSTED_CLIENT)
            self.assertEqual(verdict.verdict, OperationPermission.PERMIT)

        # The limit + 1 call must be rejected
        blocked = self.policy.evaluate(op, caller, EnclaveRole.UNTRUSTED_CLIENT)
        self.assertEqual(blocked.verdict, OperationPermission.DENY)
        self.assertIn("Rate limit exceeded", blocked.reason)


class TestIsolatedSandbox(unittest.TestCase):
    """Test sandbox execution timeouts and environment scrubbing."""

    def setUp(self):
        self.sandbox = IsolatedSandbox(max_workers=2)

    def tearDown(self):
        self.sandbox.shutdown()

    def test_environment_scrubbing(self):
        os.environ["SUPER_SECRET_HOST_KEY"] = "sk-live-should-never-leak"
        scrubbed = self.sandbox.scrub_environment()
        self.assertNotIn("SUPER_SECRET_HOST_KEY", scrubbed)
        del os.environ["SUPER_SECRET_HOST_KEY"]

    def test_execution_timeout_enforcement(self):
        def slow_infinite_task(payload):
            time.sleep(1.0)
            return "done"

        with self.assertRaises(SandboxTimeoutError):
            self.sandbox.execute_bounded(slow_infinite_task, args=({},), timeout_ms=100)


class TestSecureIPC(unittest.TestCase):
    """Test authenticated IPC, HMAC signatures, and anti-replay protection."""

    def setUp(self):
        self.ipc = SecureIPCChannel()

    def test_message_integrity_roundtrip(self):
        msg = self.ipc.create_message(
            caller_id="service_A",
            caller_role="operator",
            operation="notary.sign_record",
            payload={"khasra": "KHA-7829-RJ"},
        )

        is_valid, err = self.ipc.verify_message(msg)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_replay_attack_prevention(self):
        msg = self.ipc.create_message(
            caller_id="service_A",
            caller_role="operator",
            operation="notary.sign_record",
            payload={"khasra": "KHA-7829-RJ"},
        )

        # First verification succeeds
        is_valid, _ = self.ipc.verify_message(msg)
        self.assertTrue(is_valid)

        # Immediate replay with same nonce MUST be rejected
        is_replay, err = self.ipc.verify_message(msg)
        self.assertFalse(is_replay)
        self.assertIn("Replay attack detected", err)

    def test_ipc_signature_tampering_detection(self):
        msg = self.ipc.create_message(
            caller_id="service_A",
            caller_role="operator",
            operation="notary.sign_record",
            payload={"khasra": "KHA-7829-RJ"},
        )

        # Alter payload
        msg.payload["khasra"] = "MALICIOUS-TAMPERED-PLOT"
        is_valid, err = self.ipc.verify_message(msg)
        self.assertFalse(is_valid)
        self.assertIn("signature mismatch", err)


class TestTamperEvidentAuditLog(unittest.TestCase):
    """Test cryptographic hash chaining and data corruption detection."""

    def setUp(self):
        self.audit = TamperEvidentAuditLog()

    def test_hash_chaining_and_validation(self):
        self.audit.record_event("EVENT_1", "caller1", "user", "op.test", "SUCCESS")
        self.audit.record_event("EVENT_2", "caller2", "user", "op.test", "SUCCESS")
        self.audit.record_event("EVENT_3", "caller3", "user", "op.test", "SUCCESS")

        self.assertEqual(self.audit.total_entries, 4)  # Genesis + 3 events
        is_valid, err = self.audit.validate_chain()
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_tampering_detection_in_audit_trail(self):
        self.audit.record_event("OP_A", "userA", "user", "test", "SUCCESS")
        self.audit.record_event("OP_B", "userB", "user", "test", "SUCCESS")

        # Maliciously modify historic log entry in memory
        self.audit._entries[1].status = "TAMPERED_FAILED"

        is_valid, err = self.audit.validate_chain()
        self.assertFalse(is_valid)
        self.assertIn("Data tampering detected", err)

    def test_secret_scrubbing_in_audit_metadata(self):
        dirty = {
            "api_key": "sk-test-secret-12345",
            "password": "my_super_secret_password",
            "user_id": "usr_987",
            "auth_token": "bearer xyz",
        }
        sanitized = sanitize_audit_metadata(dirty)
        self.assertEqual(sanitized["api_key"], "[REDACTED_SECRET]")
        self.assertEqual(sanitized["password"], "[REDACTED_SECRET]")
        self.assertEqual(sanitized["auth_token"], "[REDACTED_SECRET]")
        self.assertEqual(sanitized["user_id"], "usr_987")


class TestEnclaveAPIEndpoints(unittest.TestCase):
    """Test FastAPI enclave endpoints and negative attack surfaces."""

    def setUp(self):
        self.client = TestClient(app)

    def test_get_status_endpoint(self):
        res = self.client.get("/api/v1/enclave/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["isolation_level"], "SOFTWARE_PROCESS_ISOLATED")
        self.assertFalse(data["hardware_backed"])
        self.assertTrue(data["audit_chain_valid"])

    def test_attestation_endpoint(self):
        nonce = "test-nonce-12345678"
        res = self.client.post("/api/v1/enclave/attest", json={"nonce": nonce})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["caller_nonce"], nonce)
        self.assertIn("signature", data)
        self.assertEqual(data["attestation_type"], "SOFTWARE_INTEGRITY_MEASURED")

    def test_audit_verify_endpoint(self):
        res = self.client.get("/api/v1/enclave/audit/verify")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_valid"])
        self.assertGreaterEqual(data["total_entries"], 1)

    def test_execute_document_verify_through_enclave(self):
        test_bytes = b"Sample property sale deed content for testing"
        payload = {
            "file_bytes_base64": base64.b64encode(test_bytes).decode(),
            "extracted_text": "Sample property sale deed content for testing",
        }
        req = {
            "operation": "document.verify_integrity",
            "payload": payload,
            "caller_id": "test_client",
            "caller_role": "untrusted-client",
        }
        res = self.client.post("/api/v1/enclave/execute", json=req)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("binary_hash_sha256", data["data"])
        self.assertIn("text_fingerprint_sha256", data["data"])

    def test_execute_unauthorized_operation_denied(self):
        # untrusted-client attempting privileged crypto.seal_secret
        req = {
            "operation": "crypto.seal_secret",
            "payload": {"secret_value": "attempted_leak"},
            "caller_id": "malicious_actor",
            "caller_role": "untrusted-client",
        }
        res = self.client.post("/api/v1/enclave/execute", json=req)
        self.assertEqual(res.status_code, 403)

    def test_unauthorized_unseal_rejected(self):
        res = self.client.post(
            "/api/v1/enclave/secrets/unseal",
            json={
                "secret_name": "test_key",
                "sealed_blob": "fake_blob",
                "caller_id": "unauthorized_user",
            },
        )
        self.assertEqual(res.status_code, 403)

    def test_document_upload_size_limit_rejection(self):
        # 11 MB payload exceeding 10 MB limit
        oversized = b"0" * (11 * 1024 * 1024)
        files = {"file": ("oversized.pdf", oversized, "application/pdf")}
        res = self.client.post("/api/v1/documents/upload", files=files)
        self.assertEqual(res.status_code, 413)


if __name__ == "__main__":
    unittest.main()
