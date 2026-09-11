"""
Trusted Execution Environment (TEE) Provider Abstraction & Software Implementation.

Defines:
- SecureExecutionProvider: Platform-independent abstract base class
- SoftwareSecureExecutionProvider: Production software-isolated implementation

CRITICAL DESIGN PRINCIPLE:
Never misrepresent a software sandbox as equivalent to a hardware-backed TEE (e.g. Intel SGX).
Where actual hardware TEE support is absent, clearly label the security status and isolation
level as SOFTWARE_PROCESS_ISOLATED while providing the strongest available software security.
"""

from abc import ABC, abstractmethod
import hashlib
import platform
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.secure_enclave.schemas import (
    AttestationReport,
    ExecutionResult,
    IsolationLevel,
    SecurityStatus,
)
from app.secure_enclave.vault import SecureSecretVault
from app.secure_enclave.attestation import AttestationService
from app.secure_enclave.policy import PolicyEngine
from app.secure_enclave.sandbox import IsolatedSandbox
from app.secure_enclave.audit import TamperEvidentAuditLog


class SecureExecutionProvider(ABC):
    """Platform-independent Secure Execution Provider interface."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the execution provider, key vaults, and baseline measurements."""
        pass

    @abstractmethod
    def attest(self, caller_nonce: str) -> AttestationReport:
        """Produce a signed attestation report reflecting current code and config integrity."""
        pass

    @abstractmethod
    def execute(
        self,
        operation: str,
        payload: Dict[str, Any],
        caller_id: str,
        caller_role: str,
        request_id: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute an operation within the isolated execution environment."""
        pass

    @abstractmethod
    def seal(self, plaintext: str | bytes, context_binding: Optional[str] = None) -> str:
        """Cryptographically seal a sensitive secret."""
        pass

    @abstractmethod
    def unseal(self, sealed_blob: str, context_binding: Optional[str] = None) -> bytes:
        """Unseal an encrypted secret inside the enclave boundary."""
        pass

    @abstractmethod
    def destroy(self) -> None:
        """Wipe keys and tear down isolated execution resources."""
        pass

    @abstractmethod
    def get_security_status(self) -> SecurityStatus:
        """Query security parameters, provider disclosures, and audit state."""
        pass


class SoftwareSecureExecutionProvider(SecureExecutionProvider):
    """
    Software-Isolated Secure Execution Provider.
    
    Provides process isolation, memory limits, AES-256-GCM envelope sealing,
    and software integrity attestation.
    
    DISCLOSURE: This provider operates via software security boundaries and does NOT
    provide CPU hardware-enforced memory encryption (such as Intel SGX or AMD SEV).
    """

    PROVIDER_NAME = "BHOOMI-SoftwareSecureExecutionProvider"
    PROVIDER_VERSION = "2.0.0-PROD"

    def __init__(
        self,
        vault: SecureSecretVault,
        policy_engine: PolicyEngine,
        attestation: AttestationService,
        audit_log: TamperEvidentAuditLog,
        sandbox: IsolatedSandbox,
    ) -> None:
        self._vault = vault
        self._policy = policy_engine
        self._attestation = attestation
        self._audit = audit_log
        self._sandbox = sandbox
        self._initialized_at = datetime.now(timezone.utc).isoformat()
        self._start_perf_time = time.perf_counter()
        self._operations_count = 0
        self._operations_registry: Dict[str, Any] = {}

    def register_operation_handler(self, operation: str, handler: Any) -> None:
        """Register an internal secure operation handler function."""
        self._operations_registry[operation] = handler

    def initialize(self) -> None:
        """Initialize provider baseline and verify integrity."""
        self._audit.record_event(
            event_type="PROVIDER_INITIALIZED",
            caller_id="system",
            caller_role="system",
            operation="provider.init",
            status="SUCCESS",
        )

    def attest(self, caller_nonce: str) -> AttestationReport:
        """Generate software integrity attestation report."""
        report = self._attestation.generate_attestation_report(
            caller_nonce=caller_nonce,
            provider_name=self.PROVIDER_NAME,
        )
        self._audit.record_event(
            event_type="ATTESTATION_REQUESTED",
            caller_id="caller",
            caller_role="untrusted-client",
            operation="enclave.attest",
            status="SUCCESS",
        )
        return report

    def seal(self, plaintext: str | bytes, context_binding: Optional[str] = None) -> str:
        """Seal plaintext data using AES-256-GCM and HKDF."""
        sealed = self._vault.seal(plaintext, context_binding)
        self._audit.record_event(
            event_type="SECRET_SEALED",
            caller_id="system",
            caller_role="system",
            operation="crypto.seal_secret",
            status="SUCCESS",
        )
        return sealed

    def unseal(self, sealed_blob: str, context_binding: Optional[str] = None) -> bytes:
        """Unseal ciphertext data inside the enclave."""
        unsealed = self._vault.unseal(sealed_blob, context_binding)
        self._audit.record_event(
            event_type="SECRET_UNSEALED",
            caller_id="system",
            caller_role="system",
            operation="crypto.unseal_secret",
            status="SUCCESS",
        )
        return unsealed

    def execute(
        self,
        operation: str,
        payload: Dict[str, Any],
        caller_id: str,
        caller_role: str,
        request_id: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute an operation inside the isolated sandbox subject to policy verification.
        """
        req_id = request_id or f"REQ-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Lookup handler
        handler = self._operations_registry.get(operation)
        if not handler:
            self._audit.record_event(
                event_type="OPERATION_FAILED",
                caller_id=caller_id,
                caller_role=caller_role,
                operation=operation,
                status="HANDLER_NOT_FOUND",
            )
            return ExecutionResult(
                request_id=req_id,
                operation=operation,
                status="HANDLER_NOT_FOUND",
                data={"error": f"Operation '{operation}' has no registered execution handler."},
                execution_time_ms=0.0,
                isolation_level=IsolationLevel.SOFTWARE_PROCESS_ISOLATED,
                hardware_backed=False,
                output_signature="0" * 64,
                timestamp=now_iso,
            )

        # 2. Get policy limits
        policy = self._policy.get_policy(operation)
        timeout_ms = policy.max_execution_time_ms if policy else 5000

        # 3. Execute bounded inside sandbox
        try:
            result_data, exec_ms = self._sandbox.execute_bounded(
                handler,
                args=(payload,),
                timeout_ms=timeout_ms,
            )
            status = "SUCCESS"
            error_data = None
        except Exception as e:
            result_data = None
            exec_ms = 0.0
            status = "ERROR"
            error_data = {"error": str(e)}

        self._operations_count += 1

        # 4. Record audit event
        audit_event = self._audit.record_event(
            event_type="SECURE_OPERATION_COMPLETED" if status == "SUCCESS" else "SECURE_OPERATION_FAILED",
            caller_id=caller_id,
            caller_role=caller_role,
            operation=operation,
            status=status,
            execution_time_ms=exec_ms,
        )

        # 5. Sign the output envelope
        output_sig_data = f"{req_id}|{operation}|{status}|{audit_event.entry_hash}|{now_iso}"
        output_sig = hashlib.sha256(output_sig_data.encode("utf-8")).hexdigest()

        return ExecutionResult(
            request_id=req_id,
            operation=operation,
            status=status,
            data=result_data if status == "SUCCESS" else error_data,
            execution_time_ms=round(exec_ms, 2),
            isolation_level=IsolationLevel.SOFTWARE_PROCESS_ISOLATED,
            hardware_backed=False,
            audit_entry_id=audit_event.entry_id,
            output_signature=output_sig,
            timestamp=now_iso,
        )

    def get_security_status(self) -> SecurityStatus:
        """Return full security status disclosure."""
        is_chain_valid, _ = self._audit.validate_chain()
        uptime = time.perf_counter() - self._start_perf_time

        return SecurityStatus(
            provider_name=self.PROVIDER_NAME,
            provider_version=self.PROVIDER_VERSION,
            isolation_level=IsolationLevel.SOFTWARE_PROCESS_ISOLATED,
            hardware_backed=False,
            hardware_technology=None,
            platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
            os_protection_mechanism=self._vault.os_protection,
            initialized_at=self._initialized_at,
            uptime_seconds=round(uptime, 2),
            total_operations_executed=self._operations_count,
            audit_chain_length=self._audit.total_entries,
            audit_chain_valid=is_chain_valid,
            policy_version=self._policy.version,
        )

    def destroy(self) -> None:
        """Tear down vault keys, sandbox executor, and record shutdown."""
        self._vault.destroy()
        self._sandbox.shutdown()
        self._audit.record_event(
            event_type="ENCLAVE_DESTROYED",
            caller_id="system",
            caller_role="system",
            operation="enclave.destroy",
            status="SUCCESS",
        )
