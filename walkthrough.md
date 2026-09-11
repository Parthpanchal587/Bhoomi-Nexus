# Ask BHOOMI — Land Intelligence Engine Upgrade Walkthrough

## 1. Overview & Objective
Upgraded the existing **Ask BHOOMI / Land Intelligence Search** (`#modal-ai-ask`) from an ungrounded keyword essay generator into an authoritative, parcel-grounded, multi-intent land intelligence engine.

---

## 2. Root Causes Identified in the Existing Implementation

1. **Missing Parcel Context in Invocations**:
   - In `index.html` (lines 6399–6402), `runModalAIQuery()` sent `{ query: q, focus_region: "Rajasthan" }` without passing `lat`, `lon`, `khasra`, `district`, `tehsil`, `area`, or `land_classification`.
   - The backend was completely blind to which parcel the user had selected on the GIS map.
2. **Aggressive Client Timeout**:
   - `timeoutId = setTimeout(() => controller.abort(), 2500)` in `runModalAIQuery` aborted after only 2.5 seconds, immediately triggering fallback to `renderAIModalOffline(q)`.
3. **Static Regex Essay Generator**:
   - In `datasets.py` (`ask_bhoomi_intelligence`), the endpoint matched queries against hardcoded essay text blocks.
   - It lacked structured evidence objects, provenance tracking, and data statuses.
4. **False Fallbacks & Presumptive Answers**:
   - Missing data was often treated as negative confirmation (e.g. claiming "no court case exists" when litigation databases were not connected or queried).
5. **Unicode Normalization Flaw**:
   - Previous regex sanitizers stripped Unicode combining marks (matras) from Devanagari Hindi text (e.g. converting `मालिक` to `म ल क`), causing Hindi queries to fall through to `UNKNOWN_QUERY`.

---

## 3. Architecture & Key Changes

### Architecture Flow:
```
USER QUESTION (English / Hindi / Hinglish)
      ↓
QUERY NORMALIZER (Devanagari-safe Unicode preservation)
      ↓
INTENT DETECTOR (16+ Canonical Land Intents & Multi-Intent Parser)
      ↓
ACTIVE PARCEL CONTEXT (Selected lat/lon, Khasra, District, Tehsil, Area, Soil, Telemetry)
      ↓
RELEVANT DATA PROVIDERS (DILRMP, Jamabandi, BhuNaksha, CERSAI, NJDG, Open-Meteo, ISRIC SoilGrids)
      ↓
EVIDENCE & CONFIDENCE ENGINE (4-Tier Statuses: VERIFIED, PROVISIONAL, NOT_FOUND, UNAVAILABLE)
      ↓
STRUCTURED CITATIONS & PROVENANCE ENGINE
      ↓
BHOOMI RESPONSE
```

### 16+ Canonical Land Intents Implemented:
1. `LAND_OWNERSHIP_CLASSIFICATION` (Public/Govt vs Private Khatedari)
2. `TRIBAL_TRANSFER_RESTRICTION` (Section 42 statutory restrictions)
3. `REGISTERED_OWNER` (Registered Khatedar identification)
4. `TITLE_CHAIN_30_YEAR` (30-year mutation lineage and title deeds)
5. `DOCUMENT_AUTHENTICITY` (File integrity vs legal title distinction)
6. `TITLE_LITIGATION` (Clear title & court disputes; no match != no case)
7. `DOCUMENT_COMPLETENESS` (Mandatory clauses, stamps, witnesses)
8. `PROPERTY_RISK_SUMMARY` (Multi-factor analytical risk index)
9. `MORTGAGE_ENCUMBRANCE` (Bank charges, liens; unavailable != no loan)
10. `ENCUMBRANCE_CERTIFICATE` (Form 15 vs Form 16 search)
11. `PARCEL_IDENTITY_AREA` (Khasra/survey number & recorded area)
12. `BOUNDARIES` (North, South, East, West; imagery != legal boundary)
13. `SPATIAL_RESTRICTIONS` (Flood zones, railway/forest buffers)
14. `LAND_USE_CONVERSION` (Section 90-A Non-Agricultural diversion)
15. `MUNICIPAL_RERA_APPROVAL` (Master plan layout & RERA status)
16. `GENERAL_LAND_QUERY` (Structured 6-point due diligence checklist)
17. `UNKNOWN_QUERY` (Helpful guidance without hallucination)

---

## 4. Key Files Created & Modified

| File | Status | Description |
| :--- | :--- | :--- |
| `Bhoomi-Nexus/backend/app/services/land_intelligence.py` | **NEW** | Complete Land Intelligence Engine with intent detection, multi-intent extraction, Devanagari normalization, evidence creation, and 4-tier data states. |
| `api/app/services/land_intelligence.py` | **NEW** | Mirrored service file for deployment symmetry. |
| `Bhoomi-Nexus/backend/app/schemas/common.py` | **MODIFIED** | Added parcel, telemetry, soil, and document context to `AIQueryRequest`; extended `AIQueryResponse` with structured evidence, intent, data status, and provenance. |
| `api/app/schemas/common.py` | **MODIFIED** | Mirrored common schema. |
| `Bhoomi-Nexus/backend/app/routers/datasets.py` | **MODIFIED** | Refactored `POST /api/ai/query` to route directly through `LandIntelligenceEngine`. |
| `api/app/routers/datasets.py` | **MODIFIED** | Mirrored dataset router. |
| `index.html` & `Bhoomi-Nexus/frontend/index.html` | **MODIFIED** | Added `window.currentActiveParcel` binding, race-condition protection (AbortController + sequence tracking), active parcel banner, structured evidence list, status badges, and limitations box. |
| `tests/test_land_intelligence.py` | **NEW** | Comprehensive unit test suite covering 20 tests across all intents, languages, parcel switching, and multi-intent queries. |

---

## 5. Verification & Test Results

### 1. Unit & Integration Test Suite
```bash
python -m unittest discover -s tests -p "test_*.py"
```
**Result**:
```
Ran 46 tests in 8.970s
OK
```

### 2. Verified Test Cases
- **TEST 1**: "Who owns this land?" -> `REGISTERED_OWNER` [PASS]
- **TEST 2**: "kiske naam pe hai?" -> `REGISTERED_OWNER` [PASS]
- **TEST 3**: "इस जमीन का पंजीकृत मालिक कौन है?" -> `REGISTERED_OWNER` [PASS]
- **TEST 4**: "Is this government land?" -> `LAND_OWNERSHIP_CLASSIFICATION` [PASS]
- **TEST 5**: "govt hai ya private?" -> `LAND_OWNERSHIP_CLASSIFICATION` [PASS]
- **TEST 6**: "Any loan on this property?" -> `MORTGAGE_ENCUMBRANCE` [PASS]
- **TEST 7**: "mortgage hai?" -> `MORTGAGE_ENCUMBRANCE` [PASS]
- **TEST 8**: "Is there any court case?" -> `TITLE_LITIGATION` (Clear distinction: NO MATCH != NO CASE) [PASS]
- **TEST 9**: "30 year ownership history" -> `TITLE_CHAIN_30_YEAR` [PASS]
- **TEST 10**: "Can I build a house here?" -> `LAND_USE_CONVERSION` [PASS]
- **TEST 11**: "Is this document genuine?" -> `DOCUMENT_AUTHENTICITY` (Distinction: File integrity != Legal title) [PASS]
- **TEST 12**: "khasra number aur area batao" -> `PARCEL_IDENTITY_AREA` [PASS]
- **TEST 13**: "north boundary kya hai?" -> `BOUNDARIES` (Imagery != Cadastral boundary) [PASS]
- **TEST 14**: "Is this tribal land?" -> `TRIBAL_TRANSFER_RESTRICTION` [PASS]
- **TEST 15**: "RERA approved hai?" -> `MUNICIPAL_RERA_APPROVAL` [PASS]
- **TEST 16**: "Is this land safe to buy?" -> `GENERAL_LAND_QUERY` [PASS]
- **TEST 17**: Multi-intent: "Who owns this and does it have a mortgage?" -> Handled both `REGISTERED_OWNER` + `MORTGAGE_ENCUMBRANCE` [PASS]
- **TEST 18**: Parcel Context Switching: Verified switching from Amer (Jaipur) to Bengaluru updates coordinates, district, and khasra [PASS]
- **TEST 19**: Missing Context / Stale Requests: Gracefully flagged as `UNAVAILABLE` without hallucination [PASS]
- **TEST 20**: Unknown queries: Guided user to valid land queries without hallucinating land facts [PASS]
