# 🇮🇳 BHOOMI-NEXUS: Quick Start & Feature Guide

> National Cadastral GIS, LegalTech & Anti-Tamper Land Records System (NIC Style).

---

## ⚡ 3-Step Quick Start

### Step 1: Open Terminal in Backend Folder
```powershell
cd "c:\Users\Parth Panchal\Downloads\bhoomi-nexus\Bhoomi-Nexus\backend"
```

### Step 2: Install Dependencies (One-time setup)
```powershell
pip install -r requirements.txt
```
*(Zero external database required! Uses high-performance in-memory immutable ledger & real-time live internet GIS).*

### Step 3: Start the Backend Server
```powershell
python run.py
# Or:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

You will see:
```text
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

## 🌐 How to Use

- **Web Application Portal**: Open [http://localhost:8000/](http://localhost:8000/) or [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in any modern web browser.
- **Interactive Swagger API Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs).
- **Alternative ReDoc Docs**: Open [http://localhost:8000/redoc](http://localhost:8000/redoc).

---

## 🌟 Key Capabilities & Features

### 1. 🇮🇳 Pan-India Geographic Hierarchy (36 States & UTs)
- **Full Coverage**: Includes all 28 States and 8 Union Territories of India.
- **Dynamic Cascading Dropdowns**: Selecting any State automatically populates its respective Districts, and selecting a District populates its Tehsils.
- **India-Only Bounded Map**: The Leaflet GIS canvas is strictly bounded to India's territorial coordinates (`6.4°N, 68.0°E` to `37.5°N, 97.5°E`) with minimum zoom constraints to exclude the outer world map.

### 2. 📡 Real-Time Internet Land & House Details
- **Live Reverse Geocoding (`/api/geo/reverse?lat=...&lon=...`)**: Fetches real-time cadastral data directly from OpenStreetMap & NIC National Cadastral nodes for any point clicked on the map or selected from dropdowns.
- **Granular Building & Plot Inspection**:
  - **House / Plot No.** (भवन / भूखंड संख्या)
  - **Road / Street** (सड़क / मार्ग)
  - **Village / Mouza** (ग्राम / मौजा)
  - **Tehsil & District** (तहसील व जिला)
  - **Khasra Parcel Number** (खसरा संख्या)
  - **Cadastral Area** in Hectares & Acres
  - **Live Soil Moisture & Surface Temperature** via Open-Meteo Satellite Telemetry.

### 3. 🛡️ Anti-Tamper Document Verification (Zero-Tampering Security)
- Upload or drag-and-drop any deed or land record.
- Generates SHA-256 binary hash + perceptual fingerprint.
- Instantly matches against the immutable ledger:
  - **Identical Document**: `VERIFIED_AUTHENTIC` with block number and seal.
  - **Tampered Document**: `VERIFICATION_FAILED` alert.
- One-click register tool with live blockchain ledger recording.

### 4. 🌐 Full Bilingual Support (Hindi ⇄ English)
- Instant top-bar language switcher translating all labels, tables, inspector cards, toasts, and modal dialogs.
- Official Ashoka Stambh (अशोक स्तम्भ) National Emblem branding.

---

## 🧪 Automated Verification Scripts

In the `backend` directory, run:
```powershell
# Test core V1 modules (GIS, Policy, AI Ask, Legal Research, Document Verification):
python verify_v1_endpoints.py

# Test all system endpoints (Telemetry, Simulation, Blockchain verification, Datasets):
python verify_endpoints.py
```
