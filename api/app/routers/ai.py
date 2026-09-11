"""
AI Ask & Research Router.

Endpoints:
  POST /api/v1/ai/ask       — Contextual document Q&A with RAG
  POST /api/v1/ai/research   — Autonomous legal risk analysis
"""

from fastapi import APIRouter, HTTPException

from app.schemas.ai import (
    AIAskRequest,
    AIAskResponse,
    AIResearchRequest,
    AIResearchResponse,
)
from app.services.ai_ask import ask_document_question
from app.services.ai_research import analyze_legal_document
from app.services.document_verification import get_document_by_id

router = APIRouter(prefix="/api/v1/ai", tags=["AI Intelligence (v1)"])


def _resolve_document_text(
    document_id: str | None,
    document_text: str | None,
) -> tuple[str | None, str]:
    """
    Resolve document text from either a document_id or raw text.
    Returns (document_id, text).
    """
    if document_id:
        record = get_document_by_id(document_id)
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID '{document_id}' not found in the ledger.",
            )
        return document_id, record.extracted_text

    if document_text and document_text.strip():
        return None, document_text

    raise HTTPException(
        status_code=400,
        detail="Either 'document_id' or 'document_text' must be provided.",
    )


@router.post("/ask", response_model=AIAskResponse)
async def ai_ask_endpoint(
    req: AIAskRequest,
):
    """
    Ask a natural language question about an uploaded document.

    Supports RAG-powered contextual answers with source excerpts.
    Optionally enhanced by Gemini API when api_key is provided.

    Examples:
    - "Is there any mortgage clause?"
    - "Who is the boundary owner on the North side?"
    - "What is the total area of the property?"
    """
    doc_id, text = _resolve_document_text(req.document_id, req.document_text)

    return await ask_document_question(
        question=req.question,
        document_text=text,
        document_id=doc_id,
        api_key=req.api_key,
    )


@router.post("/research", response_model=AIResearchResponse)
async def ai_research_endpoint(
    req: AIResearchRequest,
):
    """
    Perform autonomous legal research over a property document.

    Analyzes:
    - Chain of custody and title deed history
    - Encumbrances, liens, and restrictions
    - Missing signatures and legal elements
    - Computes Risk Score and Clarity Score
    - Plain-language legal intelligence summary
    """
    doc_id, text = _resolve_document_text(req.document_id, req.document_text)

    return await analyze_legal_document(
        document_text=text,
        document_id=doc_id,
        api_key=req.api_key,
    )
