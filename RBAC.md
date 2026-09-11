# BHOOMI NEXUS — ROLE-BASED ACCESS CONTROL (RBAC) ARCHITECTURE

**System:** Bhoomi Nexus — National Land Intelligence & Cadastral Geospatial Engine  
**Module:** Enterprise Authorization & Fine-Grained Permissions Engine  
**Classification:** Technical Security Specification  
**Version:** 2.0 (Defense-in-Depth)  
**Last Updated:** September 2026  

---

## 1. Architectural Philosophy: Deny-by-Default

Bhoomi Nexus enforces a **strict deny-by-default** access control model:
1. **Zero Implicit Privilege:** Any request to a protected endpoint is denied unless the caller proves identity AND holds the explicit atomic permission required for that exact action.
2. **Decoupled Roles and Permissions:** Business logic never checks raw role strings (e.g., `if user.role == 'admin'`). Instead, code checks atomic capabilities (`require_permission(Permission.REGISTER_DOCUMENT)`), enabling flexible role re-composition without refactoring endpoints.
3. **Dual-Layer Enforcement:**
   - **Frontend UI Guards:** Provide clear user feedback, contextual tooltips, and prevent invalid user states.
   - **Backend API Middleware:** Independent, authoritative cryptographic verification of permissions on every single request. Frontend guards are treated as UX affordances only, never security boundaries.

---

## 2. The Five System Roles + Guest Public Tier

| Role Enum | Official Title | Operational Scope |
| :--- | :--- | :--- |
| `GUEST` | **Public Visitor / नागरिक** | Unauthenticated public access to general land education, high-level cadastral boundary views, and basic research. |
| `GOVERNMENT_OFFICER` | **Government Officer / राजस्व अधिकारी (तहसीलदार / पटवारी)** | Authorized state and district revenue officials executing cadastral deed registration, land title verification, parcel ownership analysis, and policy compliance audits. |
| `POLICYMAKER` | **Policymaker / नीति विश्लेषक एवं नगर नियोजक** | Urban and rural planning authorities running Section 90-A land conversion simulations, master plan compliance modeling, and state-wide development analytics. |
| `RESEARCHER` | **Researcher / वैज्ञानिक एवं भू-स्थानिक शोधकर्ता** | Academic, ISRO, and environmental scientists analyzing multi-spectral satellite imagery, soil moisture telemetry, ecological zoning, and historical parcel topography. |
| `LEGAL_VERIFIER` | **Legal / Property Verifier / विधिक सत्यापनकर्ता** | Advocates, title search attorneys, and institutional banks performing cryptographic SHA-256 deed verification, sovereign ledger title search, and encumbrance checking. |
| `ADMIN` | **System Administrator / मुख्य प्रणाली प्रशासक** | Master cadastral administration, user lifecycle management, role provisioning, raw immutable security audit log examination, and system integrity oversight. |

---

## 3. Explicit Atomic Permission Catalog

```python
class Permission(str, Enum):
    # Public & Exploration Capabilities
    VIEW_PUBLIC_GIS       = "VIEW_PUBLIC_GIS"        # View base satellite and vector maps
    VIEW_PUBLIC_RESEARCH  = "VIEW_PUBLIC_RESEARCH"   # Access public circulars and articles
    USE_AI_BASIC          = "USE_AI_BASIC"           # Submit standard natural language queries
    USE_AI_FULL           = "USE_AI_FULL"            # Execute deep land intelligence reasoning

    # Intelligence & Analysis
    RUN_OSINT             = "RUN_OSINT"              # Trigger geospatial cross-source reconnaissance
    VIEW_OSINT_EVIDENCE   = "VIEW_OSINT_EVIDENCE"    # Inspect detailed cadastral evidence graphs
    RUN_POLICY_SIMULATION = "RUN_POLICY_SIMULATION"  # Run Section 90-A conversion calculators

    # Document & Sovereign Ledger Operations
    VERIFY_DOCUMENT       = "VERIFY_DOCUMENT"        # Compare document SHA-256 against ledger
    REGISTER_DOCUMENT     = "REGISTER_DOCUMENT"      # Notarize new property deed in blockchain ledger
    VIEW_LEDGER           = "VIEW_LEDGER"            # Inspect chronological block integrity
    WRITE_LEDGER          = "WRITE_LEDGER"           # Append sovereign blocks to ledger

    # Dataset & Administrative Operations
    MANAGE_DATASETS       = "MANAGE_DATASETS"        # Upload, sync, or purge parcel geo-datasets
    VIEW_AUDIT_LOGS       = "VIEW_AUDIT_LOGS"        # Read immutable system security audit logs
    MANAGE_USERS          = "MANAGE_USERS"           # Provision or de-provision user accounts
    MANAGE_ROLES          = "MANAGE_ROLES"           # Modify role-to-permission mappings
    ADMIN_SYSTEM          = "ADMIN_SYSTEM"           # Complete root platform authority
```

---

## 4. Complete Role-Permission Matrix

| Permission | GUEST | GOV OFFICER | POLICYMAKER | RESEARCHER | LEGAL VERIFIER | ADMIN |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `VIEW_PUBLIC_GIS` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `VIEW_PUBLIC_RESEARCH`| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `USE_AI_BASIC` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `USE_AI_FULL` | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `RUN_OSINT` | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ |
| `VIEW_OSINT_EVIDENCE`| ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| `VERIFY_DOCUMENT` | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| `REGISTER_DOCUMENT` | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| `VIEW_LEDGER` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `WRITE_LEDGER` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `MANAGE_DATASETS` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `RUN_POLICY_SIMULATION`| ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| `VIEW_AUDIT_LOGS` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `MANAGE_USERS` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `MANAGE_ROLES` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `ADMIN_SYSTEM` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 5. Server-Side Enforcement Mechanics

### 5.1 FastAPI Route Dependency Injection
All protected REST endpoints invoke the `require_permission(perm)` dependency:

```python
# app/services/auth.py
def require_permission(required_permission: Union[Permission, str]):
    def dependency(user: User = Depends(get_current_active_user)):
        if not auth_service.has_permission(user.role, required_permission):
            auth_service.log_audit(
                "AUTH_PERMISSION_DENIED",
                user.user_id,
                None,
                f"User {user.email} denied permission {required_permission}",
                severity="WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Role '{user.role.value}' does not possess required permission '{required_permission}'."
            )
        return user
    return dependency
```

### 5.2 Protected Endpoint Application
Example from `app/routers/documents.py`:
```python
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    ...
    current_user: User = Depends(require_permission(Permission.REGISTER_DOCUMENT))
):
    # Execution only proceeds if current_user possesses REGISTER_DOCUMENT
    ...
```

### 5.3 HTTP Status Code Semantics
- **`HTTP 401 Unauthorized`:** Caller provided no authentication credentials or an invalid/expired session token. The response header does not disclose internal system state.
- **`HTTP 403 Forbidden`:** Caller is authenticated and identity is verified, but their assigned role does not grant the atomic permission required for this resource.

---

## 6. Broken Access Control & IDOR Defense

Bhoomi Nexus guards against Insecure Direct Object References (IDOR):
1. **Unpredictable Object Identifiers:** Document IDs and ledger references use 128-bit cryptographically random hex strings (`uuid.uuid4().hex`) rather than sequential auto-incrementing integers (`/documents/1`, `/documents/2`).
2. **Server-Side Ownership Verification:** When accessing private document files or audit records, the backend verifies that the requesting user's `user_id` matches the document creator OR that the caller holds administrative audit clearance (`VIEW_AUDIT_LOGS`).
3. **Magic Bytes Validation at Ingestion:** Even authorized users cannot bypass file format integrity. Every deed upload is strictly checked for the `%PDF` binary header before processing.
