# BHOOMI NEXUS — DEMO & PROTOTYPE ARCHITECTURAL LIMITATIONS

**System:** Bhoomi Nexus — National Land Intelligence & Cadastral Geospatial Engine  
**Document Purpose:** Accurate Technical Disclosure of Prototype Scope & Production Prerequisites  
**Context:** Smart India Hackathon (SIH) / GovTech Innovation Prototype  
**Classification:** Public Engineering Notice  
**Version:** 2.0  
**Last Updated:** September 2026  

---

## 1. Explicit Transparency Notice

BHOOMI-NEXUS is an advanced research and engineering prototype developed to demonstrate how modern web technologies, geospatial GIS, role-based access control, and cryptographic ledger verification can transform national land administration.

To maintain absolute integrity and compliance with Government of India digital standards:
- **NO Official Government Affiliation:** Bhoomi Nexus is an academic/hackathon prototype. It does not represent an official portal of the Ministry of Rural Development, Department of Land Resources (DoLR), or National Informatics Centre (NIC).
- **NO Real Citizen PII or Live Registry Binding:** The system operates using synthetic cadastral coordinates, demonstration deed records, and sandbox environment variables.
- **NO Real Government Identity Provider (IdP):** The platform DOES NOT integrate with Aadhaar e-KYC, DigiLocker production endpoints, or MeriPehchan SSO. All authentication is handled by the internal prototype identity system.

---

## 2. Functional Comparison: Prototype vs. Production

| Capability | Current Bhoomi Nexus Prototype | Production Government Deployment Requirement |
| :--- | :--- | :--- |
| **Authentication Provider** | In-memory PBKDF2-HMAC-SHA256 user database with pre-seeded demo accounts. | Integration with **MeriPehchan (National Single Sign-On)**, **Jan Parichay**, or state-level SSO portals with Aadhaar OTP / DigiLocker e-KYC verification. |
| **Session Persistence** | In-memory 256-bit bearer token store reset upon server restart. | Distributed **Redis Cluster** with signed, encrypted `HttpOnly`, `Secure`, `SameSite=Strict` cookies and Redis session replication. |
| **Password Management** | Fixed demo credentials for 5 roles seeded with cryptographic salt. | Dynamic user self-registration, mandatory multi-factor authentication (TOTP/FIDO2 hardware keys), and automated self-service password recovery via SMS/Email OTP. |
| **Sovereign Ledger** | In-memory SHA-256 block chain simulation with cryptographic hash linkage (`prev_hash + data`). | Permissioned distributed consortium ledger (e.g., **Hyperledger Fabric** or **NIC National Blockchain Framework**) with state-level validator nodes. |
| **File Storage** | Ephemeral in-memory byte buffer validation with `%PDF` magic byte inspection and SHA-256 fingerprinting. | Encrypted cloud object storage (**MinIO / S3 Glacier**) with antivirus scanning (`ClamAV`), strict tenant isolation, and legal retention compliance. |
| **Geospatial & Cadastral Data** | OpenStreetMap, ESRI public satellite tiles, and GeoJSON cadastral overlays for selected pilot zones (e.g., Jaipur, Delhi). | Official **Survey of India (SoI)** High-Resolution Orthorectified Imagery (ORI) and state revenue cadastral maps under National Geospatial Policy 2022. |
| **Section 90-A Simulator** | Rule-based mathematical calculator implementing the statutory fee structure of the Rajasthan Land Revenue Act. | State-integrated Urban Improvement Trust (UIT) and Jaipur Development Authority (JDA) land conversion workflows. |
| **Rate Limiting** | In-memory sliding-window token bucket per client IP (`RateLimiterMiddleware`). | Edge Web Application Firewall (**Cloudflare Enterprise / AWS WAF / NIC National Firewall**) with geo-blocking, DDoS mitigation, and bot management. |

---

## 3. Prototype Security Assumptions

1. **Single Node Environment:** In prototype mode, the application runs within a single FastAPI server process or serverless function context. The in-memory session cache and rate limiters are local to that instance.
2. **Demo Account Accessibility:** The pre-seeded accounts (`admin`, `officer`, `policymaker`, `researcher`, `verifier`) are publicly documented for evaluation convenience. In production, default credentials must be removed and replaced with database migration seeds requiring immediate initial password resets.
3. **Transport Security:** During local testing, endpoints run over plain HTTP (`http://127.0.0.1:8000`). In production deployments (such as Vercel HTTPS), strict HTTPS with HSTS (`max-age=31536000; includeSubDomains; preload`) is mandatory and automatically enforced by the application middleware.

---

## 4. Production Hardening Roadmap

Before deploying Bhoomi Nexus into a live state or national production infrastructure, the following engineering steps must be executed:

```
                                [ PRODUCTION ROADMAP ]
                                          │
       ┌──────────────────┬───────────────┴───────────────┬──────────────────┐
       ▼                  ▼                               ▼                  ▼
[ Database Layer ]  [ SSO Identity ]              [ Session Tier ]    [ Ledger Core ]
PostgreSQL + PostGIS  MeriPehchan / DigiLocker     Distributed Redis   Hyperledger Fabric
Encrypted at Rest    FIDO2 / TOTP MFA             HttpOnly Cookies    NIC Validator Nodes
```

1. **Persistent Database Migration:**
   - Replace in-memory dictionaries with **PostgreSQL 16 + PostGIS** for geospatial parcel indexing.
   - Use **SQLAlchemy 2.0 async** with connection pooling and automated Alembic schema migrations.
2. **Government SSO Integration:**
   - Integrate standard OpenID Connect (OIDC) / SAML 2.0 flows with **MeriPehchan** / **Jan Parichay**.
   - Validate digital signatures on e-Sign and e-KYC assertion tokens.
3. **Hardware Security Module (HSM):**
   - Anchor sovereign block signing keys inside a FIPS 140-2 Level 3 Hardware Security Module (HSM).
4. **Independent Third-Party VAPT:**
   - Commission a comprehensive Vulnerability Assessment & Penetration Testing (VAPT) audit by a CERT-In empanelled auditing agency.
   - Address any findings prior to formal Government authorization.
