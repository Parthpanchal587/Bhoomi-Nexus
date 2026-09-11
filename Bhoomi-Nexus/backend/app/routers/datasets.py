"""
Dataset catalog, research repository, and AI query endpoints.
Extracted from original main.py — logic identical.
"""

import re
import json
from typing import Optional

import httpx
from fastapi import APIRouter, Query

from app.config import (
    DATASET_CATALOG,
    RESEARCH_REPOSITORY,
    DISTRICT_PROFILES,
)
from app.schemas.common import (
    AIQueryRequest,
    AIQueryResponse,
    SourceCitation,
    CompetitiveAdvantage,
)
from app.services.land_intelligence import LandIntelligenceEngine

router = APIRouter(tags=["Datasets & Research"])


# ── Competitor Benchmarks ─────────────────────────────────────────────────

COMPETITOR_BENCHMARKS = [
    CompetitiveAdvantage(
        legacy_platform="Legacy Cadastral Map Viewers",
        current_limitation="Provides static digital cadastral boundary maps and plot ownership. Zero research cross-referencing, no AI semantic search, no environmental telemetry, and no policy simulation.",
        bhoomi_nexus_advantage="Unifies cadastral boundaries with ISRO satellite remote sensing, real-time soil telemetry, predictive Section 90-A policy impact modeling, and cryptographic blockchain notary.",
    ),
    CompetitiveAdvantage(
        legacy_platform="Basic Drone Mapping Surveys",
        current_limitation="Excellent for high-resolution drone ortho-photos and rural property cards, but lacks cross-departmental ecological analytics, groundwater depletion modeling, or policy scenario forecasting.",
        bhoomi_nexus_advantage="Integrates drone-scale parcel resolutions with macro-level CGWB hydrological stress models and peer-reviewed research papers to evaluate agricultural viability before conversion.",
    ),
    CompetitiveAdvantage(
        legacy_platform="Isolated State Land Record Portals",
        current_limitation="Siloed state repositories limited to viewing static record extracts. Records are static PDFs with no multi-temporal satellite time-series or multi-state federation.",
        bhoomi_nexus_advantage="Federated cross-state architecture (Rajasthan, Karnataka, Delhi, Gujarat) with multi-epoch Sentinel-2 time series (2018–2026) and immutable SHA-256 blockchain verification.",
    ),
    CompetitiveAdvantage(
        legacy_platform="Commercial Real Estate Portals",
        current_limitation="Private real-estate land aggregation advisories focused strictly on commercial acquisitions and private transactions. Zero public accountability or ecological impact simulation.",
        bhoomi_nexus_advantage="Sovereign GovTech platform built for public officials, researchers, and farmers prioritizing Land Degradation Neutrality (LDN) and sustainable aquifer management.",
    ),
]


# ── Dataset Endpoints ─────────────────────────────────────────────────────

@router.get("/api/datasets")
def get_datasets(
    category: Optional[str] = Query(None, description="Filter by category: 'Land Degradation', 'Groundwater', 'Soil Health', 'Land Use', 'Cadastral'"),
    search: Optional[str] = Query(None, description="Text search in title/description"),
):
    results = DATASET_CATALOG
    if category and category.lower() != "all":
        results = [d for d in results if d["category"].lower() == category.lower()]
    if search:
        s_lower = search.lower()
        results = [
            d for d in results
            if s_lower in d["title"].lower()
            or s_lower in d["description"].lower()
            or s_lower in d["region"].lower()
        ]
    return {
        "total": len(results),
        "verified_count": sum(1 for d in results if d.get("verified")),
        "datasets": results,
    }


@router.get("/api/datasets/{dataset_id}")
def get_dataset_detail(dataset_id: str):
    from fastapi import HTTPException
    for d in DATASET_CATALOG:
        if d["id"].upper() == dataset_id.upper():
            return d
    raise HTTPException(status_code=404, detail="Dataset not found")


@router.get("/api/research")
def get_research_papers():
    return {
        "total": len(RESEARCH_REPOSITORY),
        "repository": RESEARCH_REPOSITORY,
    }


# ── AI Query (Ask BHOOMI — existing) ─────────────────────────────────────

@router.post("/api/ai/query", response_model=AIQueryResponse)
async def ask_bhoomi_intelligence(req: AIQueryRequest):
    """
    Central Land Intelligence Engine (Ask BHOOMI).
    Synthesizes natural-language legal and spatial land queries across 16+ canonical intents
    grounded strictly in the active parcel context, verified cadastral/GIS telemetry,
    and structured evidence states (VERIFIED, PROVISIONAL, NOT_FOUND, UNAVAILABLE).
    """
    result = await LandIntelligenceEngine.process_query(
        query=req.query,
        parcel=req.parcel,
        telemetry=req.telemetry,
        soil=req.soil,
        document_text=req.document_text,
        document_id=req.document_id,
        api_key=req.api_key
    )
    return AIQueryResponse(**result)
