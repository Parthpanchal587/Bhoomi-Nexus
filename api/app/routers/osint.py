"""
BHOOMI NEXUS - OSINT / Public-Source Land Intelligence API Router

Provides RESTful endpoints for open-source land intelligence discovery,
cross-registry corroboration, conflict detection, risk triage, timeline analysis,
knowledge graphs, and verified evidence reports.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form

from app.osint.schemas import (
    DocumentCrossCheckRequest,
    DocumentCrossCheckResult,
    EvidenceGraphData,
    LandIntelligenceReport,
    OSINTSearchQuery,
    RestrictionFlag,
)
from app.osint.orchestrator import osint_orchestrator

router = APIRouter(prefix="/api/v1/osint", tags=["Public-Source Land Intelligence (OSINT)"])


@router.post("/search", summary="Execute OSINT Land Search")
async def search_land_intelligence(query: OSINTSearchQuery):
    """
    Executes a multi-source intelligence discovery across state land records,
    OpenStreetMap cadastral boundaries, Sentinel-2 public satellite epochs,
    and statutory e-Gazette notifications.
    """
    try:
        results = await osint_orchestrator.execute_intelligence_search(query)
        return {
            "status": "success",
            "query_id": results["query_id"],
            "parcel": results["parcel"],
            "sources": results["sources"],
            "conflicts": results["conflicts"],
            "restrictions": results["restrictions"],
            "risk_assessment": results["risk_assessment"],
            "observations": results["observations"],
            "timeline": results["timeline"],
            "temporal_anomalies": results["temporal_anomalies"],
            "graph": results["graph"],
            "report": results["report"],
            "markdown_dossier": results["markdown_dossier"],
            "sources_consulted": results["sources_consulted"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OSINT intelligence query failed: {str(e)}")


@router.get("/providers", summary="List Registered OSINT Data Providers")
async def list_registered_providers():
    """
    Returns registered public source providers (State portals, OSM, Sentinel-2, Gazette),
    their availability, provenance levels, and confidence ratings.
    """
    return {
        "status": "success",
        "providers": osint_orchestrator.get_registered_providers(),
    }


@router.post("/cross-check", response_model=DocumentCrossCheckResult, summary="Cross-Check Land Document with Public Registries")
async def cross_check_document(request: DocumentCrossCheckRequest):
    """
    Cross-references uploaded deed/mutation text with official public land registries.
    Computes document SHA-256 fingerprint (with legal disclaimer) and highlights inconsistencies.
    """
    try:
        res = await osint_orchestrator.cross_check_document(request)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document cross-check failed: {str(e)}")


@router.get("/graph/{parcel_id}", response_model=EvidenceGraphData, summary="Get Land Intelligence Knowledge Graph")
async def get_parcel_graph(parcel_id: str, state: str = "Rajasthan", district: str = "Jaipur"):
    """
    Returns the synthesized knowledge graph (nodes, edges, node degrees, entity links)
    for the specified land parcel.
    """
    query = OSINTSearchQuery(
        state=state,
        district=district,
        khasra_number=parcel_id,
    )
    res = await osint_orchestrator.execute_intelligence_search(query)
    return res["graph"]


@router.get("/timeline/{parcel_id}", summary="Get Multi-Year Chronological Timeline")
async def get_parcel_timeline(parcel_id: str, state: str = "Rajasthan", district: str = "Jaipur"):
    """
    Returns multi-year timeline synthesizing revenue mutations,
    satellite observation epochs, and gazette notifications, with anomaly flags.
    """
    query = OSINTSearchQuery(
        state=state,
        district=district,
        khasra_number=parcel_id,
    )
    res = await osint_orchestrator.execute_intelligence_search(query)
    return {
        "parcel_id": parcel_id,
        "timeline": res["timeline"],
        "temporal_anomalies": res["temporal_anomalies"],
    }


@router.post("/report", response_model=LandIntelligenceReport, summary="Generate Official Land Intelligence Dossier")
async def generate_evidence_report(query: OSINTSearchQuery):
    """
    Compiles an official Land Intelligence Dossier in structured JSON
    with cryptographic provenance ratings, conflict matrices, and statutory notices.
    """
    res = await osint_orchestrator.execute_intelligence_search(query)
    return res["report"]


@router.get("/restrictions", response_model=List[RestrictionFlag], summary="Check Statutory & Environmental Restrictions")
async def check_statutory_restrictions(state: str = "Rajasthan", district: str = "Jaipur"):
    """
    Evaluates statutory land ceiling, tribal land alienation (Sec 42/165/73AA),
    NHAI highway right-of-way (60m), and Eco-Sensitive Zone buffers.
    """
    query = OSINTSearchQuery(
        state=state,
        district=district,
    )
    return osint_orchestrator.restriction_engine.evaluate_restrictions(query)


@router.get("/audit", summary="Get OSINT Query Audit Trail")
async def get_audit_trail():
    """
    Returns the audit log of all executed OSINT queries with timestamps,
    operators, and parameters.
    """
    return {
        "status": "success",
        "audit_logs": osint_orchestrator.get_audit_trail(),
    }
