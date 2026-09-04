"""
Health & system info endpoints.
Extracted from original main.py — logic identical.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings
from app.schemas.common import HealthResponse
from app.services.blockchain import ledger

router = APIRouter(tags=["System"])

start_time = time.time()


@router.get("/api")
def root_info():
    return {
        "title": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "node_id": settings.NODE_ID,
        "status": "OPERATIONAL",
        "modules": [
            "AI Search ('Ask BHOOMI')",
            "AI Document Chat (v1)",
            "AI Legal Research (v1)",
            "GIS Intelligence (v1)",
            "Policy & Zoning Analytics (v1)",
            "Document Verification (v1)",
            "Dataset Repository",
            "Policy Simulator V2",
            "Sovereign Blockchain Notary",
        ],
    }


@router.get("/api/health", response_model=HealthResponse)
def get_health():
    uptime = time.time() - start_time
    return HealthResponse(
        status="ONLINE",
        node_id=settings.NODE_ID,
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(uptime, 2),
        blockchain_blocks=len(ledger.chain),
        latest_block_hash=ledger.latest_block.hash,
    )
