import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))

possible_paths = [
    current_dir,
    os.path.join(current_dir, "app"),
    os.path.join(root_dir, "Bhoomi-Nexus", "backend"),
    os.path.join(current_dir, "..", "Bhoomi-Nexus", "backend"),
    os.path.join(root_dir, "backend"),
    os.path.abspath("Bhoomi-Nexus/backend"),
    os.path.abspath("backend"),
]

for p in possible_paths:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.main import app
except Exception as e:
    import traceback
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI(title="Bhoomi-Nexus Diagnostic Fallback")
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def vercel_diag_fallback(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Bhoomi-Nexus Serverless Module Initialization Error",
                "detail": str(e),
                "traceback": err_tb,
                "sys_path": sys.path[:5]
            }
        )


