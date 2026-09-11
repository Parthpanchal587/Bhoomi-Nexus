"""
Deny-by-Default Security Policy Engine.

Enforces:
1. Versioned declarative operation policies
2. Role-Based Access Control (RBAC)
3. Maximum execution timeout limits
4. Input payload size limits
5. Resource and capability constraints (network, filesystem)
6. Deny-by-default verdict for all unmapped or unauthorized operations
"""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict

from app.secure_enclave.schemas import (
    EnclaveRole,
    OperationPermission,
    OperationPolicy,
    PolicyEvaluationResult,
)


# ── Built-in System Security Policies (Version 1.0) ────────────────────────

DEFAULT_POLICIES: Dict[str, OperationPolicy] = {
    # 1. Cryptographic Document Verification & Fingerprinting
    "document.verify_integrity": OperationPolicy(
        operation="document.verify_integrity",
        allowed=True,
        required_role=EnclaveRole.UNTRUSTED_CLIENT,
        allow_network=False,
        allow_filesystem="NONE",
        max_execution_time_ms=8000,
        max_payload_bytes=10 * 1024 * 1024,  # 10 MB
        rate_limit_per_minute=120,
        requires_attestation=False,
    ),

    # 2. Document PDF Text & Structure Extraction
    "document.parse_and_extract": OperationPolicy(
        operation="document.parse_and_extract",
        allowed=True,
        required_role=EnclaveRole.UNTRUSTED_CLIENT,
        allow_network=False,
        allow_filesystem="NONE",
        max_execution_time_ms=6000,
        max_payload_bytes=10 * 1024 * 1024,  # 10 MB
        rate_limit_per_minute=60,
        requires_attestation=False,
    ),

    # 3. Notary Blockchain Signing & Block Notarization
    "notary.sign_record": OperationPolicy(
        operation="notary.sign_record",
        allowed=True,
        required_role=EnclaveRole.OPERATOR,
        allow_network=False,
        allow_filesystem="NONE",
        max_execution_time_ms=3000,
        max_payload_bytes=512 * 1024,  # 512 KB
        rate_limit_per_minute=100,
        requires_attestation=True,
    ),

    # 4. Policy & Zoning Statutory Evaluation
    "policy.evaluate_zoning": OperationPolicy(
        operation="policy.evaluate_zoning",
        allowed=True,
        required_role=EnclaveRole.UNTRUSTED_CLIENT,
        allow_network=False,
        allow_filesystem="NONE",
        max_execution_time_ms=4000,
        max_payload_bytes=256 * 1024,  # 256 KB
        rate_limit_per_minute=120,
        requires_attestation=False,
    ),

    # 5. Autonomous Legal Title Risk Analysis
    "ai.analyze_title_risk": OperationPolicy(
        operation="ai.analyze_title_risk",
        allowed=True,
        required_role=EnclaveRole.UNTRUSTED_CLIENT,
        allow_network=False,
        allow_filesystem="NONE",
        max_execution_time_ms=8000,
        max_payload_bytes=1 * 1024 * 1024,  # 1 MB
        rate_limit_per_minute=60,
        requires_attestation=False,
    ),

    # 6. Secret Vault Sealing
    "crypto.seal_secret": OperationPolicy(
        operation="crypto.seal_secret",
        allowed=True,
        required_role=EnclaveRole.SYSTEM,
        allow_network=False,
        allow_filesystem="NONE",
        max_execution_time_ms=2000,
        max_payload_bytes=64 * 1024,  # 64 KB
        rate_limit_per_minute=30,
        requires_attestation=True,
    ),

    # 7. Secret Vault Unsealing
    "crypto.unseal_secret": OperationPolicy(
        operation="crypto.unseal_secret",
        allowed=True,
        required_role=EnclaveRole.SYSTEM,
        allow_network=False,
        allow_filesystem="NONE",
        max_execution_time_ms=2000,
        max_payload_bytes=64 * 1024,  # 64 KB
        rate_limit_per_minute=30,
        requires_attestation=True,
    ),

    # 8. Integrity Attestation Quote Generation
    "enclave.attest": OperationPolicy(
        operation="enclave.attest",
        allowed=True,
        required_role=EnclaveRole.UNTRUSTED_CLIENT,
        allow_network=False,
        allow_filesystem="NONE",
        max_execution_time_ms=3000,
        max_payload_bytes=16 * 1024,  # 16 KB
        rate_limit_per_minute=60,
        requires_attestation=False,
    ),
}


class PolicyEngine:
    """
    Evaluates execution requests against versioned security policies.
    Guarantees deny-by-default behavior.
    """

    POLICY_VERSION = "2026.1-TEE-POLICY"

    # Hierarchy: SYSTEM > OPERATOR > AUDITOR > UNTRUSTED_CLIENT
    ROLE_HIERARCHY = {
        EnclaveRole.SYSTEM: 4,
        EnclaveRole.OPERATOR: 3,
        EnclaveRole.AUDITOR: 2,
        EnclaveRole.UNTRUSTED_CLIENT: 1,
    }

    def __init__(self, custom_policies: Optional[Dict[str, OperationPolicy]] = None) -> None:
        self._policies: Dict[str, OperationPolicy] = dict(DEFAULT_POLICIES)
        if custom_policies:
            self._policies.update(custom_policies)
        self._rate_trackers: Dict[str, list] = defaultdict(list)

    @property
    def version(self) -> str:
        return self.POLICY_VERSION

    def get_policy(self, operation: str) -> Optional[OperationPolicy]:
        return self._policies.get(operation)

    def evaluate(
        self,
        operation: str,
        caller_id: str,
        caller_role: EnclaveRole,
        payload_size_bytes: int = 0,
    ) -> PolicyEvaluationResult:
        """
        Evaluate operation permission.
        Returns PERMIT or DENY with an explicit reason.
        """
        policy = self._policies.get(operation)

        # 1. Deny unknown operations immediately
        if not policy:
            return PolicyEvaluationResult(
                verdict=OperationPermission.DENY,
                operation=operation,
                caller_id=caller_id,
                caller_role=caller_role,
                reason=f"Operation '{operation}' is not recognized or permitted by policy.",
                max_execution_time_ms=0,
                max_payload_bytes=0,
            )

        # 2. Check if explicitly disabled
        if not policy.allowed:
            return PolicyEvaluationResult(
                verdict=OperationPermission.DENY,
                operation=operation,
                caller_id=caller_id,
                caller_role=caller_role,
                reason=f"Operation '{operation}' is explicitly disabled in policy {self.POLICY_VERSION}.",
                max_execution_time_ms=0,
                max_payload_bytes=0,
            )

        # 3. Check RBAC role authorization
        caller_level = self.ROLE_HIERARCHY.get(caller_role, 0)
        required_level = self.ROLE_HIERARCHY.get(policy.required_role, 99)

        if caller_level < required_level:
            return PolicyEvaluationResult(
                verdict=OperationPermission.DENY,
                operation=operation,
                caller_id=caller_id,
                caller_role=caller_role,
                reason=(
                    f"Insufficient permissions for '{operation}'. "
                    f"Required: '{policy.required_role.value}', Caller: '{caller_role.value}'."
                ),
                max_execution_time_ms=policy.max_execution_time_ms,
                max_payload_bytes=policy.max_payload_bytes,
            )

        # 4. Check payload size constraints
        if payload_size_bytes > policy.max_payload_bytes:
            return PolicyEvaluationResult(
                verdict=OperationPermission.DENY,
                operation=operation,
                caller_id=caller_id,
                caller_role=caller_role,
                reason=(
                    f"Payload size ({payload_size_bytes} bytes) exceeds limit "
                    f"({policy.max_payload_bytes} bytes) for operation '{operation}'."
                ),
                max_execution_time_ms=policy.max_execution_time_ms,
                max_payload_bytes=policy.max_payload_bytes,
            )

        # 5. Check rate limits
        now = time.time()
        rate_key = f"{caller_id}:{operation}"
        recent_calls = [t for t in self._rate_trackers[rate_key] if now - t < 60.0]
        self._rate_trackers[rate_key] = recent_calls

        if len(recent_calls) >= policy.rate_limit_per_minute:
            return PolicyEvaluationResult(
                verdict=OperationPermission.DENY,
                operation=operation,
                caller_id=caller_id,
                caller_role=caller_role,
                reason=f"Rate limit exceeded ({policy.rate_limit_per_minute} calls/minute) for '{operation}'.",
                max_execution_time_ms=policy.max_execution_time_ms,
                max_payload_bytes=policy.max_payload_bytes,
            )

        self._rate_trackers[rate_key].append(now)

        # All checks passed
        return PolicyEvaluationResult(
            verdict=OperationPermission.PERMIT,
            operation=operation,
            caller_id=caller_id,
            caller_role=caller_role,
            reason="Authorized by security policy.",
            max_execution_time_ms=policy.max_execution_time_ms,
            max_payload_bytes=policy.max_payload_bytes,
        )
