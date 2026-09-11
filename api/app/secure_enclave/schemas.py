"""
Secure Enclave Data Transfer Schemas.

Strictly typed Pydantic models for authenticated IPC, attestation quotes,
policy definitions, audit log entries, and secure execution requests/responses.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IsolationLevel(str, Enum):
    """Execution isolation level classifications."""
    NONE = "NONE"
    SOFTWARE_PROCESS_ISOLATED = "SOFTWARE_PROCESS_ISOLATED"
    HARDWARE_BACKED_TEE = "HARDWARE_BACKED_TEE"


class EnclaveRole(str, Enum):
    """Enclave caller roles for Role-Based Access Control."""
    SYSTEM = "system"
    OPERATOR = "operator"
    AUDITOR = "auditor"
    UNTRUSTED_CLIENT = "untrusted-client"


class OperationPermission(str, Enum):
    """Security policy permission verdict."""
    PERMIT = "PERMIT"
    DENY = "DENY"


# ── Status & Attestation Schemas ──────────────────────────────────────────

class SecurityStatus(BaseModel):
    """Publicly disclosable enclave security status."""
    provider_name: str
    provider_version: str
    isolation_level: IsolationLevel
    hardware_backed: bool = False
    hardware_technology: Optional[str] = None
    platform: str
    os_protection_mechanism: str
    initialized_at: str
    uptime_seconds: float
    total_operations_executed: int
    audit_chain_length: int
    audit_chain_valid: bool
    policy_version: str


class MeasurementVector(BaseModel):
    """Software integrity measurement vector."""
    application_version: str
    code_hash_sha256: str
    config_hash_sha256: str
    policy_hash_sha256: str
    runtime_environment_hash: str


class AttestationReport(BaseModel):
    """
    Cryptographic attestation report.
    
    Clearly states whether it is hardware-backed or software-measured.
    Never misrepresents software isolation as a hardware TEE.
    """
    attestation_id: str
    timestamp: str
    caller_nonce: str
    provider: str
    hardware_backed: bool = False
    attestation_type: str = "SOFTWARE_INTEGRITY_MEASURED"
    measurements: MeasurementVector
    enclave_public_key_fingerprint: str
    signature_algorithm: str
    signature: str
    attestation_statement: str


# ── Policy Schemas ────────────────────────────────────────────────────────

class OperationPolicy(BaseModel):
    """Explicit, versioned security policy for an individual operation."""
    operation: str
    allowed: bool = True
    required_role: EnclaveRole = EnclaveRole.SYSTEM
    allow_network: bool = False
    allow_filesystem: str = "NONE"  # "NONE", "READONLY", "RESTRICTED"
    max_execution_time_ms: int = 5000
    max_payload_bytes: int = 10 * 1024 * 1024  # 10 MB default ceiling
    rate_limit_per_minute: int = 60
    requires_attestation: bool = False


class PolicyEvaluationResult(BaseModel):
    """Verdict of a policy check."""
    verdict: OperationPermission
    operation: str
    caller_id: str
    caller_role: EnclaveRole
    reason: str
    max_execution_time_ms: int
    max_payload_bytes: int


# ── Execution Schemas ─────────────────────────────────────────────────────

class SecureExecutionRequest(BaseModel):
    """Request payload submitted to the secure execution gateway."""
    operation: str = Field(..., description="Target operation name (e.g. document.verify_integrity)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Operation input data")
    caller_id: str = Field(..., description="Unique caller or service identity")
    caller_role: EnclaveRole = Field(default=EnclaveRole.UNTRUSTED_CLIENT, description="Caller RBAC role")
    auth_token: Optional[str] = Field(None, description="Optional bearer or HMAC token for role verification")
    request_id: Optional[str] = Field(None, description="Optional caller correlation ID")


class ExecutionResult(BaseModel):
    """Validated, signed result returned from the isolated execution environment."""
    request_id: str
    operation: str
    status: str  # "SUCCESS", "POLICY_DENIED", "ERROR", "TIMEOUT"
    data: Optional[Dict[str, Any]] = None
    execution_time_ms: float
    isolation_level: IsolationLevel
    hardware_backed: bool = False
    audit_entry_id: Optional[str] = None
    output_signature: str
    timestamp: str


# ── Secret Sealing Schemas ────────────────────────────────────────────────

class SealSecretRequest(BaseModel):
    """Request to seal a plaintext secret inside the vault."""
    secret_name: str = Field(..., description="Unique secret descriptor")
    secret_value: str = Field(..., description="Plaintext secret value")
    context_binding: Optional[str] = Field(None, description="Cryptographic context string bound to the ciphertext")
    caller_id: str = Field(..., description="Caller identity")
    auth_token: Optional[str] = Field(None, description="Enclave authorization token")


class SealSecretResponse(BaseModel):
    """Response containing the sealed ciphertext."""
    secret_name: str
    sealed_blob: str
    key_derivation: str
    algorithm: str
    sealed_at: str


class UnsealSecretRequest(BaseModel):
    """Request to unseal a secret inside the enclave for authorized execution."""
    secret_name: str
    sealed_blob: str
    context_binding: Optional[str] = None
    caller_id: str
    auth_token: Optional[str] = None


# ── Audit Log Schemas ─────────────────────────────────────────────────────

class AuditEvent(BaseModel):
    """Tamper-evident audit trail entry."""
    entry_id: str
    sequence_number: int
    timestamp: str
    previous_hash: str
    event_type: str
    caller_id: str
    caller_role: str
    operation: str
    status: str
    execution_time_ms: Optional[float] = None
    entry_hash: str
