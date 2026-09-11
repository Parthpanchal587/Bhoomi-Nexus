# BHOOMI NEXUS — OSINT & Public-Source Land Intelligence Subsystem

### Government-Grade Land Intelligence, Due-Diligence Triage & Cross-Source Corroboration

---

## 1. Architectural Overview & Philosophy

The **Bhoomi Nexus OSINT (Open-Source Intelligence) Subsystem** is an automated, government-style due-diligence engine designed to discover, ingest, normalize, cross-check, and synthesize legally accessible public land records, cadastral surveys, multispectral satellite observations, and statutory government notifications.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 AUTHORIZED ANALYST / USER                              │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ REST API / Frontend Web UI
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              BHOOMI NEXUS OSINT ORCHESTRATOR                           │
│                      (FastAPI Route: /api/v1/osint/search, /report, etc.)               │
└─────┬───────────────────┬───────────────────┬───────────────────┬──────────────────────┘
      │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ State Land  │     │OpenStreetMap│     │ Sentinel-2  │     │  e-Gazette  │
│ Registries  │     │  Cadastral  │     │Multispectral│     │ Statutory   │
│ (RJ, MP, GJ)│     │ Boundaries  │     │ Remote Sens │     │Notifications│
└─────┬───────┘     └─────┬───────┘     └─────┬───────┘     └─────┬───────┘
      └───────────────────┼───────────────────┴───────────────────┘
                          │ Standardized SourceRecordEntry
                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         DATA PROVENANCE & NORMALIZATION ENGINE                         │
│               (5-Tier Attribution, Star Ratings, No-Orphan-Data Guarantee)             │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                       AUTOMATED CONFLICT & DISCREPANCY DETECTOR                        │
│          (Area Mismatch >5%, Land-Use Divergence, Boundary Non-Closure Alerts)         │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
┌─────────────────────────────────────────┐ ┌──────────────────────────────────────────┐
│        STATUTORY RESTRICTION ENGINE     │ │       TEMPORAL & TIMELINE ENGINE         │
│   • Section 42 RJ Tenancy Act (SC/ST)   │ │   • Multi-Year Timeline (2018–2026)      │
│   • Section 165 MP Land Revenue Code    │ │   • Rapid Successive Transfers (<90d)    │
│   • Section 73AA Gujarat Land Rev Code  │ │   • Physical vs Administrative Sequence  │
│   • NHAI Highway 60m ROW Buffer         │ └──────────────────┬───────────────────────┘
│   • Wildlife Sanctuary 1km ESZ Buffer   │                    │
└────────────────────┬────────────────────┘                    │
                     └────────────────────┬────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         COMPOSITE RISK SCORING ENGINE (0–100)                          │
│               [LOW: 0-20 | MEDIUM: 21-50 | HIGH: 51-75 | CRITICAL: 76-100]             │
│            *Strictly investigative triage — Never outputs "FRAUD CONFIRMED"*            │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
┌─────────────────────────────────────────┐ ┌──────────────────────────────────────────┐
│      EVIDENCE KNOWLEDGE GRAPH ENGINE    │ │   LAND EVIDENCE REPORT DOSSIER GENERATOR  │
│  (Nodes: Parcel, Mutation, Satellite,   │ │ (Cryptographic SHA-256 Digest, Structured │
│   Notification; Edges: HAS, OBSERVED)   │ │  JSON & Markdown, Legal Disclaimers)      │
└─────────────────────────────────────────┘ └──────────────────────────────────────────┘
```

---

## 2. Core Operational Constraints & Ethical Guardrails

1. **No People-Profiling or Doxxing**: Searches are strictly anchored on land parcels (Khasra, Survey Number, ULPIN, Centroid Lat/Lon, or Gazette notification). The engine never constructs personal identity graphs, scrapes private social media, or indexes leaked credentials.
2. **No Access-Control Bypass**: Operates strictly within legal public boundaries. Does not bypass CAPTCHAs, paywalls, or authentication sessions. Where state portals require interactive citizen sessions or encounter transient latency, the system seamlessly uses transparently labelled offline fallback records.
3. **Objective Inconsistency Indicators**: The engine flags discrepancies objectively (e.g., *"Cadastral survey reports 1.00 Ha whereas OSM/satellite footprint spans 1.25 Ha"*). It **never accuses any person or party of fraud**. Explanations such as unrecorded subdivision, roadside buffer deductions, or digitization variance are explicitly provided.
4. **Physical Observations vs. Legal Title**: Satellite remote-sensing observations (NDVI, surface moisture, built-up reflectance) reflect physical ground condition and **do not constitute statutory legal ownership or tenancy rights**.
5. **Cryptographic SHA-256 Scope**: The SHA-256 fingerprint generated during document cross-checking proves the exact digital byte uniqueness of the file; it does **not** certify statutory genuineness or government registration.

---

## 3. Data Provenance & Trust Hierarchy

Every field and record ingested by the subsystem is stamped with an immutable `ProvenanceMetadata` envelope adhering to a 5-tier classification:

| Tier Level | Provenance Enum | Rating | Description & Typical Data Sources |
| :--- | :--- | :---: | :--- |
| **Tier 1** | `VERIFIED_OFFICIAL_DATA` | ★★★★★ | Published state revenue department RoR extracts (*Apna Khata*, *MP Bhulekh*, *AnyRoR*). |
| **Tier 2** | `PUBLIC_GOVERNMENT_DATA` | ★★★★☆ | Statutory e-Gazette acquisition notices, highway alignment plans (NHAI), master plan reservations. |
| **Tier 3** | `REPUTABLE_PUBLIC_DATASET` | ★★★★☆ | OpenStreetMap vector boundaries, ISRO Space Applications Centre (SAC) Atlas, CGWB aquifer surveys. |
| **Tier 4** | `THIRD_PARTY_DATA` | ★★☆☆☆ | Aggregated commercial listings, unofficial local compilations. Requires independent revenue verification. |
| **Tier 5** | `AI_INFERRED_INFORMATION` | ★☆☆☆☆ | Machine learning land-cover classification, satellite NDVI change heuristics, automated discrepancy flags. |

---

## 4. Pluggable State Source Provider Architecture

State revenue records differ in schema, nomenclature, and access structure across India. The engine implements an extensible provider model:

- **`StateSourceProvider` (Abstract Base Class)**:
  - `state_code` & `state_name`
  - `portal_name` & `portal_url`
  - `search_parcel(query: OSINTSearchQuery) -> Optional[SourceRecordEntry]`
  - `get_source_metadata() -> ProvenanceMetadata`
- **Implemented State Connectors**:
  1. **Rajasthan (`RajasthanSourceProvider`)**: Connects to Apna Khata & BhuNaksha patterns (Tehsil, Village, Khasra, Jamabandi, and Mutation history).
  2. **Madhya Pradesh (`MadhyaPradeshSourceProvider`)**: Connects to MP Bhulekh (Khasra, Khatauni, B-1/P-II, Diversion orders).
  3. **Gujarat (`GujaratSourceProvider`)**: Connects to AnyRoR (Rural/Urban 7/12, 8A Khata, VF-6 mutation register).
- **Geospatial & Gazette Connectors**:
  - **OpenStreetMap (`OpenStreetMapProvider`)**: Overpass API querying with strict 4.5-second timeout, rate pacing, custom User-Agent, and shoelace area calculation.
  - **Public Satellite Provider (`PublicSatelliteProvider`)**: European Space Agency Copernicus Sentinel-2 multispectral surface reflectance and ISRO SAC Atlas historical indicators (2018–2026).
  - **Notification Provider (`GovernmentNotificationProvider`)**: e-Gazette notifications, Section 4 preliminary acquisition notices, and highway buffers.

---

## 5. Automated Conflict Detection Matrix

The `ConflictEngine` cross-references all acquired source entries against objective tolerance thresholds:

```python
# Area Discrepancy Tolerance: 5.0%
area_divergence = abs(primary_ha - competing_ha) / primary_ha * 100
if area_divergence > 5.0:
    severity = "HIGH" if area_divergence > 20.0 else "MEDIUM"
```

1. **Area Discrepancies**: Compares Cadastral RoR area vs. GIS OpenStreetMap vector area vs. User-declared deed area.
2. **Classification Divergence**: Detects mismatches where administrative records state *Agricultural (Chahi)* while satellite sensors observe *Built-up Commercial / Industrial structures*.
3. **Tenure Ambiguities**: Flags joint tenancy, missing mutation numbers, or unpartitioned family shares.

---

## 6. Statutory & Environmental Restriction Engine

The `LandRestrictionRuleEngine` evaluates jurisdiction-specific rules:

- **Tribal Land Transfer Bar (SC/ST Khatedari Protection)**:
  - *Rajasthan*: Section 42(b) of the Rajasthan Tenancy Act 1955.
  - *Madhya Pradesh*: Section 165(6) of the MP Land Revenue Code 1959.
  - *Gujarat*: Section 73AA of the Gujarat Land Revenue Code 1879.
- **Highway Infrastructure Right-of-Way Buffer (NHAI 60m)**:
  - Flags parcels abutting notified National Highways under Section 3A of the National Highways Act 1956.
- **Eco-Sensitive Zone (ESZ) Buffer (1 km Wildlife Sanctuary)**:
  - Flags parcels within Eco-Sensitive Zone corridors surrounding national parks and wildlife sanctuaries (e.g., Sariska, Gir, Ranthambore).

---

## 7. Multi-Year Temporal & Anomaly Engine

Tracks events across multi-year epochs (2018–2026) and scans for:
- **Rapid Successive Mutations**: Flags properties transferred more than twice in under 90 days (title flipping indicators).
- **Physical vs. Administrative Inversion**: Flags instances where satellite imagery detects physical construction years before official conversion orders (*CLUPA / Section 90-A*) were notified in the gazette.

---

## 8. Evidence Knowledge Graph

Constructs a structured topological graph:
- **Nodes**:
  - `PARCEL` (Root entity)
  - `KHASRA_RECORD` (State RoR snapshot)
  - `MUTATION` (Historical title transactions)
  - `SATELLITE_EVIDENCE` (Multispectral remote sensing passes)
  - `NOTIFICATION` (Statutory acquisition and zoning notifications)
  - `CONFLICT` (Cross-source discrepancies)
- **Edges**:
  - `HAS_KHASRA`, `BOUNDED_BY`, `MODIFIED_BY`, `MONITORED_BY`, `SUBJECT_TO_RESTRICTION`, `CONFLICTS_WITH`.

---

## 9. Security Controls & SSRF Defense

When querying external public endpoints:
1. **SSRF Guard (`app.osint.security`)**:
   - Strictly blocks private IP subnets (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`, `::1`, `fc00::/7`).
   - Resolves hostnames and validates all resolved IP addresses before initiating HTTP connections (DNS rebinding defense).
   - Enforces `http` and `https` scheme whitelisting.
2. **Domain Rate Limiter (`app.osint.rate_limiter`)**:
   - Token bucket algorithm enforcing domain-level pacing (default 10 req/min, 5 req/min for `.gov.in` and `.nic.in` domains) to respect server resources and terms of use.

---

## 10. REST API Endpoints

Mounted under `/api/v1/osint`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/osint/search` | Execute end-to-end multi-source intelligence discovery and reconciliation. |
| `GET` | `/api/v1/osint/providers` | List registered OSINT connectors, availability status, and licenses. |
| `POST` | `/api/v1/osint/cross-check` | Cross-check deed text against public registries; outputs SHA-256 hash. |
| `GET` | `/api/v1/osint/graph/{parcel_id}` | Retrieve synthesized Evidence Knowledge Graph data. |
| `GET` | `/api/v1/osint/timeline/{parcel_id}` | Retrieve multi-year chronological sequence and anomaly flags. |
| `POST` | `/api/v1/osint/report` | Generate official-grade Land Intelligence Evidence Dossier. |
| `GET` | `/api/v1/osint/restrictions` | Evaluate statutory and environmental buffer restrictions. |
| `GET` | `/api/v1/osint/audit` | View audit trail of executed queries and operator justifications. |

---

## 11. Verification & Testing

Run the automated test suites:
```bash
# Run complete OSINT test suite (19 tests)
python -m unittest tests/test_osint_module.py -v

# Run FastAPI OSINT endpoint integration tests (5 tests)
python -m unittest tests/test_osint_endpoints.py -v

# Run Secure Enclave (TEE) test suite (26 tests)
python -m unittest tests/test_secure_enclave.py -v
```
All test suites pass 100% with 0 errors and 0 regressions.
