"""
Tamper-Evident Security Audit Log.

Implements a cryptographically hash-chained audit trail for all sensitive enclave operations.
Guarantees:
1. Each audit log entry is chained via SHA-256 to its predecessor.
2. The chain can be audited on-demand via validate_chain().
3. Never logs secret values, passwords, private keys, API keys, or raw PII.
4. Includes caller IDs, request timestamps, operation names, and status codes.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.secure_enclave.schemas import AuditEvent


# Patterns to scrub from any auxiliary audit metadata
SCRUB_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer|private[_-]?key|auth)"),
]


def sanitize_audit_metadata(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Ensure no credentials or sensitive payloads enter the audit log."""
    if not data:
        return {}
    sanitized = {}
    for k, v in data.items():
        if any(pat.search(k) for pat in SCRUB_PATTERNS):
            sanitized[k] = "[REDACTED_SECRET]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_audit_metadata(v)
        elif isinstance(v, (str, int, float, bool)):
            sanitized[k] = v
        else:
            sanitized[k] = str(type(v).__name__)
    return sanitized


class TamperEvidentAuditLog:
    """Hash-chained, tamper-evident audit repository."""

    GENESIS_PREV_HASH = "0" * 64

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self._entries: List[AuditEvent] = []
        self._persist_path = persist_path
        self._initialize_genesis()

    def _initialize_genesis(self) -> None:
        """Create genesis audit event."""
        now_iso = datetime.now(timezone.utc).isoformat()
        genesis_data = f"0|{now_iso}|ENCLAVE_INITIALIZED|system|system|enclave.init|SUCCESS|{self.GENESIS_PREV_HASH}"
        genesis_hash = hashlib.sha256(genesis_data.encode("utf-8")).hexdigest()

        genesis_event = AuditEvent(
            entry_id="AUDIT-0000-GENESIS",
            sequence_number=0,
            timestamp=now_iso,
            previous_hash=self.GENESIS_PREV_HASH,
            event_type="ENCLAVE_INITIALIZED",
            caller_id="system",
            caller_role="system",
            operation="enclave.init",
            status="SUCCESS",
            execution_time_ms=0.0,
            entry_hash=genesis_hash,
        )
        self._entries.append(genesis_event)

    @property
    def latest_entry(self) -> AuditEvent:
        return self._entries[-1]

    @property
    def total_entries(self) -> int:
        return len(self._entries)

    def record_event(
        self,
        event_type: str,
        caller_id: str,
        caller_role: str,
        operation: str,
        status: str,
        execution_time_ms: Optional[float] = None,
    ) -> AuditEvent:
        """Append an event to the cryptographically linked audit chain."""
        seq = len(self._entries)
        now_iso = datetime.now(timezone.utc).isoformat()
        prev_hash = self.latest_entry.entry_hash
        entry_id = f"AUDIT-{seq:06d}"

        # Hash computation binding all fields
        entry_string = (
            f"{seq}|{now_iso}|{event_type}|{caller_id}|{caller_role}|"
            f"{operation}|{status}|{execution_time_ms or 0.0:.2f}|{prev_hash}"
        )
        entry_hash = hashlib.sha256(entry_string.encode("utf-8")).hexdigest()

        event = AuditEvent(
            entry_id=entry_id,
            sequence_number=seq,
            timestamp=now_iso,
            previous_hash=prev_hash,
            event_type=event_type,
            caller_id=caller_id,
            caller_role=caller_role,
            operation=operation,
            status=status,
            execution_time_ms=execution_time_ms,
            entry_hash=entry_hash,
        )
        self._entries.append(event)

        # Optional append-only file persistence
        if self._persist_path:
            try:
                self._persist_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self._persist_path, "a", encoding="utf-8") as f:
                    f.write(event.model_dump_json() + "\n")
            except Exception:
                pass

        return event

    def validate_chain(self) -> Tuple[bool, Optional[str]]:
        """
        Verify cryptographic integrity of the entire audit chain.
        Returns (True, None) if valid, or (False, failure_reason) if tampered with.
        """
        if not self._entries:
            return False, "Audit log is empty"

        # Check genesis
        if self._entries[0].previous_hash != self.GENESIS_PREV_HASH:
            return False, "Genesis block previous_hash is corrupted"

        for i in range(1, len(self._entries)):
            current = self._entries[i]
            prev = self._entries[i - 1]

            # 1. Verify link to previous entry
            if current.previous_hash != prev.entry_hash:
                return False, (
                    f"Hash link broken at sequence {current.sequence_number}: "
                    f"previous_hash does not match prior entry_hash."
                )

            # 2. Recompute current hash to detect in-place data tampering
            expected_string = (
                f"{current.sequence_number}|{current.timestamp}|{current.event_type}|"
                f"{current.caller_id}|{current.caller_role}|{current.operation}|"
                f"{current.status}|{current.execution_time_ms or 0.0:.2f}|{current.previous_hash}"
            )
            recomputed = hashlib.sha256(expected_string.encode("utf-8")).hexdigest()
            if current.entry_hash != recomputed:
                return False, (
                    f"Data tampering detected at sequence {current.sequence_number}: "
                    f"recomputed hash mismatch."
                )

        return True, None

    def get_recent_entries(self, limit: int = 50) -> List[AuditEvent]:
        """Retrieve recent audit events (read-only)."""
        return list(self._entries[-limit:])
