# BHOOMI NEXUS — DATA PROVENANCE & ATTRIBUTION FRAMEWORK

### Transparency, Lineage Tracking & Legal Disclaimers for Public Land Intelligence

---

## 1. Principles of Data Provenance

Land administration is a statutory subject where the origin, reliability, and age of data determine its legal evidentiary value. The **Bhoomi Nexus Data Provenance Framework** enforces four core tenets:

1. **Mandatory Attribution**: No data element, parcel attribute, or spatial polygon may exist in the system without an attached `ProvenanceMetadata` record.
2. **Explicit Fact vs. Inference Separation**: Administrative facts (published RoRs, gazettes) are strictly segregated from remote-sensing inferences (satellite classifications) and user submissions.
3. **No Orphan Fields**: Aggregated canonical parcels preserve source references for every individual property attribute (area, classification, tenancy).
4. **Transparent Confidence Metrics**: Every source is mapped to an objective 1-to-5 star confidence rating based on statutory authority.

---

## 2. Five-Tier Provenance Taxonomy

```
+-------------------------------------------------------------------------+
| Level 1: VERIFIED_OFFICIAL_DATA (★★★★★)                                 |
| Official published state land records (Apna Khata, MP Bhulekh, AnyRoR)   |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
| Level 2: PUBLIC_GOVERNMENT_DATA (★★★★☆)                                 |
| Published statutory e-Gazette notifications, highway alignment orders   |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
| Level 3: REPUTABLE_PUBLIC_DATASET (★★★★☆)                               |
| OpenStreetMap cadastral layers, ISRO SAC Atlas, CGWB hydrology grids   |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
| Level 4: THIRD_PARTY_DATA (★★☆☆☆)                                       |
| Aggregated municipal listings, commercial real-estate indices           |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
| Level 5: AI_INFERRED_INFORMATION (★☆☆☆☆)                                |
| Machine-learning land cover classifications, NDVI trend extrapolations  |
+-------------------------------------------------------------------------+
```

---

## 3. Provenance Metadata Schema

Every ingested record and normalized canonical entity encapsulates:

```python
class ProvenanceMetadata:
    provenance_level: ProvenanceLevel       # One of the 5 formal tiers
    confidence_stars: int                  # 1 to 5 stars
    source_name: str                       # e.g., "Rajasthan Apna Khata (Revenue Dept)"
    source_url: Optional[str]              # e.g., "https://apnakhata.rajasthan.gov.in"
    retrieved_at: str                      # ISO 8601 UTC timestamp
    dataset_version: Optional[str]         # e.g., "RoR FY 2025-2026"
    license: str                           # Open Access / Public Record / ODbL 1.0
    verification_status: str               # "Verified Source Match"
    disclaimer: Optional[str]              # Mandatory statutory warning
```

---

## 4. Source Attribution & Licensing Matrix

| Data Provider | Provenance Level | Stars | License Type | Primary Attribution / Custodian |
| :--- | :--- | :---: | :--- | :--- |
| **Rajasthan Apna Khata** | `VERIFIED_OFFICIAL_DATA` | 5 | Government Open Access | Department of Revenue, Government of Rajasthan / NIC |
| **MP Bhulekh** | `VERIFIED_OFFICIAL_DATA` | 5 | Government Open Access | Commissioner of Land Records, Government of Madhya Pradesh |
| **Gujarat AnyRoR** | `VERIFIED_OFFICIAL_DATA` | 5 | Government Open Access | Revenue Department, Government of Gujarat / NIC |
| **OpenStreetMap** | `REPUTABLE_PUBLIC_DATASET` | 4 | Open Database License (ODbL 1.0) | OpenStreetMap Community & Contributors |
| **Copernicus Sentinel-2** | `REPUTABLE_PUBLIC_DATASET` | 4 | Creative Commons CC-BY 4.0 | European Space Agency (ESA) & European Union |
| **ISRO SAC Atlas** | `REPUTABLE_PUBLIC_DATASET` | 4 | Government Open Data (GODL) | Space Applications Centre (SAC), ISRO, Ahmedabad |
| **e-Gazette of India** | `PUBLIC_GOVERNMENT_DATA` | 4 | Public Record / Government Gazette | Directorate of Printing, Ministry of Housing & Urban Affairs |

---

## 5. Mandatory Statutory & Legal Disclaimers

### A. General Intelligence Dossier Notice
> **AUTOMATED INTELLIGENCE NOTICE:** This dossier is compiled from publicly accessible records, satellite observations, and open datasets for research and due-diligence prioritization only. It **DOES NOT constitute an official title certificate**, judicial determination, or government cadastral clearance. Final verification must be obtained from the competent Sub-Registrar and Revenue Authorities.

### B. Remote Sensing & Satellite Observation Disclaimer
> **PHYSICAL OBSERVATION NOTICE:** Satellite imagery observations reflect physical ground conditions, surface moisture, and visible vegetation/canopy reflectance at the time of overpass. Physical structures or lack thereof **do not constitute proof of lawful tenancy, title entitlement, or unauthorized encroachment**.

### C. Cryptographic Document Fingerprint Notice
> **CRYPTOGRAPHIC INTEGRITY NOTICE:** The SHA-256 digital fingerprint validates the exact byte-level uniqueness and tamper-free integrity of the uploaded digital file. It **DOES NOT certify statutory authenticity, official registration, or legal validity of the deed under the Indian Registration Act 1908**.
