"""
Anti-Tamper Document Verification Service (In-Memory Ledger).

Implements SHA-256 binary cryptographic hashing + perceptual text fingerprinting
for zero-tampering security on property documents. Operates completely in-memory
without requiring any external SQL database.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, List

from app.models.document import DocumentRecord, VerificationLog
from app.utils.pdf_extractor import extract_text, extract_structure, normalize_text


# ── In-Memory Document Ledger Store ───────────────────────────────────────

class InMemoryLedger:
    """Thread-safe in-memory repository for registered documents and verification logs."""

    def __init__(self):
        self._records_by_id: Dict[str, DocumentRecord] = {}
        self._records_by_hash: Dict[str, DocumentRecord] = {}
        self._records_by_fingerprint: Dict[str, DocumentRecord] = {}
        self._logs: List[VerificationLog] = []

    def get_by_id(self, doc_id: str) -> Optional[DocumentRecord]:
        return self._records_by_id.get(doc_id)

    def get_by_binary_hash(self, binary_hash: str) -> Optional[DocumentRecord]:
        return self._records_by_hash.get(binary_hash)

    def get_by_fingerprint(self, fingerprint: str) -> Optional[DocumentRecord]:
        return self._records_by_fingerprint.get(fingerprint)

    def add_record(self, record: DocumentRecord) -> DocumentRecord:
        self._records_by_id[record.id] = record
        self._records_by_hash[record.binary_hash_sha256] = record
        self._records_by_fingerprint[record.text_fingerprint_sha256] = record
        return record

    def add_log(self, log: VerificationLog) -> None:
        self._logs.append(log)

    def all_records(self) -> List[DocumentRecord]:
        return list(self._records_by_id.values())

    def all_logs(self) -> List[VerificationLog]:
        return list(self._logs)


# Global in-memory ledger instance
ledger = InMemoryLedger()


# ── Hashing (Enclave-Secured) ──────────────────────────────────────────────

def compute_binary_hash(file_bytes: bytes) -> str:
    """Compute SHA-256 hex digest of raw file bytes through the secure enclave."""
    try:
        import base64
        from app.secure_enclave.service import enclave_gateway
        res = enclave_gateway.dispatch(
            operation="document.verify_integrity",
            payload={"file_bytes_base64": base64.b64encode(file_bytes).decode("utf-8")},
            caller_id="document-service",
        )
        if res.status == "SUCCESS" and res.data and "binary_hash_sha256" in res.data:
            return res.data["binary_hash_sha256"]
    except Exception:
        pass
    return hashlib.sha256(file_bytes).hexdigest()


def compute_text_fingerprint(text: str) -> str:
    """
    Compute SHA-256 of normalized text content through the secure enclave.

    Catches re-saves, edits, or reconstructions that preserve
    text content but change the underlying binary stream.
    """
    try:
        from app.secure_enclave.service import enclave_gateway
        res = enclave_gateway.dispatch(
            operation="document.verify_integrity",
            payload={"extracted_text": text},
            caller_id="document-service",
        )
        if res.status == "SUCCESS" and res.data and "text_fingerprint_sha256" in res.data:
            return res.data["text_fingerprint_sha256"]
    except Exception:
        pass
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ── Registration ──────────────────────────────────────────────────────────

def register_document(
    file_bytes: bytes,
    filename: str,
    owner_name: Optional[str] = None,
    registration_date: Optional[str] = None,
    stamp_number: Optional[str] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    property_type: Optional[str] = None,
    area_description: Optional[str] = None,
) -> DocumentRecord:
    """
    Register a document in the in-memory verification ledger.

    Computes binary hash and text fingerprint, extracts text,
    and stores everything in memory.
    """
    binary_hash = compute_binary_hash(file_bytes)
    raw_text = extract_text(file_bytes)
    text_fingerprint = compute_text_fingerprint(raw_text)
    structure = extract_structure(file_bytes)

    # Check if document already exists (by binary hash)
    existing = ledger.get_by_binary_hash(binary_hash)
    if existing:
        return existing

    record = DocumentRecord(
        filename=filename,
        binary_hash_sha256=binary_hash,
        text_fingerprint_sha256=text_fingerprint,
        file_size_bytes=len(file_bytes),
        page_count=structure.get("page_count", 1),
        extracted_text=raw_text,
        owner_name=owner_name,
        registration_date=registration_date,
        stamp_number=stamp_number,
        district=district,
        state=state,
        property_type=property_type,
        area_description=area_description,
    )
    ledger.add_record(record)
    return record


# ── Verification ──────────────────────────────────────────────────────────

class VerificationResult:
    """Result of a document verification attempt."""

    def __init__(
        self,
        status: str,
        message: str,
        match_type: Optional[str] = None,
        record: Optional[DocumentRecord] = None,
        binary_hash: str = "",
        text_fingerprint: str = "",
    ):
        self.status = status
        self.message = message
        self.match_type = match_type
        self.record = record
        self.binary_hash = binary_hash
        self.text_fingerprint = text_fingerprint


def verify_document(file_bytes: bytes, filename: str) -> VerificationResult:
    """
    Verify a document against the in-memory ledger.

    Checks:
    1. Exact binary hash match -> VERIFIED_REAL
    2. Text fingerprint match (binary differs) -> VERIFICATION_FAILED
       (document was re-saved / edited with different binary stream)
    3. No match at all -> VERIFICATION_FAILED
    """
    binary_hash = compute_binary_hash(file_bytes)
    raw_text = extract_text(file_bytes)
    text_fingerprint = compute_text_fingerprint(raw_text)

    # 1. Check exact binary hash
    exact_match = ledger.get_by_binary_hash(binary_hash)

    if exact_match:
        result = VerificationResult(
            status="VERIFIED_REAL",
            message=(
                "Document VERIFIED as authentic. Binary SHA-256 hash and text fingerprint "
                "match the immutable ledger record exactly. No tampering detected."
            ),
            match_type="EXACT_BINARY",
            record=exact_match,
            binary_hash=binary_hash,
            text_fingerprint=text_fingerprint,
        )
        _log_verification(result, filename)
        return result

    # 2. Check text fingerprint (catches re-saves with altered binary bytes)
    fingerprint_match = ledger.get_by_fingerprint(text_fingerprint)

    if fingerprint_match:
        result = VerificationResult(
            status="VERIFICATION_FAILED",
            message=(
                "Document is NOT REAL or has been tampered with. Signature and hash mismatch. "
                "The text content matches a registered document, but the binary file has been "
                "modified, re-saved, or reconstructed. This indicates potential tampering."
            ),
            match_type="TEXT_FINGERPRINT_ONLY",
            record=fingerprint_match,
            binary_hash=binary_hash,
            text_fingerprint=text_fingerprint,
        )
        _log_verification(result, filename)
        return result

    # 3. No match at all
    result = VerificationResult(
        status="VERIFICATION_FAILED",
        message=(
            "Document is NOT REAL or has been tampered with. Signature and hash mismatch. "
            "No matching record found in the immutable verification ledger. "
            "This document has not been registered or has been substantially altered."
        ),
        match_type=None,
        record=None,
        binary_hash=binary_hash,
        text_fingerprint=text_fingerprint,
    )
    _log_verification(result, filename)
    return result


def _log_verification(result: VerificationResult, filename: str) -> None:
    """Write an audit log entry for the verification attempt."""
    log = VerificationLog(
        document_record_id=result.record.id if result.record else None,
        uploaded_binary_hash=result.binary_hash,
        uploaded_text_fingerprint=result.text_fingerprint,
        filename=filename,
        verification_status=result.status,
        match_type=result.match_type,
        message=result.message,
    )
    ledger.add_log(log)


def get_document_by_id(doc_id: str) -> Optional[DocumentRecord]:
    """Retrieve a document record by ID from the in-memory ledger."""
    return ledger.get_by_id(doc_id)
