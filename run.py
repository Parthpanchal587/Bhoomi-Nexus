"""
BHOOMI-NEXUS Root Launcher
Allows running `python run.py` directly from the project root directory.
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent / "Bhoomi-Nexus" / "backend"
if backend_dir.exists():
    sys.path.insert(0, str(backend_dir))
    os.chdir(str(backend_dir))

if __name__ == "__main__":
    import uvicorn

    print("🇮🇳 Starting Bhoomi-Nexus Land Intelligence Server on http://127.0.0.1:8000 ...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
