# 🇮🇳 Bhoomi-Nexus Backend

FastAPI backend engine for GovTech Cadastral & Land Intelligence (Zero Database Setup Required).

---

## ⚡ Quick Start: How to Run

### Method 1: Running from Root Directory (Recommended)
Open your terminal in `bhoomi-nexus`:
```powershell
# 1. Install dependencies
pip install -r Bhoomi-Nexus/backend/requirements.txt

# 2. Start the server
python run.py
```

---

### Method 2: Running from Backend Directory
If you navigate inside the `backend` folder (make sure to use quotes if your folder path has spaces):
```powershell
# 1. Change directory to backend
cd "Bhoomi-Nexus\backend"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python run.py
```

Alternatively with Uvicorn:
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌐 Web Interface & API Documentation

Once the server is running:
- **Web App**: Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.
- **Interactive Swagger Docs**: Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Docs**: Open [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Automated Testing

While the server is running on port 8000, open a separate terminal inside the `backend` folder and run:

```powershell
cd "Bhoomi-Nexus\backend"

# Test all V1 modules:
python verify_v1_endpoints.py

# Test full system integration:
python verify_endpoints.py
```
