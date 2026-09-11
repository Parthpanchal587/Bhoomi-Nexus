# BHOOMI-NEXUS: Comprehensive Technical & Architectural Audit (Iteration 1)

**Audit Date:** September 2026  
**Scope:** Repository Structure, Application Configuration, Routes, Components, Data/API Integrations, Security-Sensitive Code, and Deployed Web Application (`bhoomi-nexus.vercel.app`).  
**Audit Objective:** Independent verification of implemented technical capabilities versus presentation-only/simulated features, security and compliance posture assessment, and preparation of an architectural baseline prior to subsequent iterations. **No application code was modified during this audit.**

---

## 1. Executive Summary

BHOOMI-NEXUS is designed as an end-to-end GovTech/PropTech decision-support prototype uniting Cadastral GIS mapping, satellite/soil telemetry, legal document due diligence, anti-tamper hash verification, land policy simulation (Rajasthan Section 90-A), and provenance tracking.

The prototype demonstrates a compelling domain concept and working technical workflows (e.g., geodesic shoelace polygon calculations, Open-Meteo telemetry integration, SHA-256 binary and text fingerprinting, rule-based zoning evaluation). However, this audit identified **critical prototype positioning risks, an architectural disconnect between backend V1 endpoints and frontend views, and several security vulnerabilities**:

1. **Unsafe Government Branding & False Authority Claims:**  
   The deployed site and codebase present the system as an official Government of India portal developed and hosted by the **National Informatics Centre (NIC)**, claiming an active **"NIC Meghraj Node: ONLINE"**, direct live links to official state cadastral registries, and statutory evidentiary standing under the Indian IT Act. In reality, no government backend, NIC API, or live state cadastral database connection exists. This violates prototype safety guidelines.
2. **Monolithic Frontend Architecture with Orphaned Backend Endpoints:**  
   The frontend consists of a single 3,978-line monolithic HTML file (`index.html`) combining embedded styles, SVGs, Leaflet map scripts, and inline JavaScript. While newly designed modular V1 backend routers exist for GIS Analysis, Policy Evaluation, and Document Due Diligence, **the frontend UI has not integrated four of the five V1 endpoints** (`/api/v1/gis/analyze`, `/api/v1/policy/evaluate`, `/api/v1/ai/ask`, `/api/v1/ai/research`). The frontend remains tightly coupled to legacy endpoints.
3. **Simulated vs. Real Capability Divergence:**  
   The platform advertises "98.4% Confidence AI", "Sovereign Blockchain Ledger", and "Direct Cadastral Alignment". In the codebase:
   - "Blockchain" is an ephemeral, in-memory Python list with a 500-iteration nonce loop.
   - "Cadastral Parcels" are either fetched from OpenStreetMap Overpass or synthetically generated 6-sided polygons calculated using coordinate offsets around user clicks.
   - "Ask BHOOMI RAG" uses regular-expression keyword categorization returning hardcoded paragraphs with hardcoded confidence percentages (e.g., `98.1%`, `99.2%`), falling back to Google Gemini only if an API key is passed in the request body.
4. **Security & Serverless Persistence Deficits:**  
   - Zero authentication, authorization, or role-based access control (RBAC).
   - Unrestricted file upload endpoints (`/api/v1/documents/upload`) with no file size limits, MIME-type validation, or memory protection.
   - Insecure CORS configuration (`allow_origins=["*"]` with `allow_credentials=True`).
   - Purely in-memory storage: When hosted as serverless functions on Vercel, all uploaded documents, verification audit logs, and notarized ledger blocks are erased on container recycle or cold start.

---

## 2. Repository & Deployment Architecture

### 2.1 Directory Structure & Monorepo Duplication

The workspace exhibits a duplicate/hybrid root structure:

```text
bhoomi-nexus/
├── .gitignore
├── README.md                      <- Root documentation & setup instructions
├── read.md                        <- Quick-access instructions
├── vercel.json                    <- Serverless routing configuration
├── requirements.txt               <- Root Python dependencies for Vercel
├── run.py                         <- Root launcher (adds Bhoomi-Nexus/backend to sys.path)
├── index.html                     <- 215 KB Monolithic Frontend (served by Vercel)
├── ashoka_stambh.png / .svg       <- State Emblem of India graphical assets
├── india_mask.json / boundary.json<- GeoJSON boundaries
├── api/
│   └── index.py                   <- Vercel serverless entrypoint (mounts app.main)
└── Bhoomi-Nexus/
    ├── README.md
    ├── frontend/
    │   ├── index.html             <- Exact duplicate of root index.html (215 KB)
    │   ├── ashoka_stambh.png
    │   └── india_boundary.json
    └── backend/
        ├── run.py                 <- Local Uvicorn server launcher (port 8000)
        ├── requirements.txt       <- Backend-specific dependency manifest
        ├── test_overpass.py       <- Standalone Overpass API test script
        ├── verify_endpoints.py    <- Test script for legacy endpoints
        ├── verify_v1_endpoints.py <- Test script for new V1 modular routers
        └── app/
            ├── __init__.py
            ├── config.py          <- Static settings, dataset catalogs & district baselines
            ├── main.py            <- FastAPI app factory & router mounter
            ├── models/            <- In-memory Pydantic models (document.py)
            ├── schemas/           <- Request/response validation schemas
            ├── routers/           <- Modular route controllers (11 routers)
            ├── services/          <- Business logic (AI, Blockchain, GIS, Policy, Docs)
            └── utils/             <- Geodesic math helpers & PDF text extractors
```

### 2.2 Dual-File Synchronization Hazard

- `index.html` exists simultaneously at the root and in `Bhoomi-Nexus/frontend/index.html`.
- On Vercel, static requests serve root `index.html`.
- When running locally via `run.py`, FastAPI serves `Bhoomi-Nexus/frontend/index.html` via `app.mount("/static", ...)` and root route `FileResponse`.
- **Finding:** Developers editing one file without copying to the other create divergence between local development and cloud deployment.

### 2.3 Dependency Manifest Inconsistency

- Root `requirements.txt` specifies: `pypdf>=4.0.0`
- Backend `requirements.txt` specifies: `PyPDF2>=3.0.0`, `shapely>=2.0.0`, `requests>=2.28.0`
- In `app/utils/pdf_extractor.py`, line 12 explicitly executes: `from PyPDF2 import PdfReader`.
- **Finding:** Root `requirements.txt` lacks `PyPDF2`. In Vercel serverless builds relying solely on root `requirements.txt`, any call to PDF extraction routes triggers an `ImportError` unless `PyPDF2` is bundled or resolved.

### 2.4 Serverless In-Memory State Loss

- Both `InMemoryLedger` (`app/services/document_verification.py`) and `BlockchainLedger` (`app/services/blockchain.py`) store state exclusively in Python instance variables (`self._records_by_id = {}`, `self.chain = []`).
- **Finding:** Vercel functions run in ephemeral, stateless lambda execution environments. Any document uploaded via `/api/v1/documents/upload` or block added via `/api/blockchain/notarize` is lost as soon as the lambda container terminates or a request is routed to a different instance.

---

## 3. Frontend Inspection & UI/UX Audit

### 3.1 Monolithic Structure

- File size: 215 KB (3,978 lines in a single file).
- Contains ~1,200 lines of CSS styles, ~450 lines of HTML markup, and ~2,300 lines of JavaScript.
- Lacks a modular component framework (React, Vue, or modular Vanilla ES modules).
- All features (GIS map, satellite telemetry, document upload, document verification, dataset catalog, research publications, policy simulator, blockchain ledger) are crammed into a single page and triggered via modal popups (`openModal('modal-doc-verify')`, `openModal('modal-ai-ask')`, etc.).

### 3.2 Visual Hierarchy & Cognitive Load

- The screen is overly dense: the map visualizer, layer switchers, state/district dropdowns, coordinate indicators, live telemetry cards, Section 90-A calculator, and top ticker all compete for visual priority.
- Primary navigation does not represent a clean workflow-based routing structure:
  - Missing standalone routes for: **Home**, **Land Explorer**, **GIS Intelligence**, **Ask BHOOMI AI**, **Policy Simulator**, **Research & Evidence**, **Document Verification**, and **Trust Ledger**.
  - Current tabs mix interactive UI toggles with modal window triggers.

### 3.3 Internationalization (Bilingual Hindi/English)

- An in-memory JavaScript dictionary (`TRANSLATIONS = { hi: {...}, en: {...} }`) handles client-side bilingual rendering.
- Defaults to Hindi (`hi`) on first visit.
- While bilingual support is a strong accessibility feature, certain technical and legal terms in Hindi are translated in a way that sounds authoritative and governmental (e.g., "राजस्व संप्रभु सीमा", "सॉवरेन ब्लॉकचेन लेज़र"), intensifying the false impression of an official state agency.

---

## 4. Backend & API Route Audit

### 4.1 Route Catalog & Endpoints

| Route Path | HTTP Method | Router File | Status & Implementation Reality |
| :--- | :--- | :--- | :--- |
| `/api` | GET | `health.py` | Operational; returns static JSON metadata and node status |
| `/api/health` | GET | `health.py` | Operational; reports in-memory blockchain block count |
| `/api/geo/search` | GET | `geo.py` | Operational; queries OpenStreetMap Nominatim with offline fallback |
| `/api/geo/reverse` | GET | `geo.py` | Operational; Nominatim reverse geocode with nearest-admin fallback |
| `/api/geo/hierarchy` | GET | `geo.py` | Static catalog of 28 States + 8 UTs with districts and tehsils |
| `/api/geo/cadastral-features` | GET | `geo.py` | Queries OSM Overpass; falls back to synthetic coordinate math |
| `/api/telemetry/live` | GET | `telemetry.py` | Real integration with Open-Meteo forecast API + synthetic fallback |
| `/api/simulate` | POST | `simulation.py` | Mathematical calculator for Sec 90-A conversion & groundwater metrics |
| `/api/blockchain/ledger` | GET | `blockchain.py` | Returns in-memory block list (Genesis + pre-seeded catalog blocks) |
| `/api/blockchain/notarize` | POST | `blockchain.py` | Appends a block with SHA-256 hash using 0-prefix/500-nonce loop |
| `/api/blockchain/verify-dataset` | POST | `blockchain.py` | Compares hardcoded string hashes; fakes tamper if flag is true |
| `/api/datasets` | GET | `datasets.py` | Returns 5 static catalog entries from `config.py` |
| `/api/datasets/{id}` | GET | `datasets.py` | Returns single static catalog entry |
| `/api/research` | GET | `datasets.py` | Returns 3 static research paper entries from `config.py` |
| `/api/ai/query` | POST | `datasets.py` | Regex-based keyword matcher returning hardcoded essay paragraphs |
| `/api/insights/briefings` | GET | `insights.py` | Returns 3 static cabinet briefing notes |
| `/api/policy/simulate-v2` | POST | `insights.py` | Multi-variable policy intervention calculator |
| `/api/v1/documents/upload` | POST | `documents.py` | **V1:** Computes SHA-256 and text fingerprint, stores in memory |
| `/api/v1/documents/verify` | POST | `documents.py` | **V1:** Matches binary hash or text fingerprint against memory |
| `/api/v1/ai/ask` | POST | `ai.py` | **V1:** Regex chunking + keyword scoring + Gemini API (Orphaned in UI) |
| `/api/v1/ai/research` | POST | `ai.py` | **V1:** Rule-based title deed analysis + risk scoring (Orphaned in UI) |
| `/api/v1/gis/analyze` | POST | `gis.py` | **V1:** Polygon area, centroid, bounding box & buffer alerts (Orphaned in UI) |
| `/api/v1/policy/evaluate` | POST | `policy.py` | **V1:** Zoning matrix, FAR limits & setback compliance (Orphaned in UI) |

### 4.2 The Orphaned V1 Backend Problem

While the backend architecture was significantly refactored into clean modular V1 routers in `app/routers/` and `app/services/`:
- The frontend `index.html` **only interacts with `/api/v1/documents/upload` and `/api/v1/documents/verify`**.
- The frontend AI modal calls `/api/ai/query`, not `/api/v1/ai/ask` or `/api/v1/ai/research`.
- The frontend GIS map computes polygon geometry client-side and calls `/api/geo/cadastral-features`, completely ignoring `/api/v1/gis/analyze`.
- The frontend Section 90-A tab calls `/api/simulate`, completely ignoring `/api/v1/policy/evaluate`.
- **Finding:** The modernized V1 modular logic is currently dead code from the user interface perspective.

---

## 5. Implemented vs. Presentation-Only & Simulated Matrix

| Feature Area | User-Facing / Deployed Claim | Actual Codebase Implementation | Classification |
| :--- | :--- | :--- | :--- |
| **Authority & Hosting** | "Government of India", "Ministry of Rural Development", "Hosted by NIC" | Independent hobby/hackathon repository with zero official hosting or affiliation | **FABRICATED / UNSAFE** |
| **Infrastructure Node** | "NIC Meghraj Node: ONLINE" | Static badge in HTML header (`#86EFAC` green dot); no connection to Meghraj cloud | **SIMULATED UI ONLY** |
| **Cadastral Link** | "Direct link verified with Rajasthan & Karnataka land-record databases" | Hardcoded string in HTML marquee. No API calls to Bhunaksha, Apna Khata, or Bhoomi Karnataka | **FABRICATED** |
| **Cadastral Parcels** | Real-time Cadastral Survey Khasra Boundaries (BhuNaksha 1:1000) | Queries OSM Overpass for `landuse=farmland`; if empty, generates synthetic offset polygon | **SYNTHETIC / DERIVED** |
| **Soil & Environmental Data** | Live Satellite Telemetry & Multi-Spectral Ground Index | Real GET request to Open-Meteo public forecast API; falls back to static float values | **REAL EXTERNAL API** |
| **Policy & Conversion** | Section 90-A Conversion Calculator & Diversion Fee Modeling | Mathematical formula in `simulation.py` and `policy_engine.py` using statutory tariffs | **REAL LOGIC (Deterministic)** |
| **Document Anti-Tamper** | "Zero-tamper security", "Legal evidence under IT Act" | Computes standard SHA-256 hex digest of file bytes and normalized string; matches in-memory | **REAL CRYPTO / NO LEGAL WEIGHT** |
| **Blockchain Ledger** | "Sovereign Blockchain Ledger", "NIC Sovereign Cadastral Trust" | Ephemeral Python list with dummy nonce loop; no P2P consensus, no distributed nodes | **MOCK / SIMULATED** |
| **AI RAG Search** | "Google Gemini Live Cloud RAG", "98.4% Confidence" | Regex keyword match returning pre-written text with hardcoded confidence (e.g., 98.7) | **SIMULATED (unless key provided)** |
| **AI Legal Title Check** | "Who is registered owner?", "Tribal land purchase legality" | Pattern matching over plain text; prompt template for optional Gemini API | **HEURISTIC EXPERIMENTAL** |
| **Scientific Research** | Peer-Reviewed Research Repository (ISRO, CAZRI, CGWB) | Static list of 3 pre-written dictionary objects in `config.py` | **STATIC CURATED SAMPLE** |

---

## 6. Security & Vulnerability Assessment

### 6.1 Critical Vulnerabilities

1. **Unrestricted File Uploads (Denial of Service & Crash Hazard):**  
   - Location: `app/routers/documents.py` (`upload_document` and `verify_document_endpoint`).  
   - Implementation: `file_bytes = await file.read()`.  
   - Risk: The server reads the entire file into server RAM without checking content-length headers or stream size limits. An attacker uploading a 1GB or 5GB file can instantly exhaust memory on the host or serverless container, triggering a Denial of Service (DoS).  
   - File Types: No MIME-type or file magic header validation. Any executable, script, or binary can be submitted.

2. **Absence of Authentication, Authorization & RBAC:**  
   - Location: Entire application.  
   - Risk: All endpoints are completely open and unauthenticated. Any user on the public internet can upload documents, trigger OCR/PDF parsing, add blocks to the blockchain ledger, and run simulations without rate-limiting or identity verification.

3. **Insecure CORS Configuration:**  
   - Location: `app/main.py` lines 44-50:
     ```python
     app.add_middleware(
         CORSMiddleware,
         allow_origins=["*"],
         allow_credentials=True,
         allow_methods=["*"],
         allow_headers=["*"],
     )
     ```
   - Risk: Combining `allow_origins=["*"]` with `allow_credentials=True` violates standard browser security specifications (CORS RFC 6454). Modern browsers block credentials with wildcard origins, and tools flag this as an exploitable misconfiguration.

4. **Client-Side API Key Transmission & Injection Risks:**  
   - Location: `app/routers/datasets.py`, `app/routers/ai.py`, and `app/services/ai_ask.py`.  
   - Implementation: User-supplied `api_key` is passed via plaintext JSON payload in HTTP requests.  
   - Risk: If intercepted or logged, user API keys are exposed. Furthermore, user questions are concatenated directly into LLM prompts without structured delimiter framing or prompt injection filtering.

5. **Authoritative Legal Output Liability:**  
   - The platform generates definitive answers to questions such as:
     - *"Can OBC/General buy SC/ST Tribal land?"*
     - *"Who is the registered legal owner?"*
     - *"Clear Title & Court Litigation Check"*
   - Risk: Presenting these outputs under a Government of India badge creates serious legal liability. If a user relies on this prototype for real-world land purchases, boundary disputes, or title transactions, false conclusions could lead to financial or legal harm.

---

## 7. Product Positioning & Compliance Recommendations

To align with prototype-safe guidelines for the upcoming iterations:

1. **Remove All Government Impersonation:**
   - Remove the State Emblem of India (`ashoka_stambh.png` / `ashoka_stambh.svg`).
   - Remove "Government of India", "Ministry of Rural Development", "Department of Land Resources", and "National Informatics Centre (NIC)".
   - Remove fictitious email references (`contact@bhoomi-nexus.nic.in`) and fake node IDs (`NIC-GEO-NODE-IND-DEL-01`).
   - Remove "NIC Meghraj Node: ONLINE" and claims of direct alignment with state revenue databases.
2. **Implement Prominent Prototype & Disclaimer Banners:**
   - Add a persistent prototype badge: **"RESEARCH & DEMONSTRATION PROTOTYPE — NOT AN OFFICIAL GOVERNMENT PORTAL"**.
   - Add explicit legal and AI disclaimers:
     > *"BHOOMI-NEXUS is an experimental decision-support prototype developed for research and technology demonstration purposes. It does not provide authoritative legal title certificates, official cadastral records, or statutory determinations. Cadastral maps and regulatory simulations are illustrative and must be verified with competent revenue authorities."*
3. **Transparent Data Provenance & Confidence Metrics:**
   - Clearly label the true source of all data:
     - OpenStreetMap / Overpass for road and agricultural polygons.
     - Open-Meteo for meteorological and soil indicators.
     - Synthetic / Algorithmic Model for simulated parcel boundaries.
     - Curated Academic Whitepapers for research references.
   - Replace arbitrary confidence scores (`98.4% Confidence`, `99.2% Confidence`) with transparent heuristic indicators: "Evidence Matches: 4/5 Checklist Items", "Exact SHA-256 Match", or "Semantic Keyword Correlation: Medium".
4. **Clarify "Trust Ledger" Scope:**
   - Reframe the blockchain module from a "National Sovereign Blockchain" to an **"Artifact Integrity Ledger (SHA-256 Verifiable Hash Chain)"**.

---

## 8. Strategic Roadmap (Iteration 2 & Beyond)

Based on this audit, the recommended implementation plan for subsequent iterations is structured as follows:

| Stage | Milestone | Primary Objectives | Complexity |
| :--- | :--- | :--- | :--- |
| **Iteration 2** | **Branding, Disclaimers & App Shell** | Strip government emblems and NIC claims; add prototype disclaimers; build unified design system and multi-view navigation (Home, Explorer, GIS, AI, Policy, Evidence, Verification, Ledger). | Medium |
| **Iteration 3** | **Frontend Decomposition & Modular Routing** | Break monolithic `index.html` into clean, maintainable view modules; eliminate root/subfolder duplication; ensure single source of truth for Vercel and local runs. | Medium-High |
| **Iteration 4** | **Backend V1 Integration & Security Hardening** | Connect frontend views to the orphaned V1 backend routers (`/api/v1/gis`, `/api/v1/policy`, `/api/v1/ai`); enforce file size limits (max 10MB) and PDF validation; fix CORS and dependencies. | High |
| **Iteration 5** | **GIS & Land Explorer Overhaul** | Integrate proper Leaflet/MapLibre layers; display accurate bounding boxes, coordinates, geodesic metrics, and explicit "Synthetic Parcel Demo" vs "Live OSM" source tags. | High |
| **Iteration 6** | **Transparent Policy & Trust Verification** | Make Section 90-A calculations completely transparent with exposed formulas and assumptions; rename Blockchain to Integrity Ledger with downloadable verification receipts. | Medium |
| **Iteration 7** | **Final Quality Assurance & Verification** | Run automated end-to-end tests (`verify_v1_endpoints.py`), browser audit across responsive breakpoints, and create `FINAL_AUDIT.md`. | Medium |

---

*End of Audit — Proceeding to Iteration 2 upon review.*
