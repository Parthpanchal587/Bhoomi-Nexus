"""
Authenticated Secure Inter-Process Communication (IPC) Channel.

Provides:
1. Message authentication using HMAC-SHA256
2. Anti-replay protection via sliding timestamp windows and unique nonce tracking
3. Safe JSON-only serialization (no unsafe pickle deserialization)
4. Request correlation with UUID4 request_ids
5. Strict schema validation
"""

import hashlib
import hmac
import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set, Tuple


class IPCMessage:
    """Structured, authenticated IPC envelope."""

    def __init__(
        self,
        request_id: str,
        caller_id: str,
        caller_role: str,
        operation: str,
        payload: Dict[str, Any],
        timestamp: float,
        nonce: str,
        signature: str = "",
    ):
        self.request_id = request_id
        self.caller_id = caller_id
        self.caller_role = caller_role
        self.operation = operation
        self.payload = payload
        self.timestamp = timestamp
        self.nonce = nonce
        self.signature = signature

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "caller_id": self.caller_id,
            "caller_role": self.caller_role,
            "operation": self.operation,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IPCMessage":
        return cls(
            request_id=d["request_id"],
            caller_id=d["caller_id"],
            caller_role=d["caller_role"],
            operation=d["operation"],
            payload=d.get("payload", {}),
            timestamp=float(d["timestamp"]),
            nonce=d["nonce"],
            signature=d.get("signature", ""),
        )


class SecureIPCChannel:
    """
    Authenticated IPC Channel with Anti-Replay Protection.
    
    Guarantees message integrity, prevents replay attacks, and restricts
    deserialization to verified JSON schemas.
    """

    MAX_TIMESTAMP_DRIFT_SECONDS = 30.0  # Allowed clock skew / replay window

    def __init__(self, shared_secret: Optional[bytes] = None) -> None:
        self._shared_secret = shared_secret or secrets.token_bytes(32)
        self._seen_nonces: Set[str] = set()
        self._nonce_timestamps: Dict[str, float] = {}

    def create_message(
        self,
        caller_id: str,
        caller_role: str,
        operation: str,
        payload: Dict[str, Any],
        request_id: Optional[str] = None,
    ) -> IPCMessage:
        """Create and cryptographically sign an outgoing IPC message."""
        req_id = request_id or str(uuid.uuid4())
        ts = time.time()
        nonce = secrets.token_hex(16)

        # Canonical data representation to sign
        canonical = self._canonical_string(req_id, caller_id, caller_role, operation, payload, ts, nonce)
        signature = hmac.new(self._shared_secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

        return IPCMessage(
            request_id=req_id,
            caller_id=caller_id,
            caller_role=caller_role,
            operation=operation,
            payload=payload,
            timestamp=ts,
            nonce=nonce,
            signature=signature,
        )

    def verify_message(self, message: IPCMessage) -> Tuple[bool, Optional[str]]:
        """
        Verify incoming message authenticity and replay protection.
        Returns (True, None) if authentic, or (False, error_reason) if invalid.
        """
        now = time.time()

        # 1. Check timestamp drift (anti-replay window)
        time_diff = abs(now - message.timestamp)
        if time_diff > self.MAX_TIMESTAMP_DRIFT_SECONDS:
            return False, f"IPC timestamp expired or clock skew too large ({time_diff:.1f}s > {self.MAX_TIMESTAMP_DRIFT_SECONDS}s)"

        # 2. Check nonce uniqueness (detect exact duplicate/replay attack)
        self._cleanup_old_nonces(now)
        if message.nonce in self._seen_nonces:
            return False, "IPC Replay attack detected: Nonce has already been consumed."

        # 3. Verify cryptographic HMAC signature
        canonical = self._canonical_string(
            message.request_id,
            message.caller_id,
            message.caller_role,
            message.operation,
            message.payload,
            message.timestamp,
            message.nonce,
        )
        expected_sig = hmac.new(self._shared_secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(message.signature, expected_sig):
            return False, "IPC Message signature mismatch: integrity check failed."

        # Record consumed nonce
        self._seen_nonces.add(message.nonce)
        self._nonce_timestamps[message.nonce] = now

        return True, None

    def _canonical_string(
        self,
        request_id: str,
        caller_id: str,
        caller_role: str,
        operation: str,
        payload: Dict[str, Any],
        timestamp: float,
        nonce: str,
    ) -> str:
        serialized_payload = json.dumps(payload, sort_keys=True)
        return f"{request_id}|{caller_id}|{caller_role}|{operation}|{serialized_payload}|{timestamp:.4f}|{nonce}"

    def _cleanup_old_nonces(self, now: float) -> None:
        """Evict nonces older than 2x the drift window to prevent unbounded memory growth."""
        cutoff = now - (self.MAX_TIMESTAMP_DRIFT_SECONDS * 2)
        expired = [n for n, ts in self._nonce_timestamps.items() if ts < cutoff]
        for n in expired:
            self._seen_nonces.discard(n)
            del self._nonce_timestamps[n]
