"""
Pydantic schemas for the AI Ask and AI Research modules.

Endpoints served:
  POST /api/v1/ai/ask        — contextual document Q&A (RAG)
  POST /api/v1/ai/research   — autonomous legal risk analysis
"""

from typing import Optional
from pydantic import BaseModel, Field


# ── AI Ask (Document Chat) ────────────────────────────────────────────────

class AIAskRequest(BaseModel):
    """User asks a natural language question about an uploaded document."""
    question: str = Field(
        ...,
        min_length=3,
        description="Natural language question, e.g., 'Is there any mortgage clause?'"
    )
    document_id: Optional[str] = Field(
        None,
        description="Ledger document ID. If provided, the system retrieves its stored text."
    )
    document_text: Optional[str] = Field(
        None,
        description="Raw document text. Used when document_id is not available."
    )
    api_key: Optional[str] = Field(
        None,
        description="Optional Gemini API key for live LLM synthesis."
    )


class RelevantExcerpt(BaseModel):
    """A chunk of the source document relevant to the user's question."""
    text: str
    page_reference: Optional[str] = None
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class AIAskResponse(BaseModel):
    """Structured answer to the user's question with source excerpts."""
    question: str
    answer: str
    confidence: float = Field(..., ge=0.0, le=100.0)
    relevant_excerpts: list[RelevantExcerpt]
    document_id: Optional[str] = None
    model_used: str = "BHOOMI Domain-Specific RAG Synthesizer"


# ── AI Research (Legal Analysis) ──────────────────────────────────────────

class AIResearchRequest(BaseModel):
    """Request for autonomous legal research over a property document."""
    document_id: Optional[str] = Field(
        None,
        description="Ledger document ID for the property document."
    )
    document_text: Optional[str] = Field(
        None,
        description="Raw document text. Used when document_id is not available."
    )
    api_key: Optional[str] = Field(
        None,
        description="Optional Gemini API key for enhanced analysis."
    )


class EncumbranceFlag(BaseModel):
    """A detected encumbrance, lien, or restriction on the property."""
    type: str = Field(..., description="e.g., 'Mortgage', 'Lien', 'Easement', 'Litigation'")
    description: str
    severity: str = Field(..., description="LOW / MEDIUM / HIGH / CRITICAL")
    clause_reference: Optional[str] = None


class TitleChainEntry(BaseModel):
    """One link in the chain of custody / title deed history."""
    sequence: int
    owner_name: str
    transfer_type: str = Field(..., description="e.g., 'Sale Deed', 'Gift Deed', 'Inheritance', 'Partition'")
    date: Optional[str] = None
    registration_number: Optional[str] = None
    notes: Optional[str] = None


class RiskBreakdown(BaseModel):
    """Score breakdown for a single risk category."""
    category: str
    score: float = Field(..., ge=0.0, le=100.0)
    assessment: str
    details: str


class AIResearchResponse(BaseModel):
    """Complete legal research analysis of a property document."""
    document_id: Optional[str] = None
    executive_summary: str

    # Chain of custody
    title_chain: list[TitleChainEntry]
    chain_continuity_status: str  # COMPLETE / BROKEN / PARTIAL

    # Risk analysis
    legal_risk_score: float = Field(..., ge=0.0, le=100.0, description="0 = no risk, 100 = maximum risk")
    clarity_score: float = Field(..., ge=0.0, le=100.0, description="0 = unclear, 100 = perfectly clear")
    risk_breakdown: list[RiskBreakdown]

    # Flags
    encumbrances: list[EncumbranceFlag]
    missing_elements: list[str]
    litigation_risk_indicators: list[str]

    # Suggestions
    recommended_actions: list[str]
    model_used: str = "BHOOMI Legal Research Engine"
