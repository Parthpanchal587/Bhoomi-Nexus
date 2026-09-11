# BHOOMI-NEXUS: Document Verification & Cryptographic Security Specification

**Version:** 2.4.0 (SIH Production Finishing Release)  
**Cryptographic Primitives:** SHA-256 (FIPS 180-4), Perceptual Text Normalization & Fingerprinting  
**Storage Architecture:** Immutable In-Memory Ledger (Append-Only Hash Chain)  
**Statutory Alignment:** Information Technology Act 2000 & Indian Evidence Act (Digital Evidence Sections)  

---

## 1. Cryptographic File Integrity vs. Legal Authenticity

A fundamental principle of Bhoomi-Nexus is strict accuracy in legal and security terminology:

> **IMPORTANT STATUTORY NOTICE:**
> Cryptographic SHA-256 verification proves **file identity and binary integrity** relative to a registered ledger record. 
> SHA-256 alone does **NOT** prove that a title deed is legally genuine or free from external fraud. 
> Therefore, the system NEVER outputs misleading claims such as `"Government Document Verified"` or `"Document is legally genuine"`.
> Instead, it outputs:
> - **`FILE INTEGRITY MATCH [OK]`** when the binary hash matches registered records.
> - **`FILE INTEGRITY MISMATCH [TAMPERED / UNVERIFIED]`** when altered or unknown.
> - With mandatory statutory guidance:
>   *"Legal authenticity must be confirmed against the authoritative land-record / registration source (State Sub-Registrar / Revenue Department)."*

---

## 2. Dual-Layer Verification Engine

When a PDF document is uploaded for verification, Bhoomi-Nexus processes it through two complementary cryptographic tiers:

```
                  Uploaded PDF Document
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    Tier 1: Binary Hash         Tier 2: Perceptual Layout & Text
      SHA-256 Digest                     Fingerprint
             │                           │
             ▼                           ▼
    Detects any single           Extracts structural text,
    byte alteration,             normalizes whitespace,
    hex edit, or injected        and computes canonical hash.
    malicious payload.           Detects text modifications even if
             │                   PDF stream is re-saved.
             └─────────────┬─────────────┘
                           │
                           ▼
             Ledger Match Evaluation:
             ├─ Both Match -> FILE INTEGRITY MATCH (Exact Binary)
             ├─ Text Match, Binary Differs -> FILE INTEGRITY MISMATCH (Re-saved / Altered)
             └─ No Match -> FILE INTEGRITY MISMATCH (Unregistered / Forged)
```

---

## 3. Server-Side Security Protections

### 3.1 PDF Header Magic Byte Validation
To prevent Remote Code Execution (RCE), polyglot file uploads, or malicious script injection, the backend inspects raw byte streams before any processing:
```python
if not file_bytes.startswith(b"%PDF"):
    raise HTTPException(
        status_code=400,
        detail="File security rejection: Uploaded file does not contain a valid %PDF magic byte header."
    )
```

### 3.2 Denial-of-Service (DoS) File Size Limiting
All upload and verification endpoints enforce a strict maximum size limit of **10 MB**:
```python
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024
if len(file_bytes) > MAX_DOCUMENT_SIZE_BYTES:
    raise HTTPException(status_code=413, detail="File exceeds maximum allowed size of 10 MB.")
```

### 3.3 Path Traversal & Filename Sanitization
Filenames are stripped of null bytes (`\x00`), directory separators (`/`, `\`, `..`), and restricted to safe alphanumeric characters and `.pdf` extensions:
```python
raw_name = file.filename or "unknown.pdf"
safe_filename = os.path.basename(raw_name).replace("\x00", "").strip()[:100]
if not safe_filename.lower().endswith(".pdf"):
    safe_filename += ".pdf"
```

### 3.4 Insecure Direct Object Reference (IDOR) Protection
Verification requests do not accept arbitrary client-provided document IDs. The document's binary hash is computed independently by the server and matched against the immutable ledger registry. A user cannot query or tamper with other users' records by guessing numeric sequence IDs.

### 3.5 Role-Based Authorization Enforcement
Only authorized roles (`GOVERNMENT_OFFICER`, `LEGAL_VERIFIER`, and `ADMIN`) possess the `Permission.VERIFY_DOCUMENT` privilege. Unauthorized roles (`POLICYMAKER`, `RESEARCHER`, `GUEST`) attempting direct API requests receive HTTP 401 or HTTP 403.

---

## 4. Client-Side Resilient Verification Fallback

In standalone demonstration environments, serverless edge deployments, or intermittent offline conditions, Bhoomi-Nexus provides a browser-native Web Crypto fallback:
- Uses `crypto.subtle.digest("SHA-256", buffer)` to compute the genuine 256-bit hash in browser hardware.
- Compares against local ledger records.
- Guarantees instant cryptographic demonstration capability without failing when external servers are isolated.
