# BHOOMI-NEXUS: Authentication & Authorization Flow

**Version:** 2.4.0 (SIH Production Finishing Release)  
**Security Architecture:** PBKDF2-HMAC-SHA256 (600,000 iterations) + CSPRNG Session Tokens  
**Authorization Model:** Role-Based Access Control (RBAC) with Server-Side Enforcement  

---

## 1. Overview & Principles

Bhoomi-Nexus implements a rigorous defense-in-depth authentication model designed to meet institutional government and SIH demonstration standards:

1. **Unconstrained Public Exploration:** Public GIS layers, reverse geocoding, real-time meteorological observations, and soil spatial models are accessible to all users without premature login barriers.
2. **First-Time Action Gate for Document Verification:** An unauthenticated visitor can open the Document Verification interface, browse local PDF files, inspect file metadata, and load test deeds. The authentication gate triggers **only when the user clicks "VERIFY DOCUMENT AUTHENTICITY"**.
3. **Session Preservation (Zero Re-Upload):** When authentication is triggered during document verification, the selected file object is held securely in active memory (`window._pendingDocVerificationFile`). Following successful login, registration, or 1-click Demo Verifier activation, the user is immediately returned to Document Verification, and the file verification proceeds automatically without requiring the user to select or upload the document again.
4. **Server-Side Enforcement:** Frontend permission checks exist solely for user interface feedback. All protected actions (such as `/api/v1/documents/verify` and `/api/v1/documents/upload`) strictly validate `Authorization: Bearer <token>` on the backend.

---

## 2. The Complete First-Time Verification Flow

```
User enters Bhoomi-Nexus
        │
        ▼
Clicks "दस्तावेज़ सत्यापन (Document Verification)"
(Modal opens freely — NO forced login simply to view UI)
        │
        ▼
User selects or drops PDF (e.g. Registered Sale Deed)
File details displayed in UI (Name, Size, Status: Ready)
        │
        ▼
User clicks "VERIFY DOCUMENT AUTHENTICITY" (submitDocumentVerification())
        │
        ▼
Is user authenticated?
 ├── YES (activeAuthToken exists)
 │     │
 │     └─► Executes POST /api/v1/documents/verify with Bearer Token
 │         Backend validates token & VERIFY_DOCUMENT permission
 │         Displays result: FILE INTEGRITY MATCH / MISMATCH
 │
 └── NO (activeAuthToken is null)
       │
       ▼
  1. Stores selected file safely: window._pendingDocVerificationFile = selectedVerifyFile
  2. Opens modal-auth-required:
     ┌───────────────────────────────────────────────────────────┐
     │                Authentication Required                    │
     │  To verify a property document, sign in or create an     │
     │  account to continue.                                     │
     │                                                           │
     │     [ Sign In ]              [ Create Account ]           │
     │                                                           │
     │    [ Continue as Demo User (SIH Demonstration Mode) ]     │
     └───────────────────────────────────────────────────────────┘
       │
       ▼
  User chooses:
  - Sign In: Enters credentials or selects 1-Click Role (Legal Verifier / Govt Officer / Admin)
  - Continue as Demo User: Automatically provisions authenticated Legal Verifier session
       │
       ▼
  Backend returns valid session token
  activeAuthToken = data.token
       │
       ▼
  SYSTEM RESUMES PENDING VERIFICATION SEAMLESSLY:
  1. closeModal('modal-auth-required')
  2. Restores file: selectedVerifyFile = window._pendingDocVerificationFile
  3. Ensures modal-doc-verify is active
  4. Automatically calls submitDocumentVerification()
  5. The user NEVER has to upload the PDF again!
```

---

## 3. Supported System Roles & Verification Permissions

| Role Identifier | Display Title | `VERIFY_DOCUMENT` | `REGISTER_DOCUMENT` | Access Description |
|---|---|:---:|:---:|---|
| `GOVERNMENT_OFFICER` | Government Revenue Officer | ✅ YES | ✅ YES | Full verification, ledger registration, OSINT investigation, policy simulations. |
| `LEGAL_VERIFIER` | Legal & Property Verifier | ✅ YES | ✅ YES | Dedicated verification role for title examiners, registrars, and banks. |
| `ADMIN` | System Administrator | ✅ YES | ✅ YES | Full system administrative oversight, audit log analysis, role management. |
| `RESEARCHER` | Land Economics Researcher | ❌ NO | ❌ NO | Read-only access to anonymized GIS, soil, weather, and research datasets. |
| `POLICYMAKER` | Urban & Rural Land Planner | ❌ NO | ❌ NO | Read-only macro planning, Section 90-A simulations. |
| `GUEST` | Unauthenticated Visitor | ❌ NO | ❌ NO | Public GIS map, weather, and soil viewing only. |

---

## 4. Session Lifetime & Logout Invalidation

1. **Token Storage:** Tokens are maintained in memory (`activeAuthToken`) and mirrored in `sessionStorage` (scoped strictly to the current browser tab session; cleared upon tab closure). Sensitive documents are never stored in `localStorage`.
2. **Session Expiry:** Backend tokens expire after 4 hours of inactivity. When a request receives HTTP 401:
   - Session state is cleared.
   - The user is notified: `"Session expired. Please sign in again to continue verification."`
   - Pending documents are preserved in active memory so the user can re-authenticate and immediately resume.
3. **Explicit Logout (`submitSecurityLogout()`):**
   - Calls `POST /api/v1/auth/logout` with Bearer token.
   - Backend invalidates the token in its active token registry.
   - Frontend purges `activeAuthToken`, `activeAuthUser`, and `sessionStorage`.
   - UI reflects unauthenticated guest state.
