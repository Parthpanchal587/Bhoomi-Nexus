# 🇮🇳 BHOOMI-NEXUS: National Land Intelligence & Cadastral Engine

> **GovTech & PropTech Platform** for Anti-Tamper Document Verification, AI Legal Due Diligence, Geospatial (GIS) Land Validation, and Policy & Zoning Compliance.

---

## 🚀 Quick Start Guide (How to Run the Code)

Follow these simple steps to run Bhoomi-Nexus on your machine:

### 1. Prerequisites
- **Python 3.10 or higher** installed on your system.
  - Check with: `python --version`
- A modern web browser (Chrome, Edge, Firefox, Brave, etc.).
- **No database required!** The entire system runs purely in-memory — zero SQLite/PostgreSQL setup needed.

---

### 2. Run Options

#### Option A: Run directly from Root (Recommended)
You do not need to `cd` into any subfolder:
```powershell
# 1. Install dependencies
pip install -r Bhoomi-Nexus/backend/requirements.txt

# 2. Start the server
python run.py
```

#### Option B: Run from the `backend` folder
If you want to navigate into the backend folder, make sure to use quotation marks around the path because of folder spaces:
```powershell
# 1. Change directory to backend
cd "Bhoomi-Nexus\backend"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python run.py
# Or with uvicorn:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see output like:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

### 5. Open the Web Application & Documentation

| Service | URL / Action |
| :--- | :--- |
| 🌐 **Web Frontend** | Open `http://127.0.0.1:8000/` in your browser, or double-click `Bhoomi-Nexus/frontend/index.html` |
| 📖 **Interactive Swagger Docs** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Try out any API endpoint in your browser) |
| 📑 **ReDoc Documentation** | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) |

---

### 6. Run the Verification Tests
To automatically test and verify that every feature is working properly:

```powershell
# In the backend directory:

# 1. Test all 5 New V1 Modules (GIS, Policy, AI Ask, AI Research, Document Tamper Verification):
python verify_v1_endpoints.py

# 2. Test Full System Integration (Health, Telemetry, Simulation, Blockchain, Datasets):
python verify_endpoints.py
```

Both test scripts will output:
`ALL MODULES VERIFIED & PASSING WITH 100% SUCCESS!`

---

## 🧩 Core Capabilities & API Endpoints

### 1. 🛡️ Anti-Tamper & Document Verification Engine
- **`POST /api/v1/documents/upload`**: Upload and register a deed/record in the in-memory ledger. Computes SHA-256 binary hash and text fingerprint.
- **`POST /api/v1/documents/verify`**: Checks a PDF against registered records.
  - If exact match: returns `VERIFIED_REAL`.
  - If modified, re-saved, or unknown: returns `VERIFICATION_FAILED` (`"Document is NOT REAL or has been tampered with. Signature and hash mismatch."`).

### 2. 💬 AI "Ask Your Document" Q&A
- **`POST /api/v1/ai/ask`**: Ask questions in plain English (e.g., *"Is there any mortgage or lien clause?"*, *"Who owns the boundary to the North?"*).
  - Returns concise answers, confidence scores, and verbatim citation excerpts with section labels.

### 3. ⚖️ Autonomous Legal Title & Risk Research
- **`POST /api/v1/ai/research`**: Performs deep title deed due diligence:
  - Generates **Risk Score (0–100)** and **Clarity Score (0–100)**.
  - Extracts **Chain-of-Title** (transfers, deed dates, continuity status: COMPLETE/PARTIAL/BROKEN).
  - Flags **Encumbrances** (bank mortgages, court litigation, easements).
  - Identifies **Missing Statutory Elements** (stamp numbers, witness signatures, schedules).

### 4. 🗺️ GIS & Spatial Land Validation Engine
- **`POST /api/v1/gis/analyze`**:
  - Calculates true geodesic polygon area (hectares, acres, sq. meters) and centroid.
  - Validates survey plot boundaries and polygon closure.
  - Proximity buffer analysis: detects hazardous proximity to railway corridors, water bodies, high-tension powerlines, and highways.

### 5. 🏗️ Policy & Zoning Compliance Engine
- **`POST /api/v1/policy/evaluate`**:
  - Checks proposed use against zones (Agricultural, Commercial, Residential, Industrial, Green Belt).
  - Evaluates maximum Floor Area Ratio (FAR), Ground Coverage %, and setbacks.
  - Evaluates Section 90-A land conversion diversion criteria and expected approval timelines.

---

## 📁 Project Directory Structure

```text
bhoomi-nexus/
├── README.md                  <- This guide
├── read.md                    <- Quick-access instructions
└── Bhoomi-Nexus/
    ├── frontend/
    │   └── index.html         <- GIS Map, Satellite Visualizer & Command Center
    └── backend/
        ├── run.py             <- Server startup script (`python run.py`)
        ├── requirements.txt   <- Python package dependencies (no database required)
        ├── verify_v1_endpoints.py <- Automated test script for all 5 v1 modules
        ├── verify_endpoints.py    <- Automated test script for all 8 system endpoints
        └── app/
            ├── main.py        <- FastAPI app factory & router mounter
            ├── config.py      <- App settings & configuration
            ├── models/        <- In-memory document and verification log models
            ├── schemas/       <- Pydantic request & response schemas
            ├── services/      <- Business logic (GIS, Policy, AI, Document Verification)
            ├── routers/       <- Clean modular FastAPI route handlers
            └── utils/         <- Geodesic math helpers & PDF text extractors
```

---

## ❓ Frequently Asked Questions (FAQ)

**Q: Do I need to install or configure any SQL database (SQLite, MySQL, PostgreSQL)?**  
**A:** No! All verification records and models operate in-memory. No database drivers, migrations, or local database files are needed.

**Q: Where can I test the endpoints without writing code?**  
**A:** With the server running, navigate to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). It provides an interactive Swagger UI where you can test every endpoint directly.
