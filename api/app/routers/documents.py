"""
Document Upload & Verification Router.

Anti-Tamper Zero-Tampering Security Module.
Operates with in-memory ledger storage (no external database required).

Endpoints:
  POST /api/v1/documents/upload   — Register a document in the immutable ledger
  POST /api/v1/documents/verify   — Verify a document against the ledger
"""

import os
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.document import DocumentUploadResponse, DocumentVerifyResponse
from app.services.document_verification import register_document, verify_document

router = APIRouter(prefix="/api/v1/documents", tags=["Document Verification (v1)"])


MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB security limit


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="PDF document to register in the verification ledger"),
    owner_name: Optional[str] = Form(None, description="Property owner name"),
    registration_date: Optional[str] = Form(None, description="Document registration date"),
    stamp_number: Optional[str] = Form(None, description="Stamp duty number"),
    district: Optional[str] = Form(None, description="District name"),
    state: Optional[str] = Form(None, description="State name"),
    property_type: Optional[str] = Form(None, description="Property type (e.g., Residential, Agricultural)"),
    area_description: Optional[str] = Form(None, description="Area description or measurement"),
):
    """
    Upload and register a document in the in-memory verification ledger.

    Computes SHA-256 binary hash and text fingerprint, extracts text content,
    and stores the document record with metadata. If the exact document was
    already registered, returns the existing record.
    """
    file_bytes = await file.read()

    # Enforce maximum file size limit (Denial of Service protection)
    if len(file_bytes) > MAX_DOCUMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of 10 MB (received {len(file_bytes)} bytes).",
        )

    # File Security: Enforce '%PDF' Magic Bytes Signature
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File security rejection: Uploaded file does not contain a valid %PDF magic byte header.",
        )

    # Path Traversal and Name Sanitization
    raw_name = file.filename or "uploaded_deed.pdf"
    safe_filename = os.path.basename(raw_name).replace("\x00", "").strip()[:100]
    if not safe_filename.lower().endswith(".pdf"):
        safe_filename += ".pdf"

    # Input text sanitization helper
    def _sanitize(val: Optional[str], max_len: int = 250) -> Optional[str]:
        if not val:
            return None
        clean = val.replace("<", "&lt;").replace(">", "&gt;").replace("\x00", "").strip()
        return clean[:max_len]

    record = register_document(
        file_bytes=file_bytes,
        filename=safe_filename,
        owner_name=_sanitize(owner_name),
        registration_date=_sanitize(registration_date, 50),
        stamp_number=_sanitize(stamp_number, 50),
        district=_sanitize(district, 100),
        state=_sanitize(state, 100),
        property_type=_sanitize(property_type, 100),
        area_description=_sanitize(area_description, 250),
    )

    return DocumentUploadResponse(
        document_id=record.id,
        filename=record.filename,
        binary_hash_sha256=record.binary_hash_sha256,
        text_fingerprint_sha256=record.text_fingerprint_sha256,
        file_size_bytes=record.file_size_bytes,
        page_count=record.page_count,
        owner_name=record.owner_name,
        registration_date=record.registration_date,
        stamp_number=record.stamp_number,
        status="REGISTERED",
        message="Document registered successfully in the verification ledger.",
    )


@router.post("/verify", response_model=DocumentVerifyResponse)
async def verify_document_endpoint(
    file: UploadFile = File(..., description="PDF document to verify against the ledger"),
):
    """
    Verify a document against the verification ledger.

    Computes the document's SHA-256 binary hash and text fingerprint,
    then checks for matches in the in-memory ledger.

    Returns:
    - VERIFIED_REAL: if the document matches a registered record exactly.
    - VERIFICATION_FAILED: if the document is NOT REAL or has been tampered with.
    """
    file_bytes = await file.read()

    # Enforce maximum file size limit (Denial of Service protection)
    if len(file_bytes) > MAX_DOCUMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of 10 MB (received {len(file_bytes)} bytes).",
        )

    # File Security: Enforce '%PDF' Magic Bytes Signature
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File security rejection: Uploaded file does not contain a valid %PDF magic byte header.",
        )

    raw_name = file.filename or "unknown.pdf"
    safe_filename = os.path.basename(raw_name).replace("\x00", "").strip()[:100]

    result = verify_document(file_bytes=file_bytes, filename=safe_filename)

    # Build response
    response = DocumentVerifyResponse(
        status=result.status,
        message=result.message,
        filename=safe_filename,
        uploaded_binary_hash=result.binary_hash,
        uploaded_text_fingerprint=result.text_fingerprint,
        match_type=result.match_type,
    )

    # Populate owner details if verified
    if result.record:
        response.matched_document_id = result.record.id
        response.owner_name = result.record.owner_name
        response.registration_date = result.record.registration_date
        response.stamp_number = result.record.stamp_number
        response.district = result.record.district
        response.state = result.record.state
        response.property_type = result.record.property_type
        response.registered_at = (
            result.record.registered_at.isoformat()
            if result.record.registered_at
            else None
        )
        # Validity proof: hash chain
        if result.status == "VERIFIED_REAL":
            response.validity_proof = (
                f"PROOF::SHA256({result.binary_hash[:16]}...)==LEDGER_RECORD({result.record.id})::MATCH_TYPE({result.match_type})"
            )

    return response
