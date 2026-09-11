"""
Secure Enclave API Router.

Exposes endpoints for:
- Querying enclave security status and isolation disclosures
- Generating signed software integrity attestation reports
- Authenticated dispatch of policy-governed secure operations
- Tamper-evident audit log validation and inspection
- Sealing and unsealing sensitive secrets via the enclave vault
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.secure_enclave.schemas import (
    AttestationReport,
    AuditEvent,
    ExecutionResult,
    SealSecretRequest,
    SealSecretResponse,
    SecureExecutionRequest,
    SecurityStatus,
    UnsealSecretRequest,
)
from app.secure_enclave.service import enclave_gateway

router = APIRouter(prefix="/api/v1/enclave", tags=["Secure Enclave (TEE Layer)"])


class AttestRequest(BaseModel):
    nonce: str = Field(..., min_length=8, max_length=64, description="Caller-provided freshness nonce")


class AuditVerificationResponse(BaseModel):
    is_valid: bool
    total_entries: int
    latest_entry_hash: str
    error: Optional[str] = None
    recent_events: List[AuditEvent]


@router.get("/status", response_model=SecurityStatus)
def get_enclave_status():
    """
    Get the operational and security status of the enclave layer.
    Discloses isolation level, platform protection mechanism, and audit chain state.
    """
    return enclave_gateway.get_security_status()


@router.post("/attest", response_model=AttestationReport)
def request_attestation(req: AttestRequest):
    """
    Request a cryptographically signed attestation report.
    Binds the caller nonce with live code, configuration, and policy hashes.
    """
    return enclave_gateway.get_attestation(nonce=req.nonce)


@router.post("/execute", response_model=ExecutionResult)
def execute_secure_operation(
    req: SecureExecutionRequest,
    x_enclave_token: Optional[str] = Header(None, alias="X-Enclave-Token"),
):
    """
    Execute an operation within the isolated execution environment.
    Evaluates deny-by-default policy, enforces timeouts, and records an audit event.
    """
    token = req.auth_token or x_enclave_token
    result = enclave_gateway.dispatch(
        operation=req.operation,
        payload=req.payload,
        caller_id=req.caller_id,
        caller_role=req.caller_role,
        auth_token=token,
        request_id=req.request_id,
    )

    if result.status == "POLICY_DENIED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.data.get("reason", "Operation denied by enclave security policy."),
        )

    return result


@router.get("/audit/verify", response_model=AuditVerificationResponse)
def verify_audit_trail(limit: int = Query(20, ge=1, le=100)):
    """
    Verify the cryptographic integrity of the hash-chained audit log.
    Detects any historical data modification, block insertion, or truncation.
    """
    is_valid, err = enclave_gateway.audit_log.validate_chain()
    recent = enclave_gateway.audit_log.get_recent_entries(limit=limit)

    return AuditVerificationResponse(
        is_valid=is_valid,
        total_entries=enclave_gateway.audit_log.total_entries,
        latest_entry_hash=enclave_gateway.audit_log.latest_entry.entry_hash,
        error=err,
        recent_events=recent,
    )


@router.post("/secrets/seal", response_model=SealSecretResponse)
def seal_secret_endpoint(
    req: SealSecretRequest,
    x_enclave_token: Optional[str] = Header(None, alias="X-Enclave-Token"),
):
    """
    Seal a sensitive secret into an authenticated encrypted ciphertext envelope (AES-256-GCM).
    Requires system or operator authorization.
    """
    token = req.auth_token or x_enclave_token
    if token != enclave_gateway.system_token and req.caller_id != "internal-core":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Sealing secrets requires valid enclave system credentials.",
        )

    sealed = enclave_gateway.seal_secret(req.secret_value, req.context_binding)
    import datetime
    return SealSecretResponse(
        secret_name=req.secret_name,
        sealed_blob=sealed,
        key_derivation="HKDF-SHA256",
        algorithm="AES-256-GCM",
        sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


@router.post("/secrets/unseal")
def unseal_secret_endpoint(
    req: UnsealSecretRequest,
    x_enclave_token: Optional[str] = Header(None, alias="X-Enclave-Token"),
):
    """
    Unseal a secret inside the enclave.
    Requires system authorization.
    """
    token = req.auth_token or x_enclave_token
    if token != enclave_gateway.system_token and req.caller_id != "internal-core":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Unsealing secrets requires valid enclave system credentials.",
        )

    try:
        unsealed_bytes = enclave_gateway.unseal_secret(req.sealed_blob, req.context_binding)
        return {
            "secret_name": req.secret_name,
            "unsealed_value": unsealed_bytes.decode("utf-8", errors="replace"),
            "status": "UNSEALED",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to unseal secret: {e}",
        )
