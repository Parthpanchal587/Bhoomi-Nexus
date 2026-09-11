"""
Pydantic schemas for the Anti-Tamper Document Verification module.

Endpoints served:
  POST /api/v1/documents/upload
  POST /api/v1/documents/verify
"""

from typing import Optional
from pydantic import BaseModel, Field


# ── Upload ────────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    """Returned after a document is registered in the immutable ledger."""
    document_id: str = Field(..., description="Unique ledger record ID")
    filename: str
    binary_hash_sha256: str = Field(..., description="SHA-256 hex digest of raw file bytes")
    text_fingerprint_sha256: str = Field(..., description="SHA-256 of normalized extracted text")
    file_size_bytes: int
    page_count: int
    owner_name: Optional[str] = None
    registration_date: Optional[str] = None
    stamp_number: Optional[str] = None
    status: str = Field(default="REGISTERED", description="Always 'REGISTERED' on successful upload")
    message: str = "Document registered successfully in the immutable verification ledger."


# ── Verify ────────────────────────────────────────────────────────────────

class DocumentVerifyResponse(BaseModel):
    """
    Returned when a document is verified against the ledger.

    status is either:
      - VERIFIED_REAL:       Document matches a registered record exactly.
      - VERIFICATION_FAILED: Document is NOT REAL or has been tampered with.
    """
    status: str = Field(..., description="VERIFIED_REAL or VERIFICATION_FAILED")
    message: str
    filename: str
    uploaded_binary_hash: str
    uploaded_text_fingerprint: str

    # Populated only on VERIFIED_REAL
    matched_document_id: Optional[str] = None
    match_type: Optional[str] = None          # EXACT_BINARY, TEXT_FINGERPRINT_MATCH
    owner_name: Optional[str] = None
    registration_date: Optional[str] = None
    stamp_number: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    property_type: Optional[str] = None
    registered_at: Optional[str] = None
    validity_proof: Optional[str] = None      # Hash chain proof string
