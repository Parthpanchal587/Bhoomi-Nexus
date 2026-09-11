# BHOOMI-NEXUS: Security Architecture & Comprehensive Threat Model

**Document Version:** 2.0 (TEE-Inspired Secure Execution Architecture)  
**Classification:** Public Security Specification & Threat Model  
**Last Updated:** September 2026  

---

## 1. Executive Security Overview

BHOOMI-NEXUS incorporates a **Trusted Execution Environment (TEE)-inspired secure isolation architecture**. Sensitive operations—such as cryptographic document integrity checks, perceptual text fingerprinting, legal due diligence parsing, regulatory policy evaluation, and secret key sealing—are decoupled from the untrusted web presentation tier and executed inside an isolated, policy-governed execution environment.

### Core Security Principles

1. **Explicit Trust Boundaries:** The web application, network inputs, user files, and external APIs are strictly classified as the **Untrusted Zone**. Sensitive cryptographic operations, secret keys, and policy evaluations reside in the **Trusted Zone**.
2. **Deny-by-Default Policy Enforcement:** All operations must match an explicit, versioned security policy defining caller role, execution timeouts, memory bounds, and network permissions. Unmapped operations are rejected immediately.
3. **Transparent Hardware vs. Software Labelling:** The platform operates using a pluggable `SecureExecutionProvider` interface. In environments without hardware-enforced CPU enclaves (such as Intel SGX or AMD SEV), the system deploys the `SoftwareSecureExecutionProvider`, clearly labelling measurements and attestation quotes as **software integrity proofs** without falsely claiming hardware guarantees.
4. **Zero Persistent Plaintext Secrets:** Sensitive secrets are sealed using **AES-256-GCM** envelope encryption with **HKDF-SHA256** key derivation, with master key binding to the operating system user context via **Windows DPAPI** on Windows systems. Sensitive buffers in memory are explicitly zeroized.
5. **Tamper-Evident Audit Logging:** All security-relevant events are appended to a cryptographically hash-chained audit log (`SHA-256(prev_hash + data)`), enabling on-demand audit verification and breach detection.

---

## 2. Trust Boundary Architecture

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                UNTRUSTED ZONE                                    │
│                                                                                  │
│   ┌────────────────────────┐                    ┌────────────────────────────┐   │
│   │    Web Browser UI      │                    │     External APIs          │   │
│   │  (Leaflet, HTML5, JS)  │                    │  (OpenStreetMap, Open-     │   │
│   └───────────┬────────────┘                    │   Meteo Forecast)          │   │
│               │ HTTP / JSON Payload             └─────────────┬──────────────┘   │
│               ▼                                               │                  │
│   ┌───────────────────────────────────────────────────────────┴──────────────┐   │
│   │                   FastAPI Main Application Process                       │   │
│   │  - Static file delivery                                                  │   │
│   │  - Public REST endpoints (/api/geo, /api/telemetry, /api/health)         │   │
│   │  - Untrusted file reception (PDF uploads)                                │   │
│   └─────────────────────────────────────┬────────────────────────────────────┘   │
└─────────────────────────────────────────┼────────────────────────────────────────┘
                                          │
                        TRUST BOUNDARY GATEWAY (X-Enclave-Token)
                                          │
┌─────────────────────────────────────────▼────────────────────────────────────────┐
│                                 TRUSTED ZONE                                     │
│                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                   Secure Enclave Gateway & Policy Engine                 │   │
│   │  - Caller authentication & role validation (RBAC)                        │   │
│   │  - Deny-by-default operation allowlist checking                          │   │
│   │  - Input payload size enforcement (max 10 MB ceiling)                    │   │
│   │  - Replay protection (sliding timestamp window + unique nonce tracking)  │   │
│   └─────────────────────────────────────┬────────────────────────────────────┘   │
│                                         │ Authorized Dispatch                    │
│                                         ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                   Isolated Execution Sandbox (TEE Provider)              │   │
│   │  - Dedicated worker thread/process with sanitized environment            │   │
│   │  - Strict execution timeouts (psutil & concurrent.futures)               │   │
│   │  - Cryptographic operations (SHA-256 binary & text fingerprinting)       │   │
│   │  - Document parsing in isolated exception boundary                       │   │
│   └───────────────┬───────────────────────────────┬──────────────────────────┘   │
│                   │                               │                              │
│                   ▼                               ▼                              │
│   ┌───────────────────────────────┐   ┌──────────────────────────────────────┐   │
│   │      Secure Secret Vault      │   │     Tamper-Evident Audit Log         │   │
│   │  - AES-256-GCM encryption     │   │  - SHA-256 hash-chained entries      │   │
│   │  - HKDF key derivation        │   │  - Zero secret or PII exposure       │   │
│   │  - Windows DPAPI key binding  │   │  - On-demand cryptographic audit     │   │
│   │  - Memory buffer zeroization  │   │    validation                        │   │
│   └───────────────────────────────┘   └──────────────────────────────────────┘   │
│                                         │                                        │
│                                         ▼                                        │
│                        AUTHENTICATED & SIGNED OUTPUT                             │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Comprehensive Threat Matrix

The following table documents all identified threat vectors, evaluating **Threat → Impact → Mitigation → Remaining Risk**:

| # | Threat Vector | Potential Impact | Security Mitigation | Remaining Risk |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Malware & Host OS Compromise** | Compromise of application memory, extraction of keys, or unauthorized process injection. | The enclave uses Windows DPAPI to bind master keys to the OS user account, minimizing plaintext exposure in memory. Sensitive buffers are zeroized upon release. All code files are measured in attestation hashes. | In a software-only enclave, a root/SYSTEM level kernel rootkit can observe process memory. Full mitigation requires hardware TEE (Intel SGX / AMD SEV). |
| **2** | **Malicious User Input (PDF Exploit / Zip Bomb)** | Memory exhaustion, buffer overflow, or parser vulnerability in PyPDF2 triggering host server crash. | Maximum payload limit enforced (10 MB). File bytes are parsed inside the `IsolatedSandbox` with strict execution timeouts (6000ms) and memory ceiling tracking (`psutil`). Parser crashes are caught at the sandbox boundary without killing the main server. | Zero-day parser vulnerabilities could trigger localized thread exceptions, which fail closed safely. |
| **3** | **Compromised Main Application** | Untrusted components attempting to execute unauthorized administrative actions or access raw keys. | Enclave operations enforce strict Role-Based Access Control (`SYSTEM`, `OPERATOR`, `AUDITOR`, `UNTRUSTED_CLIENT`). Sensitive operations (sealing, unsealing, block signing) require a cryptographically generated enclave bearer token (`X-Enclave-Token`). | If the application process memory itself is compromised, the attacker can impersonate in-process callers; mitigated by externalizing the enclave into a separate service daemon when scaled. |
| **4** | **Secret & Key Leakage in Memory Dumps** | Long-lived encryption keys or API tokens discovered in core dumps or memory inspection. | Master keys are derived on-demand via HKDF. Derived keys exist as ephemeral bytearrays and are immediately overwritten with zero bytes (`zeroize()`) upon operation completion. No plaintext secrets are logged or exposed via GET endpoints. | Operating system swap or pagefile might theoretically contain residual byte fragments prior to zeroization if memory paging occurs during active execution. |
| **5** | **IPC Interception & Tampering** | Man-in-the-middle manipulation of inter-component requests or responses. | All IPC messages are structured via canonical JSON envelopes signed with HMAC-SHA256. Any modification to `request_id`, `caller_id`, `operation`, or `payload` invalidates the signature and triggers an immediate drop. | In-process IPC relies on shared memory security; inter-host IPC requires TLS 1.3 transport encryption. |
| **6** | **Replay Attacks** | An attacker intercepts an authorized signed request and re-submits it to execute duplicate operations or drain resources. | `SecureIPCChannel` enforces a two-layer anti-replay defense: (1) Sliding timestamp window (rejects messages older than 30 seconds), and (2) Unique nonce tracking cache (rejects any previously seen nonce within the active window). | System clock skew exceeding 30 seconds on misconfigured servers could cause legitimate requests to be rejected. |
| **7** | **Privilege Escalation & Policy Bypass** | An unauthenticated client invokes privileged endpoints (e.g. `crypto.seal_secret` or `notary.sign_record`). | `PolicyEngine` evaluates every request against `ROLE_HIERARCHY` before dispatch. Unknown or unmapped operations are denied by default. Privileged roles (`SYSTEM`, `OPERATOR`) require token verification. | Misconfiguration of default policy files; mitigated by immutable policy versioning and policy hash attestation. |
| **8** | **Code & Configuration Tampering** | An attacker modifies `config.py`, policy rules, or enclave code files on disk to alter enforcement logic. | `AttestationService` computes SHA-256 measurement vectors across all secure module code files, `config.py`, and `policy.py`. Attestation reports sign these measurements with a caller nonce, exposing any file changes. | Offline tampering where the signing key itself is replaced on disk; mitigated by anchoring the public attestation key outside the host. |
| **9** | **Sandbox Escape** | Arbitrary code execution attempting to access the host filesystem, network, or spawn child processes. | The isolated sandbox strips all host environment variables, runs without shell invocation (`shell=False`), and disallows arbitrary command strings. Operations are strictly dispatched to an internal static function registry. | Software thread/process sandboxes do not provide hypervisor-grade isolation; kernel vulnerabilities could theoretically allow escape. |
| **10** | **Path Traversal & Arbitrary File Access** | Uploaded filenames such as `../../etc/passwd` or Windows alternate data streams manipulating storage. | Documents and artifacts are processed in-memory as byte streams. Filenames are treated as descriptive metadata only and never concatenated into filesystem path operations. | If future modules write files to disk, explicit path sanitization (`os.path.basename` + safe directory resolution) must be strictly maintained. |
| **11** | **Command Injection** | Malicious characters (`;`, `&&`, `|`) in query parameters attempting to invoke OS shell commands. | Zero shell execution (`os.system` / `subprocess.Popen(shell=True)`) is permitted within the enclave layer. All operations are deterministic Python functions. | External utilities if invoked in future must use explicit argument vectors with strict allowlists. |
| **12** | **Denial of Service (Resource Exhaustion)** | Attackers sending massive payloads or computationally intensive tasks to lock worker threads. | (1) 10 MB maximum payload limit enforced at HTTP boundary, (2) Per-operation execution timeouts (2000ms - 8000ms), (3) Per-minute caller rate limits enforced in `PolicyEngine`, (4) Memory delta tracking via `psutil`. | Distributed DoS (DDoS) targeting the public web edge must be mitigated by cloud reverse proxies (e.g., Cloudflare, Vercel DDoS Shield). |

---

## 4. Attestation & Integrity Verification

The enclave provides a verifiable attestation mechanism accessible via `POST /api/v1/enclave/attest`.

### Attestation Quote Structure

```json
{
  "attestation_id": "ATTEST-a1b2c3d4e5f60718",
  "timestamp": "2026-09-11T14:30:00.000000Z",
  "caller_nonce": "9f8e7d6c5b4a3928",
  "provider": "BHOOMI-SoftwareSecureExecutionProvider",
  "hardware_backed": false,
  "attestation_type": "SOFTWARE_INTEGRITY_MEASURED",
  "measurements": {
    "application_version": "2.0.0-TEE-PROTOTYPE",
    "code_hash_sha256": "3a7d8e...",
    "config_hash_sha256": "9f0b1c...",
    "policy_hash_sha256": "e4f5a6...",
    "runtime_environment_hash": "b2c3d4..."
  },
  "enclave_public_key_fingerprint": "7a8b9c0d1e2f3a4b",
  "signature_algorithm": "HMAC-SHA256",
  "signature": "8f3b2a...",
  "attestation_statement": "Verified software-measured integrity quote..."
}
```

Clients verify that:
1. `caller_nonce` matches the nonce generated for the request (freshness guarantee).
2. `code_hash_sha256` and `policy_hash_sha256` match published, known-good reference measurements.
3. `hardware_backed` accurately reflects the environment (transparent disclosure).

---

## 5. OSINT & Public-Source Intelligence Security Controls

The OSINT land intelligence subsystem connects with external data portals, processes untrusted public records, and provides cross-registry corroboration. It enforces the following security controls:

### 5.1 Server-Side Request Forgery (SSRF) Prevention
- **Blocked Subnets:** RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`), and carrier-grade NAT.
- **Blocked Cloud Metadata:** Direct block on `169.254.169.254`, `metadata.google.internal`, and `instance-data`.
- **Pre-Flight DNS Resolution:** Validates all resolved IP addresses (`socket.getaddrinfo`) to prevent DNS rebinding attacks.
- **Scheme Restriction:** Rejects non-HTTP(S) schemes (`file://`, `gopher://`, `ftp://`).

### 5.2 External Domain Rate Limiting & DoS Protection
- Token-bucket rate pacing (`OSINTRateLimiter`) per external domain.
- Stricter request pacing for government portals (`*.gov.in` and `*.nic.in` limited to max 5 req/min).
- Strict HTTP request timeouts (4.5 seconds) with immediate circuit breaking and fallback to verified cached datasets.

### 5.3 Provenance & Anti-Fabrication Safeguards
- 5-tier immutable provenance envelopes (`ProvenanceMetadata`) with confidence ratings (1 to 5 stars).
- No user-submitted document is ever elevated to `VERIFIED_OFFICIAL_DATA`.
- Dual SHA-256 fingerprinting for uploaded deeds (binary file digest + normalized perceptual text digest) with explicit statutory disclaimers.

---

## 6. Security Incident Reporting

To report a vulnerability or security concern regarding BHOOMI-NEXUS:
- Open a confidential security advisory via GitHub Security Advisories.
- Do NOT post active exploits, zero-days, or proof-of-concept attacks on public issues.
