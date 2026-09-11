"""
BHOOMI-NEXUS: National Land Intelligence & Cadastral Geospatial Engine
FastAPI Application Factory — Modular backend without external database dependencies.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings

# ── Import all routers ────────────────────────────────────────────────────
from app.routers import (
    health,
    geo,
    telemetry,
    simulation,
    blockchain,
    datasets,
    insights,
    documents,
    ai,
    gis,
    policy,
    enclave,
    osint,
    auth,
)
from app.middleware.security import SecurityHeadersMiddleware, RateLimiterMiddleware


# ── Application Factory ──────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Land Intelligence API with Trusted Execution Environment (TEE)-inspired "
        "Secure Execution Architecture for Document Verification, Policy Analytics, "
        "and Cryptographic Integrity."
    ),
)

# Security Middlewares: HTTP Security Headers & Rate Limiting
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware)

# Enable CORS safely for frontend clients
origins = settings.CORS_ORIGINS
use_credentials = True
if "*" in origins:
    # RFC 6454 / W3C: allow_credentials cannot be True when allow_origins is ["*"]
    use_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=use_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Mount Routers ────────────────────────────────────────────────────────

# Security & Authentication router (v1)
app.include_router(auth.router)

# Existing endpoints (backward compatible)
app.include_router(health.router)
app.include_router(geo.router)
app.include_router(telemetry.router)
app.include_router(simulation.router)
app.include_router(blockchain.router)
app.include_router(datasets.router)
app.include_router(insights.router)

# V1 module endpoints
app.include_router(documents.router)
app.include_router(ai.router)
app.include_router(gis.router)
app.include_router(policy.router)

# Secure Enclave (TEE Layer)
app.include_router(enclave.router)

# Public-Source Land Intelligence (OSINT Layer)
app.include_router(osint.router)


# ── Static Frontend Serving ──────────────────────────────────────────────

frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/", include_in_schema=False)
def root_index():
    if frontend_path.exists() and (frontend_path / "index.html").exists():
        return FileResponse(frontend_path / "index.html")
    return {"title": settings.APP_NAME, "status": "OPERATIONAL"}


@app.get("/login", include_in_schema=False)
def login_route():
    if frontend_path.exists() and (frontend_path / "login.html").exists():
        return FileResponse(frontend_path / "login.html")
    if frontend_path.exists() and (frontend_path / "index.html").exists():
        return FileResponse(frontend_path / "index.html")
    return {"title": "Bhoomi Nexus Login", "status": "LOGIN_PAGE"}


@app.get("/dashboard", include_in_schema=False)
def dashboard_route():
    if frontend_path.exists() and (frontend_path / "dashboard.html").exists():
        return FileResponse(frontend_path / "dashboard.html")
    if frontend_path.exists() and (frontend_path / "index.html").exists():
        return FileResponse(frontend_path / "index.html")
    return {"title": "Bhoomi Nexus Dashboard", "status": "DASHBOARD"}


@app.get("/ashoka_stambh.png", include_in_schema=False)
def get_ashoka_stambh():
    img_path = frontend_path / "ashoka_stambh.png"
    if img_path.exists():
        return FileResponse(img_path, media_type="image/png")
    return {"error": "Image not found"}


@app.get("/india_mask.json", include_in_schema=False)
def get_india_mask():
    mask_path = frontend_path / "india_mask.json"
    if mask_path.exists():
        return FileResponse(mask_path, media_type="application/json")
    return {"error": "Mask not found"}


@app.get("/india_boundary.json", include_in_schema=False)
def get_india_boundary():
    b_path = frontend_path / "india_boundary.json"
    if b_path.exists():
        return FileResponse(b_path, media_type="application/json")
    return {"error": "Boundary not found"}


if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

