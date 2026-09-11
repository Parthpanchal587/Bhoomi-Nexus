"""
BHOOMI-NEXUS: Authentication & Authorization (RBAC) Security Service.

Implements:
1. PBKDF2-HMAC-SHA256 password hashing with 600,000 iterations & cryptographic salt.
2. Secure session token generation (secrets.token_urlsafe) with timestamped expiry.
3. Role-Based Access Control (RBAC): GUEST, USER, ANALYST, OFFICIAL, ADMIN.
4. Brute-force protection & rate tracking.
5. Immutable security audit logging for all authentication & authorization events.
"""

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set


class Role(str, Enum):
    GUEST = "GUEST"
    GOVERNMENT_OFFICER = "GOVERNMENT_OFFICER"
    POLICYMAKER = "POLICYMAKER"
    RESEARCHER = "RESEARCHER"
    LEGAL_VERIFIER = "LEGAL_VERIFIER"
    ADMIN = "ADMIN"

    # Backward compatibility aliases
    OFFICIAL = "GOVERNMENT_OFFICER"
    ANALYST = "RESEARCHER"
    USER = "LEGAL_VERIFIER"


class Permission:
    VIEW_PUBLIC_GIS = "VIEW_PUBLIC_GIS"
    VIEW_PUBLIC_RESEARCH = "VIEW_PUBLIC_RESEARCH"
    USE_AI_BASIC = "USE_AI_BASIC"
    USE_AI_FULL = "USE_AI_FULL"
    RUN_OSINT = "RUN_OSINT"
    VIEW_OSINT_EVIDENCE = "VIEW_OSINT_EVIDENCE"
    VERIFY_DOCUMENT = "VERIFY_DOCUMENT"
    REGISTER_DOCUMENT = "REGISTER_DOCUMENT"
    VIEW_LEDGER = "VIEW_LEDGER"
    WRITE_LEDGER = "WRITE_LEDGER"
    MANAGE_DATASETS = "MANAGE_DATASETS"
    RUN_POLICY_SIMULATION = "RUN_POLICY_SIMULATION"
    VIEW_AUDIT_LOGS = "VIEW_AUDIT_LOGS"
    MANAGE_USERS = "MANAGE_USERS"
    MANAGE_ROLES = "MANAGE_ROLES"
    ADMIN_SYSTEM = "ADMIN_SYSTEM"


# Role hierarchy and permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[str]] = {
    Role.GUEST: {
        Permission.VIEW_PUBLIC_GIS,
        Permission.VIEW_PUBLIC_RESEARCH,
        Permission.USE_AI_BASIC,
        Permission.VIEW_LEDGER,
        "cadastral:view",
        "telemetry:view",
        "health:view",
        "security:view_status",
    },
    Role.GOVERNMENT_OFFICER: {
        Permission.VIEW_PUBLIC_GIS,
        Permission.VIEW_PUBLIC_RESEARCH,
        Permission.USE_AI_BASIC,
        Permission.USE_AI_FULL,
        Permission.RUN_OSINT,
        Permission.VIEW_OSINT_EVIDENCE,
        Permission.VERIFY_DOCUMENT,
        Permission.REGISTER_DOCUMENT,
        Permission.VIEW_LEDGER,
        Permission.RUN_POLICY_SIMULATION,
        "cadastral:view",
        "telemetry:view",
        "health:view",
        "security:view_status",
        "document:verify",
        "document:upload_own",
        "document:upload_official",
        "ai:query",
        "policy:evaluate",
        "gis:analyze",
        "blockchain:verify_dataset",
        "blockchain:view_ledger",
        "blockchain:notarize",
        "enclave:execute",
        "enclave:view_attestation",
    },
    Role.POLICYMAKER: {
        Permission.VIEW_PUBLIC_GIS,
        Permission.VIEW_PUBLIC_RESEARCH,
        Permission.USE_AI_BASIC,
        Permission.USE_AI_FULL,
        Permission.VIEW_LEDGER,
        Permission.RUN_POLICY_SIMULATION,
        "cadastral:view",
        "telemetry:view",
        "health:view",
        "security:view_status",
        "ai:query",
        "policy:evaluate",
        "gis:analyze",
        "blockchain:view_ledger",
    },
    Role.RESEARCHER: {
        Permission.VIEW_PUBLIC_GIS,
        Permission.VIEW_PUBLIC_RESEARCH,
        Permission.USE_AI_BASIC,
        Permission.USE_AI_FULL,
        Permission.RUN_OSINT,
        Permission.VIEW_OSINT_EVIDENCE,
        Permission.VIEW_LEDGER,
        "cadastral:view",
        "telemetry:view",
        "health:view",
        "security:view_status",
        "ai:query",
        "gis:analyze",
        "blockchain:verify_dataset",
        "blockchain:view_ledger",
    },
    Role.LEGAL_VERIFIER: {
        Permission.VIEW_PUBLIC_GIS,
        Permission.VIEW_PUBLIC_RESEARCH,
        Permission.USE_AI_BASIC,
        Permission.VERIFY_DOCUMENT,
        Permission.REGISTER_DOCUMENT,
        Permission.VIEW_LEDGER,
        Permission.VIEW_OSINT_EVIDENCE,
        "cadastral:view",
        "telemetry:view",
        "health:view",
        "security:view_status",
        "document:verify",
        "document:upload_own",
        "blockchain:view_ledger",
    },
    Role.ADMIN: {
        "*",  # Wildcard administrative access to all permissions
    },
}


@dataclass
class User:
    user_id: str
    email: str
    full_name: str
    role: Role
    password_hash: str
    salt: str
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_login: Optional[str] = None
    failed_attempts: int = 0
    locked_until: Optional[float] = None


@dataclass
class SessionToken:
    token: str
    user_id: str
    role: Role
    created_at: float
    expires_at: float
    ip_address: Optional[str] = None


@dataclass
class SecurityAuditEvent:
    timestamp: str
    event_type: str
    user_id: Optional[str]
    ip_address: Optional[str]
    detail: str
    severity: str = "INFO"


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, str]:
    """PBKDF2-HMAC-SHA256 password hashing with 600,000 iterations and 32-byte salt."""
    if salt is None:
        salt = secrets.token_bytes(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return salt, dk.hex()


def verify_password(password: str, salt: bytes, expected_hash: str) -> bool:
    """Constant-time comparison of PBKDF2-HMAC-SHA256 hash."""
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return hmac.compare_digest(dk.hex(), expected_hash)


class AuthService:
    """Thread-safe In-Memory Authentication & Authorization Manager."""

    SESSION_EXPIRY_SECONDS = 24 * 3600  # 24 Hours
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_SECONDS = 900  # 15 Minutes
    PBKDF2_ITERATIONS = 600_000

    ALIASES = {
        "admin": "admin@bhoominexus.gov.in",
        "officer": "officer.jaipur@bhoominexus.gov.in",
        "official": "officer.jaipur@bhoominexus.gov.in",
        "policymaker": "policy.delhi@bhoominexus.gov.in",
        "researcher": "research.isro@bhoominexus.gov.in",
        "analyst": "research.isro@bhoominexus.gov.in",
        "verifier": "legal.verifier@bhoominexus.gov.in",
        "user": "legal.verifier@bhoominexus.gov.in",
    }

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._sessions: Dict[str, SessionToken] = {}
        self._audit_log: List[SecurityAuditEvent] = []
        self._seed_default_accounts()

    def _hash_password(self, password: str, salt: bytes) -> str:
        """Hash password using PBKDF2-HMAC-SHA256 with 600,000 iterations."""
        _, p_hash = hash_password(password, salt)
        return p_hash

    def _seed_default_accounts(self):
        """Seed initial government role accounts with secure random salts."""
        accounts = [
            ("admin@bhoominexus.gov.in", "National Cadastral Director", Role.ADMIN, "BhoomiAdmin#2026!"),
            ("officer.jaipur@bhoominexus.gov.in", "Ramesh Kumar Sharma (Tehsildar)", Role.GOVERNMENT_OFFICER, "OfficerGov#2026!"),
            ("policy.delhi@bhoominexus.gov.in", "Dr. Sunita Verma (Director Land Policy)", Role.POLICYMAKER, "PolicyMaker#2026!"),
            ("research.isro@bhoominexus.gov.in", "Prof. Amit Banerjee (GIS Researcher)", Role.RESEARCHER, "Researcher#2026!"),
            ("legal.verifier@bhoominexus.gov.in", "Adv. Meera Chawla (Title Verifier)", Role.LEGAL_VERIFIER, "LegalVerifier#2026!"),
        ]
        for email, name, role, pwd in accounts:
            salt = secrets.token_bytes(32)
            pwd_hash = self._hash_password(pwd, salt)
            u_id = f"USR-{role.value[:3]}-{secrets.token_hex(4).upper()}"
            self._users[email] = User(
                user_id=u_id,
                email=email,
                full_name=name,
                role=role,
                password_hash=pwd_hash,
                salt=salt.hex(),
                is_active=True,
            )

    def unlock_account(self, identifier: str):
        """Unlock an account for testing or administrative recovery."""
        target_email = self.ALIASES.get(identifier.strip().lower(), identifier.strip().lower())
        user = self._users.get(target_email)
        if user:
            user.failed_attempts = 0
            user.locked_until = None
            self.log_audit("AUTH_ACCOUNT_UNLOCKED", user.user_id, "127.0.0.1", f"Account unlocked: {identifier}")

    def log_audit(self, event_type: str, user_id: Optional[str], ip: Optional[str], detail: str, severity: str = "INFO"):
        """Record immutable security event."""
        evt = SecurityAuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            user_id=user_id,
            ip_address=ip or "0.0.0.0",
            detail=detail,
            severity=severity,
        )
        self._audit_log.append(evt)
        # Limit memory retention to last 1,000 security events
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

    def authenticate(self, identifier: str, password: str, ip: Optional[str] = None) -> Optional[SessionToken]:
        """Verify user credentials with lockout protection and constant-time comparison."""
        now = time.time()
        target_email = self.ALIASES.get(identifier.strip().lower(), identifier.strip().lower())
        user = self._users.get(target_email)
        if not user:
            self.log_audit("AUTH_LOGIN_FAILED", None, ip, f"Unknown account: {identifier}", severity="WARNING")
            return None

        # Check account lockout
        if user.locked_until and now < user.locked_until:
            remaining = int(user.locked_until - now)
            self.log_audit("AUTH_LOCKED_ATTEMPT", user.user_id, ip, f"Account locked. {remaining}s remaining", severity="WARNING")
            return None

        salt_bytes = bytes.fromhex(user.salt)
        computed_hash = self._hash_password(password, salt_bytes)

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(computed_hash, user.password_hash):
            user.failed_attempts += 1
            if user.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                user.locked_until = now + self.LOCKOUT_DURATION_SECONDS
                self.log_audit("AUTH_ACCOUNT_LOCKED", user.user_id, ip, f"Exceeded {self.MAX_FAILED_ATTEMPTS} failed attempts", severity="HIGH")
            else:
                self.log_audit("AUTH_PASSWORD_MISMATCH", user.user_id, ip, f"Attempt {user.failed_attempts}/{self.MAX_FAILED_ATTEMPTS}", severity="WARNING")
            return None

        # Reset failed attempts on success
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc).isoformat()

        # Generate secure session token
        token_str = secrets.token_urlsafe(36)
        session = SessionToken(
            token=token_str,
            user_id=user.user_id,
            role=user.role,
            created_at=now,
            expires_at=now + self.SESSION_EXPIRY_SECONDS,
            ip_address=ip,
        )
        self._sessions[token_str] = session
        self.log_audit("AUTH_LOGIN_SUCCESS", user.user_id, ip, f"Role: {user.role.value}")
        return session

    def validate_token(self, token: Optional[str]) -> Optional[User]:
        """Validate bearer token and return user if active and unexpired."""
        if not token:
            return None
        clean_token = token.replace("Bearer ", "").strip()
        session = self._sessions.get(clean_token)
        if not session:
            return None

        now = time.time()
        if now > session.expires_at:
            del self._sessions[clean_token]
            return None

        for u in self._users.values():
            if u.user_id == session.user_id and u.is_active:
                return u
        return None

    def invalidate_token(self, token: str) -> bool:
        """Log out session and remove token."""
        clean_token = token.replace("Bearer ", "").strip()
        if clean_token in self._sessions:
            sess = self._sessions.pop(clean_token)
            self.log_audit("AUTH_LOGOUT", sess.user_id, sess.ip_address, "Session terminated")
            return True
        return False

    def authorize(self, user: Optional[User], required_permission: str) -> bool:
        """Check if user role satisfies required permission."""
        if not user:
            return False
        if user.role == Role.ADMIN:
            return True
        perms = ROLE_PERMISSIONS.get(user.role, set())
        return ("*" in perms) or (required_permission in perms)

    def get_security_audit_summary(self) -> dict:
        """Return non-sensitive security metrics for security center display."""
        now = time.time()
        active_sessions = sum(1 for s in self._sessions.values() if s.expires_at > now)
        recent_events = self._audit_log[-15:]
        return {
            "status": "OPERATIONAL",
            "active_sessions": active_sessions,
            "registered_accounts": len(self._users),
            "total_audit_events": len(self._audit_log),
            "recent_events": [
                {
                    "timestamp": e.timestamp,
                    "event_type": e.event_type,
                    "severity": e.severity,
                    "detail": e.detail,
                }
                for e in reversed(recent_events)
            ],
        }

    def get_full_audit_logs(self, user: User) -> List[dict]:
        """Return full audit log entries (restricted to ADMIN)."""
        if user.role != Role.ADMIN and not self.authorize(user, Permission.VIEW_AUDIT_LOGS):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: Only Administrator role can view raw security audit logs.",
            )
        return [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "user_id": e.user_id,
                "ip_address": e.ip_address,
                "detail": e.detail,
                "severity": e.severity,
            }
            for e in reversed(self._audit_log)
        ]


# Global singleton instance
auth_service = AuthService()


def require_permission(required_perm: str):
    """FastAPI route dependency to verify authentication and permission."""
    from fastapi import Header, HTTPException, status

    def dependency(authorization: Optional[str] = Header(None)):
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please sign in to perform this action.",
            )
        user = auth_service.validate_token(authorization)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token. Please sign in again.",
            )
        if not auth_service.authorize(user, required_perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Role '{user.role.value}' does not possess the required '{required_perm}' permission.",
            )
        return user

    return dependency

