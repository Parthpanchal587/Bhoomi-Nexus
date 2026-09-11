"""
AI Ask Service — Contextual Document Chat with RAG.

Supports:
1. Internal domain-specific RAG synthesis (zero external dependency)
2. Optional live Gemini API for enhanced responses

The RAG pipeline splits the document into chunks, performs keyword-based
semantic matching against the user's question, and synthesizes a
structured answer with relevant excerpts.
"""

import json
import re
from typing import Optional

import httpx

from app.schemas.ai import AIAskResponse, RelevantExcerpt


# ── Text Chunking ─────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    """Split text into overlapping chunks with page references."""
    chunks: list[dict] = []
    if not text:
        return chunks

    # Try to detect page markers
    pages = re.split(r"\[Page (\d+)\]", text)
    current_page = "1"
    full_text_parts: list[tuple[str, str]] = []

    i = 0
    while i < len(pages):
        if re.match(r"^\d+$", pages[i].strip()):
            current_page = pages[i].strip()
            i += 1
            continue
        if pages[i].strip():
            full_text_parts.append((current_page, pages[i].strip()))
        i += 1

    if not full_text_parts:
        # No page markers, treat as single block
        full_text_parts = [("1", text)]

    for page_ref, page_text in full_text_parts:
        words = page_text.split()
        for start in range(0, len(words), chunk_size - overlap):
            chunk_words = words[start : start + chunk_size]
            if chunk_words:
                chunks.append({
                    "text": " ".join(chunk_words),
                    "page": f"Page {page_ref}",
                })

    return chunks


# ── Relevance Scoring ────────────────────────────────────────────────────

def _score_chunk(chunk_text: str, question: str) -> float:
    """
    Compute a simple keyword-based relevance score (0.0–1.0).

    Uses weighted keyword matching — legal/property terms get higher weight.
    """
    q_words = set(re.findall(r"\w+", question.lower()))
    c_words = set(re.findall(r"\w+", chunk_text.lower()))

    # High-value legal/property terms
    high_value = {
        "mortgage", "lien", "encumbrance", "easement", "title", "deed",
        "owner", "boundary", "north", "south", "east", "west",
        "registration", "stamp", "clause", "section", "schedule",
        "sale", "gift", "partition", "inheritance", "lease", "rent",
        "survey", "khasra", "khata", "mutation", "parcel", "plot",
        "area", "hectare", "acre", "sqft", "square",
    }

    if not q_words:
        return 0.0

    matches = q_words & c_words
    if not matches:
        return 0.0

    # Weight high-value matches more
    score = 0.0
    for word in matches:
        if word in high_value:
            score += 2.0
        else:
            score += 1.0

    max_possible = sum(2.0 if w in high_value else 1.0 for w in q_words)
    return min(1.0, score / max_possible)


# ── Main RAG Pipeline ────────────────────────────────────────────────────

async def ask_document_question(
    question: str,
    document_text: str,
    document_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AIAskResponse:
    """
    Answer a natural language question about a document using RAG.

    1. Chunks the document text
    2. Scores chunks against the question
    3. Optionally calls Gemini API for enhanced synthesis
    4. Returns structured answer with relevant excerpts
    """
    # Chunk and score
    chunks = _chunk_text(document_text)
    scored = [(chunk, _score_chunk(chunk["text"], question)) for chunk in chunks]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Take top relevant chunks
    top_chunks = [(c, s) for c, s in scored[:5] if s > 0.05]

    # Build excerpts
    relevant_excerpts = [
        RelevantExcerpt(
            text=chunk["text"][:400],
            page_reference=chunk.get("page"),
            relevance_score=round(score, 3),
        )
        for chunk, score in top_chunks
    ]

    # Build context for answer synthesis
    context_text = "\n\n".join(chunk["text"] for chunk, _ in top_chunks) if top_chunks else document_text[:2000]

    # Try Gemini API if key provided
    if api_key:
        gemini_answer = await _call_gemini_ask(question, context_text, api_key)
        if gemini_answer:
            return AIAskResponse(
                question=question,
                answer=gemini_answer,
                confidence=round(max((s for _, s in scored[:3]), default=0.5) * 100, 1),
                relevant_excerpts=relevant_excerpts,
                document_id=document_id,
                model_used="Google Gemini 1.5 Flash (Live Cloud RAG)",
            )

    # Internal RAG synthesis
    answer = _synthesize_answer(question, context_text, top_chunks)
    confidence = round(max((s for _, s in scored[:3]), default=0.3) * 100, 1)

    return AIAskResponse(
        question=question,
        answer=answer,
        confidence=min(95.0, confidence),
        relevant_excerpts=relevant_excerpts,
        document_id=document_id,
        model_used="BHOOMI Domain-Specific RAG Synthesizer",
    )


def _synthesize_answer(question: str, context: str, top_chunks: list) -> str:
    """
    Synthesize an answer from the retrieved context chunks.
    Domain-specific heuristic synthesis without external LLM.
    """
    q_lower = question.lower()

    if not top_chunks:
        return (
            "Based on the available document content, I could not find a directly relevant "
            "section addressing your specific question. The document may not contain explicit "
            "information about this topic, or the relevant content may require deeper semantic "
            "analysis. Please try rephrasing your question or upload a more specific document."
        )

    # Extract the most relevant passage
    best_passage = top_chunks[0][0]["text"][:600]

    # Detect question type and frame answer
    if any(w in q_lower for w in ["mortgage", "lien", "encumbrance", "charge"]):
        return (
            f"Regarding mortgage and encumbrance clauses in this document: "
            f"The most relevant section states: \"{best_passage}...\" "
            f"Based on this content, the document {'appears to contain' if any(w in best_passage.lower() for w in ['mortgage', 'lien', 'charge', 'hypothecat']) else 'does not appear to explicitly mention'} "
            f"mortgage or encumbrance provisions. A thorough legal review is recommended for definitive assessment."
        )

    if any(w in q_lower for w in ["boundary", "north", "south", "east", "west", "adjacent", "neighbor"]):
        return (
            f"Regarding boundary and adjacency information in this document: "
            f"The most relevant section states: \"{best_passage}...\" "
            f"This section provides information about the property boundaries as recorded in the document. "
            f"For precise survey measurements, cross-reference with the official cadastral survey records."
        )

    if any(w in q_lower for w in ["owner", "title", "name", "holder", "who"]):
        return (
            f"Regarding ownership and title information: "
            f"The most relevant section states: \"{best_passage}...\" "
            f"This section contains information about the property ownership as documented. "
            f"Verify current ownership status through the Sub-Registrar's office and mutation records."
        )

    if any(w in q_lower for w in ["area", "size", "hectare", "acre", "extent", "measurement"]):
        return (
            f"Regarding property area and measurements: "
            f"The most relevant section states: \"{best_passage}...\" "
            f"This section provides the recorded measurements of the property. "
            f"For legal purposes, official survey measurements should be obtained from the Survey Department."
        )

    # Generic answer
    return (
        f"Based on analysis of the document content relevant to your question: "
        f"The most pertinent section states: \"{best_passage}...\" "
        f"This passage from the document is the most relevant to your query. "
        f"For comprehensive legal interpretation, consult a qualified legal professional."
    )


async def _call_gemini_ask(question: str, context: str, api_key: str) -> Optional[str]:
    """Call Gemini API for enhanced answer synthesis."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        prompt = (
            "You are a legal document analysis assistant for Indian property law. "
            "Answer the following question based ONLY on the provided document context. "
            "Be precise, cite relevant sections, and note any caveats.\n\n"
            f"DOCUMENT CONTEXT:\n{context[:3000]}\n\n"
            f"QUESTION: {question}\n\n"
            "ANSWER:"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        pass
    return None
