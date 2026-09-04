# 🇮🇳 Bhoomi-Nexus: Quick Start & Commands Reference

---

## ⚡ Option 1: Run Directly from the Root Folder (Easiest)

Open PowerShell in `bhoomi-nexus`:

```powershell
# 1. Install dependencies
pip install -r Bhoomi-Nexus/backend/requirements.txt

# 2. Start the server (serves frontend + backend on port 8000)
python run.py
```

---

## ⚡ Option 2: Run from the `backend` Folder

If you prefer to `cd` into the backend directory:

```powershell
# 1. Navigate into backend (quotes are required because of spaces in username)
cd "Bhoomi-Nexus\backend"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python run.py
```

---

## 🌐 Accessing the Application

Once started, open in your browser:
- 🗺️ **Full Web GIS Application**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- 📖 **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 📑 **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Automated Testing

In a second terminal window (while the server is running):

```powershell
cd "Bhoomi-Nexus\backend"

python verify_v1_endpoints.py
python verify_endpoints.py
```
