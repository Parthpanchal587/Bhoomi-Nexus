# BHOOMI NEXUS — AUTHENTICATION ARCHITECTURE & SPECIFICATION

**System:** Bhoomi Nexus — National Land Intelligence & Cadastral Geospatial Engine  
**Module:** Government-Grade Authentication & Identity Verification Subsystem  
**Classification:** Technical Architecture Specification  
**Version:** 2.0 (RBAC Hardened)  
**Last Updated:** September 2026  

---

## 1. Executive Summary

BHOOMI-NEXUS implements an enterprise-grade, defense-in-depth authentication framework tailored for government land administration and cadastral geospatial intelligence. It combines:
- **Cryptographic Password Hashing:** PBKDF2-HMAC-SHA256 with 600,000 iterations and per-user 32-byte cryptographic salts.
- **Constant-Time Verification:** Timing-attack resistant string comparison using `hmac.compare_digest`.
- **Brute-Force & Credential Stuffing Defense:** Account lockout after 5 consecutive failed attempts (15-minute lockout window) plus sliding-window IP rate limiting (10 attempts/minute per IP).
- **High-Entropy Session Tokens:** 256-bit cryptographically secure URL-safe tokens (`secrets.token_urlsafe(36)`) with 24-hour expiration and immediate revocation on logout.
- **Zero Plaintext Secret Exposure:** Password hashes, salts, and private keys are never transmitted to clients or written to audit logs.

---

## 2. Authentication Architecture

```
                                  [ Client Browser ]
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │                                             │
            Public Request                              Protected Request
                   │                                             │
                   ▼                                             ▼
          [ Public Landing ]                            [ Authorization Header ]
          (No login required)                           Bearer <session_token>
                   │                                             │
                   │ Clicks Protected Feature                    │
                   ▼                                             ▼
         [ Modal / Redirect ]                          [ RateLimiterMiddleware ]
         "Sign In to Continue"                         (Per-IP Sliding Bucket)
                   │                                             │
                   ▼                                             ▼
          [ POST /login ]                             [ SecurityHeadersMiddleware ]
        Email/Username + Pwd                          (CSP, HSTS, DENY, nosniff)
                   │                                             │
                   ▼                                             ▼
      [ RateLimiter (10/min) ]                         [ Auth & RBAC Dependency ]
                   │                                   - Validate 256-bit Token
                   ▼                                   - Check Expiry (24 hr)
         [ Account Lockout ]                           - Match Required Permission
      Failed attempts >= 5?                                      │
         │                │                                      ▼
        Yes               No                             [ Protected Handler ]
         │                │                              (Execute Land Intelligence)
         ▼                ▼
     HTTP 423     [ PBKDF2-HMAC-SHA256 ]
     (Locked)     Salt: 32 bytes | 600k rounds
                  Constant-Time Compare
                          │
                   Success?
                   ├── Yes ──► Generate 256-bit Session Token ──► HTTP 200 (Profile + Perms)
                   └── No  ──► Increment Failed Count (Lock if 5) ──► HTTP 401
```

---

## 3. Cryptographic Implementation Details

### 3.1 Password Storage & Derivation
- **Algorithm:** PBKDF2 (Password-Based Key Derivation Function 2)
- **Pseudorandom Function (PRF):** HMAC-SHA256
- **Iteration Count:** 600,000 iterations (exceeding OWASP recommendations for PBKDF2-HMAC-SHA256)
- **Salt Generation:** `secrets.token_bytes(32)` (cryptographically secure random byte generation from OS entropy pool)
- **Hash Output:** 256-bit binary digest, encoded as 64 lowercase hexadecimal characters.

```python
# Reference implementation in app/services/auth.py
def hash_password(password: str, salt: bytes) -> Tuple[bytes, str]:
    derived = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        600_000
    )
    return salt, derived.hex()
```

### 3.2 Constant-Time Matching
To eliminate side-channel timing attacks that could reveal password prefixes through microsecond variations in string comparison:
```python
if not hmac.compare_digest(computed_hash, user.password_hash):
    # Reject authentication
```

### 3.3 Account Lockout Matrix
| Metric | Threshold / Value | Behavior |
| :--- | :--- | :--- |
| **Max Failed Attempts** | 5 attempts | Reaching 5 failures sets `locked_until = now + 900` |
| **Lockout Window** | 15 minutes (900 seconds) | All authentication attempts reject with `HTTP 423 Locked` |
| **Failed Attempt Reset** | On successful login | Successful credential match resets counter to `0` |
| **Administrative Unlock** | `auth_service.unlock_account(id)` | Manual unlock available for emergency clearance |

---

## 4. API Endpoints Specification

### 4.1 `POST /api/v1/auth/login`
Authenticates a user and issues a bearer session token.

- **Rate Limit:** 10 requests / minute per client IP.
- **Request Body (JSON):**
  ```json
  {
    "username": "officer.jaipur@bhoominexus.gov.in",
    "password": "OfficerGov#2026!"
  }
  ```
  *(Accepts email address or convenient alias: `admin`, `officer`, `policymaker`, `researcher`, `verifier`).*

- **Response (HTTP 200 OK):**
  ```json
  {
    "user_id": "USR-GOV-8F4A1B2C",
    "email": "officer.jaipur@bhoominexus.gov.in",
    "full_name": "Ramesh Kumar Sharma (Tehsildar)",
    "role": "GOVERNMENT_OFFICER",
    "token": "dGhpc19pc19hXzI1NmJpdF9zZWN1cmVfc2Vzc2lvbl90b2tlbg...",
    "expires_at": 1789209600.0,
    "permissions": [
      "VIEW_PUBLIC_GIS",
      "VIEW_PUBLIC_RESEARCH",
      "USE_AI_BASIC",
      "USE_AI_FULL",
      "RUN_OSINT",
      "VIEW_OSINT_EVIDENCE",
      "VERIFY_DOCUMENT",
      "REGISTER_DOCUMENT",
      "VIEW_LEDGER",
      "RUN_POLICY_SIMULATION"
    ],
    "message": "Authentication successful. Session token issued."
  }
  ```

- **Error Responses:**
  - `HTTP 401 Unauthorized`: Invalid username or incorrect password.
  - `HTTP 423 Locked`: Account is temporarily locked due to excessive failed attempts. Returns remaining lockout seconds.
  - `HTTP 429 Too Many Requests`: IP rate limit exceeded. Returns `Retry-After` header.

### 4.2 `GET /api/v1/auth/me`
Retrieves the authenticated identity profile for the bearer token.

- **Headers:** `Authorization: Bearer <session_token>`
- **Response (HTTP 200 OK):**
  ```json
  {
    "user_id": "USR-GOV-8F4A1B2C",
    "email": "officer.jaipur@bhoominexus.gov.in",
    "full_name": "Ramesh Kumar Sharma (Tehsildar)",
    "role": "GOVERNMENT_OFFICER",
    "is_active": true,
    "created_at": "2026-03-01T00:00:00Z",
    "permissions": [...]
  }
  ```
- **Error:** `HTTP 401 Unauthorized` if token is missing, malformed, expired, or revoked.

### 4.3 `POST /api/v1/auth/logout`
Invalidates and revokes the active session token.

- **Headers:** `Authorization: Bearer <session_token>`
- **Response (HTTP 200 OK):**
  ```json
  {
    "status": "SUCCESS",
    "message": "Session invalidated successfully. Safe logout completed."
  }
  ```

### 4.4 `GET /api/v1/auth/security-status`
Public endpoint returning the live defensive security score, compliance metrics, and active posture of Bhoomi Nexus.

### 4.5 `GET /api/v1/auth/roles`
Public endpoint exposing the 5 official platform roles, access levels, and permission mappings.

### 4.6 `GET /api/v1/auth/audit-logs`
Protected endpoint (strictly restricted to `Role.ADMIN` with `VIEW_AUDIT_LOGS` permission) providing full immutable audit records of all authentication events, document registrations, and security rejections.

---

## 5. UI Integration & User Experience

### 5.1 Public Landing Experience Preserved
Visitors to `https://bhoomi-nexus.vercel.app/` or `http://localhost:8000/` are **never forced to log in**. The full interactive GIS map, cadastral boundary explorer, and public educational information remain 100% accessible to anonymous guests.

### 5.2 Header Authentication Control
The header displays a non-intrusive GovTech control:
- **Logged Out:** Compact button `[🔐 साइन इन / Sign In]` styled to match the official Government of India / NIC visual theme.
- **Logged In:** Compact user pill displaying `[👤 User Name / Role ▼]`. Clicking toggles a professional GovTech dropdown:
  - **कार्यक्षेत्र (My Dashboard)** -> navigates to `/dashboard`
  - **मेरी प्रोफ़ाइल (My Profile)** -> opens authenticated identity dialog
  - **भूमिका (Role & Access Level)** -> highlights active operational role
  - **सुरक्षा केंद्र (Security Center)** -> opens audit and posture modal
  - **लॉगआउट (Logout)** -> revokes session token and clears localStorage

### 5.3 Dedicated Login Page (`/login`)
A dedicated, split-screen portal adhering strictly to the national cadastral design system:
- **Left Column:** Cadastral GIS background, Ashoka Stambh emblem, platform identity, and security clearance notice.
- **Right Column:** Government credential form, one-click prototype role switcher tabs (Officer, Policymaker, Researcher, Legal Verifier, Admin), live password toggle, prototype disclaimer, and safe destination redirect support (`?redirect=/dashboard` or any relative path).

### 5.4 Protected Action Interception
When an unauthenticated visitor clicks an authenticated action (such as "Register Document in Ledger" or "Run Policy Simulation"), an access modal (`modal-auth-required`) is displayed explaining the required role and offering an immediate `[साइन इन करें / Sign In]` button that preserves the target state.

---

## 6. Development & Prototype Seed Accounts

For testing, demonstration, and Smart India Hackathon (SIH) evaluation, the backend initializes 5 pre-configured accounts:

| Role | Username / Email | Default Password | Clearance Level |
| :--- | :--- | :--- | :--- |
| **Government Officer** | `officer` or `officer.jaipur@bhoominexus.gov.in` | `OfficerGov#2026!` | Cadastral verification, document registration, parcel analysis |
| **Policymaker** | `policymaker` or `policy.delhi@bhoominexus.gov.in` | `PolicyMaker#2026!` | Section 90-A policy simulations, land use insights |
| **Researcher** | `researcher` or `research.isro@bhoominexus.gov.in` | `Researcher#2026!` | Satellite telemetry, soil data, GIS intelligence |
| **Legal / Property Verifier** | `verifier` or `legal.verifier@bhoominexus.gov.in` | `LegalVerifier#2026!` | SHA-256 deed verification, registration, title ledger checks |
| **System Administrator** | `admin` or `admin@bhoominexus.gov.in` | `BhoomiAdmin#2026!` | Complete administrative control, raw audit logs, user management |

> [!NOTE]
> Demo accounts are seeded with unique 32-byte cryptographic salts and hashed via 600,000 iterations of PBKDF2-HMAC-SHA256 upon application startup. No plaintext credentials exist in backend persistent storage.
