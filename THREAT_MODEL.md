# BHOOMI NEXUS — OSINT & LAND INTELLIGENCE THREAT MODEL

### Security Architecture, Attack Vectors & Defensive Mitigations

---

## 1. Threat Modeling Scope

This document analyzes threat vectors specific to the **OSINT / Public-Source Land Intelligence subsystem**, where the platform interacts with external network endpoints, processes untrusted third-party documents, and correlates public records.

---

## 2. Threat Vector Analysis & Implemented Mitigations

### 2.1 Threat Vector 1: Server-Side Request Forgery (SSRF) & Internal Subnet Probing
- **Risk Profile**: An attacker inputs a malicious URL disguised as a state portal or document source (e.g. `http://169.254.169.254/latest/meta-data` or `http://127.0.0.1:8000/internal-admin`) to access cloud instance metadata or pivot into internal infrastructure.
- **Implemented Mitigation (`app.osint.security`)**:
  - Pre-flight IP validation against `BLOCKED_NETWORKS`:
    - Loopback: `127.0.0.0/8`, `::1/128`
    - RFC 1918 Private Subnets: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
    - Link-Local & Cloud Metadata: `169.254.0.0/16`, `fe80::/10`
    - Prohibited Hostnames: `localhost`, `metadata.google.internal`, `instance-data`
  - URL Scheme Enforcement: Only `http://` and `https://` are permitted. Protocols like `file://`, `gopher://`, `ftp://` are immediately rejected.

---

### 2.2 Threat Vector 2: DNS Rebinding Attacks
- **Risk Profile**: An attacker provides a domain name resolving initially to a legitimate public IP during validation, but returns a private IP (e.g., `127.0.0.1`) upon connection.
- **Implemented Mitigation (`app.osint.security`)**:
  - `validate_osint_url` resolves all socket address records (`socket.getaddrinfo`) and verifies that **every returned IP address** is strictly public and non-reserved before any HTTP client request is dispatched.

---

### 2.3 Threat Vector 3: Portal Denial of Service (DoS) & Target Throttling
- **Risk Profile**: High-frequency bulk queries could overload state government servers, triggering IP blocks or degrading citizen access to revenue portals.
- **Implemented Mitigation (`app.osint.rate_limiter`)**:
  - Thread-safe Token Bucket Rate Limiter (`OSINTRateLimiter`).
  - Stricter request pacing for sensitive state and national domains (`.gov.in`, `.nic.in` throttled to max 5 req/min, burst limit of 2).
  - Strict HTTP request timeouts (4.5s max) with immediate circuit breaking and transparent fallback to cached/demo datasets.

---

### 2.4 Threat Vector 4: Data Poisoning & Fraudulent Document Injection
- **Risk Profile**: Malicious actors submit fabricated deeds with forged revenue stamps or altered survey numbers to manipulate platform intelligence output.
- **Implemented Mitigation (`app.osint.document_intelligence`)**:
  - Dual Fingerprinting: Computes both byte-exact `document_hash_sha256` and normalized `ocr_fingerprint_sha256`.
  - Independent Corroboration: User-submitted declarations are never accepted as ground truth; they are cross-matched against official state records (`SourceRecordEntry`).
  - Strict Provenance Tagging: Document attributes are permanently classified as `USER_PROVIDED_DATA` (★★☆☆☆) and never elevated to `VERIFIED_OFFICIAL_DATA`.

---

### 2.5 Threat Vector 5: Doxxing & Personal Data Exfiltration
- **Risk Profile**: OSINT engines being misused to build intrusive individual dossiers or locate citizens without administrative justification.
- **Implemented Mitigation**:
  - Strict Land Parcel Centricity: Queries require cadastral identifiers (State, District, Tehsil, Khasra) rather than individual names or phone numbers.
  - No Personal Aggregation: The engine explicitly rejects person-search features, social media crawling, or credential leaks.
  - Audit Trail Logging: All queries log operator identity, timestamp, parcel parameters, and stated justification (`/api/v1/osint/audit`).

---

### 2.6 Threat Vector 6: Misleading Risk Attribution ("Defamation via AI")
- **Risk Profile**: Platform declaring a property or party "fraudulent" based on automated discrepancy detection, creating legal exposure.
- **Implemented Mitigation (`app.osint.risk_engine` & `conflict_engine`)**:
  - Ethical GovTech Directive: Algorithms are strictly bounded to descriptive, non-accusatory language (e.g., *"Area discrepancy detected between Cadastral RoR (1.0 Ha) and OSM field trace (1.2 Ha)"*).
  - Explicit Plausible Explanations: Automatically details benign administrative factors like unrecorded subdivisions, roadside setbacks, or digitization variances.
  - Mandatory Prototype Notice: Every report and screen prominently displays prototype disclaimers requiring official manual verification.

---

## 3. Defense-in-Depth Architecture

| Layer | Component | Security Control |
| :--- | :--- | :--- |
| **Network** | `security.py` | SSRF filter, DNS rebinding inspection, private IP blocking |
| **Rate Control** | `rate_limiter.py` | Domain-level token bucket pacing |
| **Execution** | `app/secure_enclave/` | TEE-inspired isolated subprocess execution & HMAC IPC |
| **Data Integrity** | `provenance.py` | Immutable 5-tier classification & star ratings |
| **Audit** | `orchestrator.py` | Cryptographic SHA-256 report hashing & query audit trail |
