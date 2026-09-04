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
)


# ── Application Factory ──────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "GovTech Cadastral Geospatial & Soil Intelligence API for "
        "Document Verification, AI Intelligence, GIS Analysis, "
        "Policy Analytics, and Blockchain Verification."
    ),
)

# Enable CORS for local frontend GIS clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Mount Routers ────────────────────────────────────────────────────────

# Existing endpoints (backward compatible)
app.include_router(health.router)
app.include_router(geo.router)
app.include_router(telemetry.router)
app.include_router(simulation.router)
app.include_router(blockchain.router)
app.include_router(datasets.router)
app.include_router(insights.router)

# New v1 module endpoints
app.include_router(documents.router)
app.include_router(ai.router)
app.include_router(gis.router)
app.include_router(policy.router)


# ── Static Frontend Serving ──────────────────────────────────────────────

frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/", include_in_schema=False)
def root_index():
    if frontend_path.exists() and (frontend_path / "index.html").exists():
        return FileResponse(frontend_path / "index.html")
    return {"title": settings.APP_NAME, "status": "OPERATIONAL"}


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

