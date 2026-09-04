"""
In-Memory Models for the Document Verification Ledger.

No external database required — records are held in memory during runtime.
- DocumentRecord: stores registered (known-legitimate) documents with binary hash,
  text fingerprint, and metadata.
- VerificationLog: audit log entry of each verification attempt.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


@dataclass
class DocumentRecord:
    """A registered document in the in-memory verification ledger."""

    filename: str
    binary_hash_sha256: str
    text_fingerprint_sha256: str
    file_size_bytes: int
    extracted_text: str = ""
    page_count: int = 1

    id: str = field(default_factory=_uuid)
    owner_name: Optional[str] = None
    registration_date: Optional[str] = None
    stamp_number: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    property_type: Optional[str] = None
    area_description: Optional[str] = None

    registered_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class VerificationLog:
    """Audit trail entry for a verification attempt."""

    uploaded_binary_hash: str
    uploaded_text_fingerprint: str
    filename: str
    verification_status: str  # VERIFIED_REAL / VERIFICATION_FAILED
    message: str

    id: str = field(default_factory=_uuid)
    document_record_id: Optional[str] = None
    match_type: Optional[str] = None  # EXACT_BINARY / TEXT_FINGERPRINT_ONLY / NONE
    confidence_score: Optional[float] = None
    verified_at: datetime = field(default_factory=_utcnow)
