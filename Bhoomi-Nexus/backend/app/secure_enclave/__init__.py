"""
BHOOMI-NEXUS Secure Enclave Package.

Provides a Trusted Execution Environment (TEE)-inspired secure isolation layer:
- SecureExecutionProvider & SoftwareSecureExecutionProvider
- EnclaveService gateway
- SecureSecretVault (AES-256-GCM + Windows DPAPI envelope sealing)
- PolicyEngine (deny-by-default versioned policies)
- AttestationService (software integrity measurements & signed quotes)
- TamperEvidentAuditLog (cryptographic SHA-256 hash-chained audit trail)
- IsolatedSandbox (process isolation, timeout enforcement & memory ceilings)
- SecureIPCChannel (HMAC-authenticated anti-replay message channel)
"""

from app.secure_enclave.schemas import (
    AttestationReport,
    AuditEvent,
    EnclaveRole,
    ExecutionResult,
    IsolationLevel,
    MeasurementVector,
    OperationPermission,
    OperationPolicy,
    PolicyEvaluationResult,
    SecureExecutionRequest,
    SecurityStatus,
)
from app.secure_enclave.provider import (
    SecureExecutionProvider,
    SoftwareSecureExecutionProvider,
)
from app.secure_enclave.vault import SecureSecretVault
from app.secure_enclave.policy import PolicyEngine
from app.secure_enclave.attestation import AttestationService
from app.secure_enclave.audit import TamperEvidentAuditLog
from app.secure_enclave.sandbox import IsolatedSandbox
from app.secure_enclave.ipc import SecureIPCChannel, IPCMessage
from app.secure_enclave.service import EnclaveService, enclave_gateway

__all__ = [
    "SecureExecutionProvider",
    "SoftwareSecureExecutionProvider",
    "EnclaveService",
    "enclave_gateway",
    "SecureSecretVault",
    "PolicyEngine",
    "AttestationService",
    "TamperEvidentAuditLog",
    "IsolatedSandbox",
    "SecureIPCChannel",
    "IPCMessage",
    "SecurityStatus",
    "AttestationReport",
    "MeasurementVector",
    "ExecutionResult",
    "SecureExecutionRequest",
    "OperationPolicy",
    "PolicyEvaluationResult",
    "EnclaveRole",
    "IsolationLevel",
    "OperationPermission",
]
